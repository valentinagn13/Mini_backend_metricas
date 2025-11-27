import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import math

class DataQualityCalculator:
    def __init__(self, dataset_url: str, metadata: Optional[Dict] = None):
        # `dataset_url` historically contained the dataset identifier passed
        # from the API (`dataset_id`). Keep both attributes for clarity.
        self.dataset_url = dataset_url
        # expose `dataset_id` for compatibility with main.py validation
        self.dataset_id = dataset_url
        self.metadata = metadata or {}
        self.df = None
        self.df_columnas = 0
        self.df_filas = 0
        self.cached_scores = {}

    async def load_data(self, limit: int = 50000) -> None:
        """
        Carga todos los datos del dataset desde Socrata usando paginación optimizada.
        
        Optimizaciones:
        - Carga únicamente hasta el límite especificado
        - Detiene paginación temprano si detecta última página
        - Usa tipos de datos eficientes para reducir memoria
        - Realiza operaciones vectorizadas en pandas
        
        Args:
            limit: Número máximo de registros a cargar (por defecto 50000)
        """
        base_url = f"https://www.datos.gov.co/resource/{self.dataset_id}.json"
        
        print(f"🔗 Obteniendo datos desde: {base_url}")
        print(f"📦 Límite configurado: {limit} registros")
        
        all_data = []
        offset = 0
        page_size = 1000  # Máximo por página en Socrata
        total_obtained = 0
        
        try:
            import time
            while offset < limit:
                url = f"{base_url}?$limit={page_size}&$offset={offset}"
                print(f"📄 Solicitando página: offset={offset}, limit={page_size}")
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    page_data = response.json()
                    records_in_page = len(page_data)
                    all_data.extend(page_data)
                    total_obtained += records_in_page
                    
                    print(f"✅ Página obtenida: {records_in_page} registros (total: {total_obtained})")
                    
                    # Si obtenemos menos registros que el page_size, es la última página
                    if records_in_page < page_size:
                        print(f"🏁 Última página alcanzada. Total: {total_obtained} registros")
                        break
                    
                    # Si hemos alcanzado el límite, detener
                    if total_obtained >= limit:
                        print(f"⚠️  Límite de {limit} registros alcanzado")
                        break
                    
                    offset += page_size
                    time.sleep(0.05)  # Reducida la pausa
                    
                else:
                    print(f"❌ Error en página {offset}: {response.status_code}")
                    break
                    
            print(f"🎯 Total de registros obtenidos: {len(all_data)}")
            
            if all_data:
                # Crear DataFrame con tipos de datos optimizados
                self.df = pd.DataFrame(all_data)
                
                # Optimizar tipos de datos para reducir memoria
                self._optimize_dtypes()
                
                self.df_filas = len(self.df)
                self.df_columnas = len(self.df.columns)
                print(f"📊 DataFrame cargado: {self.df_filas} filas, {self.df_columnas} columnas")
                print(f"💾 Memoria usada: {self.df.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
            else:
                print("⚠️ No se obtuvieron datos")
                self.df = pd.DataFrame()
                self.df_filas = 0
                self.df_columnas = 0
                
        except Exception as e:
            print(f"❌ Error obteniendo datos: {e}")
            self.df = pd.DataFrame()
            self.df_filas = 0
            self.df_columnas = 0
            raise

    def _optimize_dtypes(self) -> None:
        """
        Optimiza los tipos de datos del DataFrame para reducir memoria y mejorar velocidad.
        Convierte strings largos a categorías cuando es apropiado.
        """
        for col in self.df.columns:
            col_type = self.df[col].dtype
            
            # Optimizar objetos (strings)
            if col_type == 'object':
                num_unique = self.df[col].nunique()
                num_total = len(self.df[col])
                
                # Si menos del 5% son valores únicos, convertir a categoría
                if num_unique / num_total < 0.05 and num_unique < 1000:
                    self.df[col] = self.df[col].astype('category')
            
            # Optimizar números enteros
            elif col_type == 'int64':
                col_min = self.df[col].min()
                col_max = self.df[col].max()
                
                if col_min >= 0 and col_max < 256:
                    self.df[col] = self.df[col].astype('uint8')
                elif col_min >= 0 and col_max < 65536:
                    self.df[col] = self.df[col].astype('uint16')
                elif col_min >= -32768 and col_max < 32768:
                    self.df[col] = self.df[col].astype('int16')
            
            # Optimizar números flotantes
            elif col_type == 'float64':
                self.df[col] = self.df[col].astype('float32')

    def _convertir_frecuencia_a_dias(self, frecuencia) -> Optional[float]:
        """
        Convierte una representación de frecuencia a número aproximado de días.
        Devuelve:
          - int/float: número de días
          - None: si la frecuencia es 'No aplica' (indeterminado)
          - math.inf: si la frecuencia es 'Nunca' (nunca se actualiza)
        """
        if frecuencia is None:
            return 365  # defecto anual

        # ya numérico
        try:
            if isinstance(frecuencia, (int, float)):
                return int(frecuencia)
            s = str(frecuencia).strip()
            if re.fullmatch(r"\d+", s):
                return int(s)
        except Exception:
            pass

        s = str(frecuencia).strip().lower()

        # mapeo ampliado (incluye etiquetas del gráfico)
        mapping = {
            'diario': 1, 'diarios': 1, 'daily': 1,
            'semanal': 7, 'semanales': 7, 'weekly': 7,
            'quincenal': 15, 'quincenales': 15,
            'mensual': 30, 'mensuales': 30, 'monthly': 30,
            'trimestral': 90, 'trimestrales': 90,
            'cuatrimestral': 120,
            'semestral': 182, 'semestrales': 182, 'semestre': 182,
            'trienio': 1095, 'trienal': 1095,
            'anual': 365, 'anualmente': 365, 'anuales': 365, 'yearly': 365, 'annual': 365,
            'mas de tres años': 1460, 'más de tres años': 1460,
            'solo una vez': 3650,  # tratamos como valor grande por defecto (≈10 años)
            'solo una vez dnp': 3650,
            'nunca': math.inf,
            'no aplica': None, 'no_aplica': None, 'na': None, 'n/a': None
        }
        if s in mapping:
            return mapping[s]

        # patrones ISO simples (P1Y, P1M, P30D)
        m2 = re.match(r"p(\d+)([ymd])", s)
        if m2:
            num = int(m2.group(1))
            unidad = m2.group(2)
            if unidad == 'y':
                return num * 365
            if unidad == 'm':
                return num * 30
            if unidad == 'd':
                return num

        # buscar patrones como '30 dias', '30 días', 'cada 15 dias'
        m = re.search(r"(\d+)\s*(d[ií]as|dias)?", s)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        # no reconocido -> por defecto anual
        return 365

    def calculate_actualidad(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de actualidad.
        - Devuelve 10.0 si (hoy - fecha_actualizacion) <= frecuencia_dias
        - Devuelve 0.0 si (hoy - fecha_actualizacion) > frecuencia_dias
        - Devuelve 5.0 si falta información o es indeterminado ('No aplica')
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles (evita duplicación cuando se llama desde endpoint)
        """
        metadata = metadata or self.metadata or {}

        if verbose:
            print("\n=== DEBUG ACTUALIDAD ===")
            print("Metadata completa recibida:")
            try:
                print(json.dumps(metadata, indent=4, ensure_ascii=False))
            except Exception:
                print(metadata)

        # 1) obtener fecha de actualización
        fecha_actualizacion = None
        fecha_actualizacion_str = metadata.get('fecha_actualizacion')
        if fecha_actualizacion_str:
            try:
                fecha_actualizacion = datetime.fromisoformat(fecha_actualizacion_str.replace('Z', '+00:00'))
            except Exception:
                try:
                    fecha_actualizacion = datetime.strptime(fecha_actualizacion_str, '%Y-%m-%d')
                except Exception:
                    print(f"⚠ No se pudo parsear fecha_actualizacion: {fecha_actualizacion_str}")
                    fecha_actualizacion = None

        # fallback: rowsUpdatedAt (Socrata u otros)
        if fecha_actualizacion is None:
            rows_updated_at = metadata.get('rowsUpdatedAt') or metadata.get('rows_updated_at')
            if rows_updated_at:
                try:
                    ts = int(rows_updated_at)
                    # detectar ms vs s
                    if ts > 1e12:
                        ts = int(ts / 1000)
                    fecha_actualizacion = datetime.fromtimestamp(ts)
                    print(f"✔ Usando rowsUpdatedAt timestamp -> {fecha_actualizacion}")
                except Exception as e:
                    print(f"⚠ Error parseando rowsUpdatedAt: {e}")

        if fecha_actualizacion is None:
            print("⚠ No se encontró fecha_actualizacion válida -> Puntaje = 5.0")
            return 5.0

        # 2) obtener frecuencia en días (puede devolver None o math.inf)
        frecuencia_dias = metadata.get('frecuencia_actualizacion_dias')
        if frecuencia_dias is None:
            # Intentar obtener frecuencia desde múltiples ubicaciones
            frecuencia_str = None
            
            # Opción 1: estructura de Socrata (metadata.metadata.custom_fields['Información de Datos']['Frecuencia de Actualización'])
            if metadata.get('metadata', {}).get('custom_fields'):
                frecuencia_str = (metadata
                                 .get('metadata', {})
                                 .get('custom_fields', {})
                                 .get('Información de Datos', {})
                                 .get('Frecuencia de Actualización'))
                if frecuencia_str:
                    print(f"✔ Frecuencia encontrada en metadata.custom_fields['Información de Datos']: {frecuencia_str}")
            
            # Opción 2: campos simples de nivel superior
            if not frecuencia_str:
                frecuencia_str = (metadata.get('updateFrequency') or
                                  metadata.get('frecuencia_actualizacion') or
                                  metadata.get('frecuencia'))
                if frecuencia_str:
                    print(f"✔ Frecuencia encontrada en campo simple: {frecuencia_str}")
            
            # Opción 3: por defecto
            if not frecuencia_str:
                frecuencia_str = 'Anual'
                print(f"✔ Usando frecuencia por defecto: {frecuencia_str}")
            
            frecuencia_dias = self._convertir_frecuencia_a_dias(frecuencia_str)

        print(f"✔ frecuencia original metadata: {frecuencia_str}")
        print(f"✔ frecuencia normalizada (días): {frecuencia_dias}")

        # manejo especiales
        if frecuencia_dias is None:
            print("⚠ Frecuencia = 'No aplica' (indeterminado) -> Puntaje = 5.0")
            return 5.0
        if frecuencia_dias == math.inf:
            print("ℹ Frecuencia = 'Nunca' -> dataset declarado como nunca actualizado -> Puntaje = 0.0")
            return 0.0

        # caso explícito 'más de tres años' — siempre 10.0
        # IMPORTANTE: buscar en la misma ubicación donde ya extrajimos frecuencia_str
        freq_raw = str(frecuencia_str or '').lower()
        # normalizar: remover acentos y caracteres especiales
        freq_normalized = re.sub(r'[^a-z0-9\s]', '', freq_raw)
        print(f"🔍 DEBUG 'más de tres años': freq_raw='{freq_raw}', freq_normalized='{freq_normalized}'")
        if 'mas' in freq_normalized and 'tres' in freq_normalized and 'anos' in freq_normalized:
            print("✅ Frecuencia = 'Más de tres años' -> Puntaje = 10.0")
            return 10.0

        # caso explícito 'solo una vez' — si fue hace <= 5 años consideramos aceptable
        if 'solo' in freq_raw and 'vez' in freq_raw:
            fecha_actual = datetime.now()
            diferencia_dias = (fecha_actual - fecha_actualizacion).days
            print(f"✔ Días transcurridos: {diferencia_dias} (regla 'solo una vez' umbral=5 años)")
            if diferencia_dias <= 5*365:
                print("✅ 'Solo una vez' dentro de 5 años -> Puntaje = 10.0")
                return 10.0
            else:
                print("❌ 'Solo una vez' fuera de 5 años -> Puntaje = 0.0")
                return 0.0

        # 3) cálculo normal
        fecha_actual = datetime.now()
        diferencia_dias = (fecha_actual - fecha_actualizacion).days
        print(f"✔ Fecha actual: {fecha_actual}")
        print(f"✔ Fecha última actualización: {fecha_actualizacion}")
        print(f"✔ Días transcurridos desde la última actualización: {diferencia_dias}")
        print(f"✔ Comparación: diferencia_dias ({diferencia_dias}) > frecuencia_dias ({frecuencia_dias}) ?")

        if diferencia_dias > frecuencia_dias:
            print("❌ Desactualizado -> Puntaje = 0.0")
            return 0.0
        else:
            print("✅ Dentro de la frecuencia -> Puntaje = 10.0")
            return 10.0
   
   
   
   
   
    def _identify_sensitive_columns(self) -> Dict[str, int]:
        sensitive_patterns = {
            'alto': ['cedula', 'cc', 'dni', 'pasaporte', 'password', 'contrasena', 'tarjeta', 'cuenta_bancaria'],
            'medio': ['telefono', 'celular', 'direccion', 'email', 'correo'],
            'bajo': ['nombre', 'apellido', 'edad', 'genero']
        }

        risk_map = {'alto': 3, 'medio': 2, 'bajo': 1}
        column_risks = {}

        for col in self.df.columns:
            col_lower = str(col).lower()
            for risk_level, patterns in sensitive_patterns.items():
                if any(pattern in col_lower for pattern in patterns):
                    column_risks[col] = risk_map[risk_level]
                    break

        return column_risks


    def calculate_confidencialidad(self) -> float:
        column_risks = self._identify_sensitive_columns()
        num_col_confidencial = len(column_risks)

        if num_col_confidencial == 0:
            return 10.0

        riesgo_total = sum(column_risks.values())

        confidencialidad = 10 - (num_col_confidencial / self.df_columnas) * (riesgo_total / (num_col_confidencial * 3)) * 10

        return max(0, min(10, confidencialidad))


    def calculate_confidencialidad_from_metadata(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de confidencialidad usando SOLO metadatos (lista de columnas).

        Reglas implementadas:
        - Detectar columnas sensibles buscando palabras clave en el `name` y `description`.
        - Clasificar riesgo: alto=3, medio=2, bajo=1.
        - propConf = N_conf / N_totalColumns
        - riesgo_total = sum(pesos de columnas confidenciales)
        - score = max(0, 10 - (propConf * riesgo_total))

        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles (evita duplicación cuando se llama desde endpoint)
        
        Prints detallados muestran entradas intermedias y el cálculo.
        """
        metadata = metadata or self.metadata or {}
        
        if verbose:
            print("\n=== DEBUG CONFIDENCIALIDAD (METADATA) ===")
            print("Metadata recibida para confidencialidad:")
            try:
                print(json.dumps(metadata, indent=2, ensure_ascii=False))
            except Exception:
                print(metadata)

        columns_meta = metadata.get('columns') or []
        # columnas pueden venir como lista de dicts con 'name' y 'description'
        total_columns = len(columns_meta)
        print(f"Total columnas detectadas en metadata: {total_columns}")

        # palabras clave por nivel de riesgo
        high_kw = [
            'documento', 'documento de identidad', 'pasaporte', 'cuenta bancaria', 'cuenta', 'banco',
            'tarjeta', 'historial', 'historial medico', 'historial médico', 'diagnostico', 'diagnóstico',
            'password', 'contraseña', 'cedula', 'cédula', 'dni'
        ]
        medium_kw = [
            'direccion', 'dirección', 'telefono', 'teléfono', 'celular', 'correo', 'email', 'mail'
        ]
        low_kw = [
            'fecha de nacimiento', 'nacimiento', 'sexo', 'edad', 'nombre', 'apellido'
        ]

        detected = []  # list of tuples (col_name, nivel, peso)

        for col in columns_meta:
            # soportar dicts o strings
            if isinstance(col, dict):
                name = str(col.get('name') or col.get('fieldName') or '')
            else:
                name = str(col)

            # Solo buscar en el NOMBRE de la columna, ignorar descripción para evitar falsos positivos
            name_lower = name.lower()
            print(f"\n  🔍 Analizando columna: '{name}'")
            print(f"     Búsqueda de palabras clave solo en el nombre")

            found = False
            for kw in high_kw:
                if kw in name_lower:
                    detected.append((name, 'alto', 3, kw))
                    print(f"     ✅ Coincidencia ALTO: palabra clave '{kw}' -> peso=3")
                    found = True
                    break
            if found:
                continue

            for kw in medium_kw:
                if kw in name_lower:
                    detected.append((name, 'medio', 2, kw))
                    print(f"     ✅ Coincidencia MEDIO: palabra clave '{kw}' -> peso=2")
                    found = True
                    break
            if found:
                continue

            for kw in low_kw:
                if kw in name_lower:
                    detected.append((name, 'bajo', 1, kw))
                    print(f"     ✅ Coincidencia BAJO: palabra clave '{kw}' -> peso=1")
                    found = True
                    break
            
            if not found:
                print(f"     ❌ No hay coincidencia (columna no sensible)")

        N_conf = len(detected)
        print(f"\n📊 RESUMEN DE DETECCIONES")
        print(f"Columnas marcadas como confidenciales: {N_conf}/{total_columns}")
        if N_conf > 0:
            for col_name, nivel, peso, keyword in detected:
                print(f"  ✓ '{col_name}': nivel={nivel}, peso={peso} (detectada por: '{keyword}')")
        else:
            print("  - Ninguna columna confidencial detectada")

        if total_columns == 0:
            print("No hay columnas en metadata -> retorno 10.0 por defecto")
            return 10.0

        propConf = N_conf / total_columns
        riesgo_total = sum(peso for (_, _, peso, _) in detected)

        print(f"\n📐 CÁLCULO DE LA MÉTRICA")
        print(f"  propConf = {N_conf} / {total_columns} = {propConf:.4f}")
        print(f"  riesgo_total = {riesgo_total}")
        print(f"  Fórmula: score = max(0, 10 - (propConf × riesgo_total))")
        print(f"           score = max(0, 10 - ({propConf:.4f} × {riesgo_total}))")
        print(f"           score = max(0, 10 - {propConf * riesgo_total:.4f})")

        if N_conf == 0:
            score = 10.0
            print(f"  ✅ Sin columnas confidenciales -> score = 10.0")
        else:
            score = max(0.0, 10.0 - (propConf * riesgo_total))
            print(f"  📊 Score confidencialidad = {score:.2f}")

        print(f"\n🎯 RESULTADO FINAL: {score:.2f}")
        return float(score)

    def calculate_relevancia(self) -> float:
        medida_categoria = 7.0

        medida_filas = 10.0 if self.df_filas > 50 else (self.df_filas / 50) * 10

        relevancia = (medida_categoria + medida_filas) / 2

        return max(0, min(10, relevancia))
    

    
    def calculate_trazabilidad(self) -> float:
        metadatos_requeridos = [
            'titulo', 'descripcion', 'fecha_actualizacion', 'fuente',
            'publicador', 'frecuencia_actualizacion_dias'
        ]

        metadatos_diligenciados = sum(1 for campo in metadatos_requeridos if self.metadata.get(campo))
        total_metadatos = len(metadatos_requeridos)
        proporcion_diligenciados = metadatos_diligenciados / total_metadatos

        proporcion_faltante = 1 - proporcion_diligenciados
        medida_prop_meta_diligenciados = 10 * (1 - proporcion_faltante ** 2)

        metadatos_acceso_auditado = sum(1 for campo in ['fuente', 'publicador', 'licencia']
                                       if self.metadata.get(campo))
        medida_meta_acceso_auditado = (metadatos_acceso_auditado / 3) * 10

        titulo = self.metadata.get('titulo', '')
        tiene_fecha_en_titulo = bool(re.search(r'\d{4}', titulo))
        medida_titulo_sin_fecha = 0.0 if tiene_fecha_en_titulo else 10.0

        trazabilidad = (medida_prop_meta_diligenciados * 0.75 +
                       medida_meta_acceso_auditado * 0.20 +
                       medida_titulo_sin_fecha * 0.05)

        return max(0, min(10, trazabilidad))

    def calculate_conformidad(self) -> float:
        total_valores_validados = 0
        num_valores_incorrectos = 0

        for col in self.df.columns:
            if self.df[col].dtype in ['int64', 'float64']:
                valores_negativos_incorrectos = ((self.df[col] < 0) & self.df[col].notna()).sum()
                num_valores_incorrectos += valores_negativos_incorrectos
                total_valores_validados += self.df[col].notna().sum()

            elif self.df[col].dtype == 'object':
                valores_vacios = (self.df[col].str.strip() == '').sum()
                num_valores_incorrectos += valores_vacios
                total_valores_validados += self.df[col].notna().sum()

        if total_valores_validados == 0:
            return 10.0

        proporcion_errores = num_valores_incorrectos / total_valores_validados
        conformidad = 10 * math.exp(-5 * proporcion_errores)

        return max(0, min(10, conformidad))

    def _calcular_similitud_texto(self, texto1: str, texto2: str) -> float:
        if not texto1 or not texto2:
            return 0.0

        vectorizer = TfidfVectorizer()
        try:
            tfidf = vectorizer.fit_transform([texto1, texto2])
            similitud = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return similitud
        except:
            return 0.0

    def calculate_exactitud_sintactica(self) -> float:
        num_col_valores_unicos_similares = 0

        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                valores_unicos = self.df[col].dropna().unique()

                if len(valores_unicos) > 1:
                    valores_normalizados = [str(v).lower().strip() for v in valores_unicos]

                    tiene_similares = False
                    for i in range(len(valores_normalizados)):
                        for j in range(i + 1, len(valores_normalizados)):
                            if self._calcular_similitud_texto(valores_normalizados[i], valores_normalizados[j]) > 0.85:
                                tiene_similares = True
                                break
                        if tiene_similares:
                            break

                    if tiene_similares:
                        num_col_valores_unicos_similares += 1

        if self.df_columnas == 0:
            return 10.0

        exactitud_sintactica = 10 * (1 - (num_col_valores_unicos_similares / self.df_columnas) ** 2)

        return max(0, min(10, exactitud_sintactica))

    def calculate_exactitud_semantica(self) -> float:
        num_col_no_sim_semantica = 0

        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                col_nombre = str(col)
                col_descripcion = self.metadata.get('columnas', {}).get(col, {}).get('descripcion', col_nombre)

                valores_sample = self.df[col].dropna().astype(str).head(10).tolist()
                texto_valores = ' '.join(valores_sample)

                similitud = self._calcular_similitud_texto(col_nombre + ' ' + col_descripcion, texto_valores)

                if similitud < 0.3:
                    num_col_no_sim_semantica += 1

        if self.df_columnas == 0:
            return 10.0

        exactitud_semantica = 10 - (10 * (num_col_no_sim_semantica / self.df_columnas) ** 2)

        return max(0, min(10, exactitud_semantica))

    def calculate_completitud(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de Completitud siguiendo la Guía de Calidad e Interoperabilidad 2025.
        VERSIÓN OPTIMIZADA para datasets grandes.
        
        Mide cuánto están completos los datos en filas y columnas, considerando:
        - Correspondencia con columnas esperadas según metadata
        - Proporción de celdas nulas/vacías (operaciones vectorizadas)
        - Columnas con alto porcentaje de nulos (umbral: 50%)
        
        Fórmula:
        Completitud = (medidaCompletitudDatos + medidaCompletitudCol + medidaColNoVacias) / 3
        
        Donde:
        - medidaCompletitudDatos = 10 × (1 - (totalNulos / totalCeldas)^1.5)
        - medidaCompletitudCol = 10 × (1 - (numColPorcNulos / totalColumnas)^2)
        - medidaColNoVacias = 10 × (totalColumnasMetadata / totalColumnas)
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles del cálculo
        
        Returns:
            float: Score entre 0 y 10, donde 10 = dataset completamente completo
        """
        metadata = metadata or self.metadata or {}
        
        if verbose:
            print("\n=== DEBUG COMPLETITUD ===")
            print("Metadata recibida para completitud:")
            try:
                print(json.dumps(metadata, indent=2, ensure_ascii=False))
            except Exception:
                print(metadata)
        
        # Validar que tengamos datos cargados
        if self.df is None or len(self.df) == 0:
            print("⚠️  No hay datos cargados. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        total_filas = len(self.df)
        total_columnas_actuales = len(self.df.columns)
        total_celdas = total_filas * total_columnas_actuales
        
        # Contar nulos totales iterando sobre cada columna
        total_nulos = 0
        for col in self.df.columns:
            total_nulos += self.df[col].isna().sum()
        
        print(f"\n📊 INFORMACIÓN DEL DATASET ANALIZADO")
        print(f"  ✓ Total de registros (filas) analizados: {total_filas}")
        print(f"  ✓ Total de columnas: {total_columnas_actuales}")
        print(f"  ✓ Total celdas (filas × columnas): {total_celdas}")
        print(f"  ✓ Total celdas nulas/vacías: {total_nulos}")
        
        # Información de metadata
        columnas_metadata = metadata.get('columns') or []
        total_columnas_metadata = len(columnas_metadata)
        
        print(f"  ✓ Total columnas esperadas en metadata: {total_columnas_metadata}")
        
        # ===== MEDIDA 1: Completitud de Datos =====
        if total_celdas == 0:
            medida_completitud_datos = 10.0
            proporcion_nulos = 0.0
        else:
            proporcion_nulos = total_nulos / total_celdas
            # Aplicar exponente 1.5 para penalizar más fuertemente los nulos
            medida_completitud_datos = 10 * (1 - (proporcion_nulos ** 1.5))
        
        print(f"\n📐 MEDIDA 1: Completitud de Datos")
        print(f"  Proporción de nulos: {proporcion_nulos:.4f} ({total_nulos}/{total_celdas})")
        print(f"  Fórmula: 10 × (1 - ({proporcion_nulos:.4f})^1.5)")
        print(f"  Resultado: {medida_completitud_datos:.2f}")
        
        # ===== MEDIDA 2: Completitud de Columnas =====
        umbral_nulos_porciento = 0.50  # 50%
        num_col_porciento_nulos = 0
        columnas_con_alto_nulos = []
        
        for col in self.df.columns:
            nulos_col = self.df[col].isna().sum()
            porciento_nulos = nulos_col / total_filas if total_filas > 0 else 0
            
            if porciento_nulos > umbral_nulos_porciento:
                num_col_porciento_nulos += 1
                columnas_con_alto_nulos.append((col, porciento_nulos * 100, nulos_col))
        
        if total_columnas_actuales == 0:
            medida_completitud_col = 10.0
        else:
            medida_completitud_col = 10 * (1 - (num_col_porciento_nulos / total_columnas_actuales) ** 2)
        
        print(f"\n📐 MEDIDA 2: Completitud de Columnas")
        print(f"  Umbral de nulos por columna: {umbral_nulos_porciento * 100:.0f}%")
        print(f"  Columnas con alto % de nulos: {num_col_porciento_nulos}/{total_columnas_actuales}")
        
        for col_name, pct, nulos in columnas_con_alto_nulos:
            print(f"    ✗ '{col_name}': {pct:.1f}% nulos ({nulos} valores)")
        
        print(f"  Fórmula: 10 × (1 - ({num_col_porciento_nulos}/{total_columnas_actuales})^2)")
        print(f"  Resultado: {medida_completitud_col:.2f}")
        
        # ===== MEDIDA 3: Correspondencia Metadata-Dataset =====
        if total_columnas_actuales == 0:
            medida_col_no_vacias = 0.0
        else:
            # Proporción de columnas de metadata vs columnas actuales
            medida_col_no_vacias = 10 * (total_columnas_metadata / total_columnas_actuales)
        
        print(f"\n📐 MEDIDA 3: Correspondencia Metadata-Dataset")
        print(f"  Fórmula: 10 × ({total_columnas_metadata} / {total_columnas_actuales})")
        print(f"  Resultado: {medida_col_no_vacias:.2f}")
        
        # ===== CÁLCULO FINAL =====
        completitud = (medida_completitud_datos + medida_completitud_col + medida_col_no_vacias) / 3
        completitud = max(0, min(10, completitud))
        
        print(f"\n🎯 RESULTADO FINAL DE COMPLETITUD")
        print(f"  Completitud = ({medida_completitud_datos:.2f} + {medida_completitud_col:.2f} + {medida_col_no_vacias:.2f}) / 3")
        print(f"  Completitud = {completitud:.2f}")
        
        return float(completitud)

    def calculate_consistencia(self) -> float:
        exactitud_sintactica = self.calculate_exactitud_sintactica()

        num_col_inconsistentes = 0
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                longitudes = self.df[col].dropna().astype(str).str.len()
                if longitudes.std() > longitudes.mean() * 0.5:
                    num_col_inconsistentes += 1

        medida_consistencia_car = 10 * (1 - (num_col_inconsistentes / self.df_columnas) ** 2) if self.df_columnas > 0 else 10.0

        col_nombres_lower = [str(col).lower().strip() for col in self.df.columns]
        num_duplicadas = len(col_nombres_lower) - len(set(col_nombres_lower))
        atributo_nombres_col_duplicadas = 10 * (1 - num_duplicadas / self.df_columnas) if self.df_columnas > 0 else 10.0

        consistencia = (exactitud_sintactica + medida_consistencia_car + atributo_nombres_col_duplicadas) / 3

        return max(0, min(10, consistencia))

    def calculate_precision(self) -> float:
        columnas_cumplen_criterios = 0

        for col in self.df.columns:
            if self.df[col].dtype in ['int64', 'float64']:
                varianza = self.df[col].var()
                valores_unicos = self.df[col].nunique()

                if varianza > 0.1 and valores_unicos >= 2:
                    columnas_cumplen_criterios += 1
            else:
                valores_unicos = self.df[col].nunique()
                if valores_unicos >= 2:
                    columnas_cumplen_criterios += 1

        if self.df_columnas == 0:
            return 10.0

        precision = (columnas_cumplen_criterios / self.df_columnas) * 10

        return max(0, min(10, precision))

    def calculate_portabilidad(self) -> float:
        num_caracteres_especiales = 0
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                caracteres_especiales = self.df[col].astype(str).str.contains(r'[^\w\s\.,;:\-\(\)]', regex=True).sum()
                num_caracteres_especiales += caracteres_especiales

        total_celdas_texto = sum(1 for col in self.df.columns if self.df[col].dtype == 'object') * self.df_filas
        medida_caracteres = 10 * (1 - num_caracteres_especiales / total_celdas_texto) if total_celdas_texto > 0 else 10.0

        total_nulos = self.df.isna().sum().sum()
        total_celdas = self.df_columnas * self.df_filas
        medida_sin_nulos = 10 * (1 - total_nulos / total_celdas) if total_celdas > 0 else 10.0

        tamano_mb = self.df.memory_usage(deep=True).sum() / (1024 * 1024)
        if tamano_mb < 10:
            medida_tamano = 10.0
        elif tamano_mb < 50:
            medida_tamano = 7.0
        else:
            medida_tamano = 5.0

        portabilidad_base = (medida_caracteres + medida_sin_nulos + medida_tamano) / 3

        conformidad = self.calculate_conformidad()
        completitud = self.calculate_completitud()

        total_portabilidad = (portabilidad_base * 0.50 + conformidad * 0.25 + completitud * 0.25)

        return max(0, min(10, total_portabilidad))

    def calculate_credibilidad(self) -> float:
        metadatos_fuente = ['fuente', 'descripcion', 'fecha_actualizacion']
        metadatos_completos = sum(1 for campo in metadatos_fuente if self.metadata.get(campo))
        medida_metadatos_completos = (metadatos_completos / len(metadatos_fuente)) * 10

        publicador = self.metadata.get('publicador', '')
        medida_publicador_valido = 10.0 if len(publicador) > 0 else 0.0

        columnas_con_desc = sum(1 for col in self.df.columns
                               if self.metadata.get('columnas', {}).get(col, {}).get('descripcion'))
        medida_col_desc_valida = (columnas_con_desc / self.df_columnas) * 10 if self.df_columnas > 0 else 0.0

        credibilidad = (medida_metadatos_completos * 0.70 +
                       medida_publicador_valido * 0.05 +
                       medida_col_desc_valida * 0.25)

        return max(0, min(10, credibilidad))

    def calculate_comprensibilidad(self) -> float:
        descripcion = self.metadata.get('descripcion', '')
        length_desc = len(descripcion)
        puntaje_medida_desc_ext = 10 * (1 - math.exp(-0.05 * length_desc))

        etiqueta_fila = self.metadata.get('etiqueta_fila', '')
        length_etiqueta = len(etiqueta_fila)
        max_length = 100

        if length_etiqueta <= 2:
            puntaje_medida_etiqueta_fila = 0.0
        else:
            puntaje_medida_etiqueta_fila = 10 * (math.log(1 + (length_etiqueta - 2)) /
                                                 math.log(1 + (max_length - 2)))

        comprensibilidad = (puntaje_medida_desc_ext + puntaje_medida_etiqueta_fila) / 2

        return max(0, min(10, comprensibilidad))

    def calculate_accesibilidad(self) -> float:
        cantidad_etiquetas = len(self.metadata.get('tags', []))
        puntaje_tags = 5.0 if cantidad_etiquetas > 0 else 0.0

        cantidad_vinculos = len(self.metadata.get('attribution_links', []))
        puntaje_link = 5.0 if cantidad_vinculos > 0 else 0.0

        accesibilidad = puntaje_tags + puntaje_link

        return max(0, min(10, accesibilidad))

    def calculate_unicidad(self) -> float:
        filas_duplicadas = self.df.duplicated().sum()
        proporcion_filas_duplicadas = 10 * (1 - filas_duplicadas / self.df_filas) if self.df_filas > 0 else 10.0

        col_nombres_lower = [str(col).lower().strip() for col in self.df.columns]
        num_col_duplicadas = len(col_nombres_lower) - len(set(col_nombres_lower))
        proporcion_columnas_duplicadas = 10 * (1 - num_col_duplicadas / self.df_columnas) if self.df_columnas > 0 else 10.0

        unicidad = (proporcion_filas_duplicadas + proporcion_columnas_duplicadas) / 2

        return max(0, min(10, unicidad))

    def calculate_eficiencia(self) -> float:
        completitud = self.calculate_completitud()

        filas_duplicadas = self.df.duplicated().sum()
        medida_filas_duplicadas = 10 * (1 - filas_duplicadas / self.df_filas) if self.df_filas > 0 else 10.0

        col_nombres_lower = [str(col).lower().strip() for col in self.df.columns]
        num_col_duplicadas = len(col_nombres_lower) - len(set(col_nombres_lower))
        medida_columnas_duplicadas = 10 * (1 - num_col_duplicadas / self.df_columnas) if self.df_columnas > 0 else 10.0

        eficiencia = (completitud + medida_filas_duplicadas + medida_columnas_duplicadas) / 3

        return max(0, min(10, eficiencia))

    def calculate_unicidad(self, nivel_riesgo: float = 1.5) -> float:
        """
        Calcula el índice de Unicidad del dataset.
        
        Evalúa la presencia de datos duplicados:
        - Filas duplicadas: Filas con exactamente los mismos valores en todas las columnas
        - Columnas duplicadas: Columnas con exactamente los mismos valores en todas las filas
        
        Fórmula:
        unicidad = [(1 - proporcion_filas_dup)^nivel_riesgo + (1 - proporcion_columnas_dup)^nivel_riesgo] / 2 * 10
        
        Args:
            nivel_riesgo: Parámetro para ajustar penalización (default = 1.5)
                - 1.0: Penalización suave
                - 1.5: Penalización media (RECOMENDADO)
                - 2.0: Penalización estricta
        
        Returns:
            float: Score entre 0 y 10, donde 10 = sin duplicados
        """
        # Validar que tengamos datos cargados
        if self.df is None or len(self.df) == 0:
            print("⚠️  No hay datos cargados. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        total_filas = len(self.df)
        total_columnas = len(self.df.columns)
        
        # ===== DETECCIÓN DE FILAS DUPLICADAS =====
        filas_duplicadas = self.df.duplicated().sum()
        proporcion_filas_dup = filas_duplicadas / total_filas if total_filas > 0 else 0
        
        print(f"\n📊 INFORMACIÓN DEL DATASET PARA UNICIDAD")
        print(f"  ✓ Total de registros (filas): {total_filas}")
        print(f"  ✓ Filas duplicadas exactas: {filas_duplicadas}")
        print(f"  ✓ Proporción de filas duplicadas: {proporcion_filas_dup:.4f} ({proporcion_filas_dup*100:.2f}%)")
        print(f"  ✓ Total de columnas: {total_columnas}")
        
        # ===== DETECCIÓN DE COLUMNAS DUPLICADAS =====
        columnas_duplicadas = 0
        
        for i in range(len(self.df.columns)):
            for j in range(i + 1, len(self.df.columns)):
                col_i = self.df.iloc[:, i]
                col_j = self.df.iloc[:, j]
                
                # Comparar columnas (ignorando NaN en la comparación)
                if col_i.equals(col_j) or (col_i.isna() == col_j.isna()).all() and \
                   (col_i.dropna().equals(col_j.dropna()) if len(col_i.dropna()) > 0 else True):
                    columnas_duplicadas += 1
        
        proporcion_columnas_dup = columnas_duplicadas / total_columnas if total_columnas > 0 else 0
        
        print(f"  ✓ Columnas duplicadas exactas: {columnas_duplicadas}")
        print(f"  ✓ Proporción de columnas duplicadas: {proporcion_columnas_dup:.4f} ({proporcion_columnas_dup*100:.2f}%)")
        
        # ===== CÁLCULO DE UNICIDAD =====
        medida_filas = (1 - proporcion_filas_dup) ** nivel_riesgo
        medida_columnas = (1 - proporcion_columnas_dup) ** nivel_riesgo
        
        unicidad = ((medida_filas + medida_columnas) / 2) * 10
        unicidad = max(0, min(10, unicidad))
        
        print(f"\n📐 CÁLCULO DE UNICIDAD (nivel_riesgo={nivel_riesgo})")
        print(f"  Medida de filas: (1 - {proporcion_filas_dup:.4f})^{nivel_riesgo} = {medida_filas:.4f}")
        print(f"  Medida de columnas: (1 - {proporcion_columnas_dup:.4f})^{nivel_riesgo} = {medida_columnas:.4f}")
        print(f"  Fórmula: [({medida_filas:.4f} + {medida_columnas:.4f}) / 2] × 10")
        
        print(f"\n🎯 RESULTADO FINAL DE UNICIDAD")
        print(f"  Unicidad = {unicidad:.2f}")
        
        return float(unicidad)

    def calculate_recuperabilidad(self) -> float:
        accesibilidad = self.calculate_accesibilidad()

        metadatos_fuente = ['fuente', 'descripcion', 'fecha_actualizacion', 'publicador']
        metadatos_completos = sum(1 for campo in metadatos_fuente if self.metadata.get(campo))
        medida_metadatos_completos = (metadatos_completos / len(metadatos_fuente)) * 10

        metadatos_auditados = sum(1 for campo in ['fuente', 'publicador', 'licencia']
                                 if self.metadata.get(campo))
        medida_metadatos_auditados = (metadatos_auditados / 3) * 10

        recuperabilidad = (accesibilidad + medida_metadatos_completos + medida_metadatos_auditados) / 3

        return max(0, min(10, recuperabilidad))

    def calculate_disponibilidad(self) -> float:
        accesibilidad = self.calculate_accesibilidad()
        actualidad = self.calculate_actualidad(self.metadata)

        disponibilidad = (accesibilidad + actualidad) / 2

        return max(0, min(10, disponibilidad))

    def calculate_all_scores(self) -> Dict[str, float]:
        return {
            'confidencialidad': self.calculate_confidencialidad(),
            'relevancia': self.calculate_relevancia(),
            'actualidad': self.calculate_actualidad(self.metadata),
            'trazabilidad': self.calculate_trazabilidad(),
            'conformidad': self.calculate_conformidad(),
            'exactitudSintactica': self.calculate_exactitud_sintactica(),
            'exactitudSemantica': self.calculate_exactitud_semantica(),
            'completitud': self.calculate_completitud(),
            'consistencia': self.calculate_consistencia(),
            'precision': self.calculate_precision(),
            'portabilidad': self.calculate_portabilidad(),
            'credibilidad': self.calculate_credibilidad(),
            'comprensibilidad': self.calculate_comprensibilidad(),
            'accesibilidad': self.calculate_accesibilidad(),
            'unicidad': self.calculate_unicidad(),
            'eficiencia': self.calculate_eficiencia(),
            'recuperabilidad': self.calculate_recuperabilidad(),
            'disponibilidad': self.calculate_disponibilidad()
        }
