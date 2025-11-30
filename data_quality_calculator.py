import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sodapy import Socrata
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
        # Cache para llamadas a API Colombia (departments/municipalities)
        self._api_colombia_cache = {
            'departments': None,
            'municipalities': None
        }
        # Lista de respaldo de departamentos (en caso de fallo de la API)
        self._colombia_departments_backup = [
            'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá', 'Caldas',
            'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 'Guainía',
            'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander',
            'Putumayo', 'Quindío', 'Risaralda', 'San Andrés y Providencia', 'Santander', 'Sucre',
            'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada'
        ]

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
        
        # print(f"🔗 Obteniendo datos desde: {base_url}")
        # print(f"📦 Límite configurado: {limit} registros")
        
        all_data = []
        offset = 0
        page_size = 1000  # Máximo por página en Socrata
        total_obtained = 0
        
        try:
            client = Socrata(
                "www.datos.gov.co",
                "sAmoC9S1twqLnpX9YUmmSTqgp",
                username="valen@yopmail.com",
                password="p4wHD7Y.SDGiQmP",
            )

            results = client.get(self.dataset_id, limit=limit)
            # print(f"🎯 Registros obtenidos (sodapy): {len(results)}")

            if results:
                df = pd.DataFrame.from_records(results)
                # set dataframe and derived properties
                self.df = df
                self.df_filas = len(df)
                self.df_columnas = len(df.columns)
                # Try to optimize dtypes if helper exists
                try:
                    self._optimize_dtypes()
                except Exception:
                    pass

                # print(f"📊 DataFrame cargado en calculador: {self.df_filas} filas, {self.df_columnas} columnas")
                return
            else:
                # print("⚠️ No se obtuvieron datos desde Socrata (sodapy)")
                self.df = pd.DataFrame()
                self.df_filas = 0
                self.df_columnas = 0
                return
                
        except Exception as e:
            # print(f"❌ Error cargando datos con sodapy: {e}")
            # Fallback a requests si sodapy falla
            try:
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
                    
            except Exception as e2:
                print(f"❌ Error obteniendo datos con fallback: {e2}")
                self.df = pd.DataFrame()
                self.df_filas = 0
                self.df_columnas = 0
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

        # if verbose:
        #     print("\n=== DEBUG ACTUALIDAD ===")
        #     print("Metadata completa recibida:")
        #     try:
        #         print(json.dumps(metadata, indent=4, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

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
                    # print(f"⚠ No se pudo parsear fecha_actualizacion: {fecha_actualizacion_str}")
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
                    # print(f"✔ Usando rowsUpdatedAt timestamp -> {fecha_actualizacion}")
                except Exception as e:
                    # print(f"⚠ Error parseando rowsUpdatedAt: {e}")
                    pass

        if fecha_actualizacion is None:
            # print("⚠ No se encontró fecha_actualizacion válida -> Puntaje = 5.0")
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
                    # print(f"✔ Frecuencia encontrada en metadata.custom_fields['Información de Datos']: {frecuencia_str}")
                    pass
            
            # Opción 2: campos simples de nivel superior
            if not frecuencia_str:
                frecuencia_str = (metadata.get('updateFrequency') or
                                  metadata.get('frecuencia_actualizacion') or
                                  metadata.get('frecuencia'))
                if frecuencia_str:
                    # print(f"✔ Frecuencia encontrada en campo simple: {frecuencia_str}")
                    pass
            
            # Opción 3: por defecto
            if not frecuencia_str:
                frecuencia_str = 'Anual'
                # print(f"✔ Usando frecuencia por defecto: {frecuencia_str}")
                pass
            
            frecuencia_dias = self._convertir_frecuencia_a_dias(frecuencia_str)

        # print(f"✔ frecuencia original metadata: {frecuencia_str}")
        # print(f"✔ frecuencia normalizada (días): {frecuencia_dias}")

        # # manejo especiales
        # if frecuencia_dias is None:
        #     print("⚠ Frecuencia = 'No aplica' (indeterminado) -> Puntaje = 5.0")
        #     return 5.0
        # if frecuencia_dias == math.inf:
        #     print("ℹ Frecuencia = 'Nunca' -> dataset declarado como nunca actualizado -> Puntaje = 0.0")
        #     return 0.0

        # # caso explícito 'más de tres años' — siempre 10.0
        # # IMPORTANTE: buscar en la misma ubicación donde ya extrajimos frecuencia_str
        # freq_raw = str(frecuencia_str or '').lower()
        # # normalizar: remover acentos y caracteres especiales
        # freq_normalized = re.sub(r'[^a-z0-9\s]', '', freq_raw)
        # print(f"🔍 DEBUG 'más de tres años': freq_raw='{freq_raw}', freq_normalized='{freq_normalized}'")
        # if 'mas' in freq_normalized and 'tres' in freq_normalized and 'anos' in freq_normalized:
        #     print("✅ Frecuencia = 'Más de tres años' -> Puntaje = 10.0")
        #     return 10.0

        # # caso explícito 'solo una vez' — si fue hace <= 5 años consideramos aceptable
        # if 'solo' in freq_raw and 'vez' in freq_raw:
        #     fecha_actual = datetime.now()
        #     diferencia_dias = (fecha_actual - fecha_actualizacion).days
        #     print(f"✔ Días transcurridos: {diferencia_dias} (regla 'solo una vez' umbral=5 años)")
        #     if diferencia_dias <= 5*365:
        #         print("✅ 'Solo una vez' dentro de 5 años -> Puntaje = 10.0")
        #         return 10.0
        #     else:
        #         print("❌ 'Solo una vez' fuera de 5 años -> Puntaje = 0.0")
        #         return 0.0

        # # 3) cálculo normal
        # fecha_actual = datetime.now()
        # diferencia_dias = (fecha_actual - fecha_actualizacion).days
        # print(f"✔ Fecha actual: {fecha_actual}")
        # print(f"✔ Fecha última actualización: {fecha_actualizacion}")
        # print(f"✔ Días transcurridos desde la última actualización: {diferencia_dias}")
        # print(f"✔ Comparación: diferencia_dias ({diferencia_dias}) > frecuencia_dias ({frecuencia_dias}) ?")

        # if diferencia_dias > frecuencia_dias:
        #     print("❌ Desactualizado -> Puntaje = 0.0")
        #     return 0.0
        # else:
        #     print("✅ Dentro de la frecuencia -> Puntaje = 10.0")
        #     return 10.0
        
        # Manejo especiales
        if frecuencia_dias is None:
            return 5.0
        if frecuencia_dias == math.inf:
            return 0.0

        # Caso explícito 'más de tres años'
        freq_raw = str(frecuencia_str or '').lower()
        freq_normalized = re.sub(r'[^a-z0-9\s]', '', freq_raw)
        if 'mas' in freq_normalized and 'tres' in freq_normalized and 'anos' in freq_normalized:
            return 10.0

        # Caso explícito 'solo una vez'
        if 'solo' in freq_raw and 'vez' in freq_raw:
            fecha_actual = datetime.now()
            diferencia_dias = (fecha_actual - fecha_actualizacion).days
            if diferencia_dias <= 5*365:
                return 10.0
            else:
                return 0.0

        # Cálculo normal
        fecha_actual = datetime.now()
        diferencia_dias = (fecha_actual - fecha_actualizacion).days

        if diferencia_dias > frecuencia_dias:
            return 0.0
        else:
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

    def calculate_accesibilidad_from_metadata(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de Accesibilidad usando SOLO metadatos.

        Reglas implementadas (Guía MinTIC 2025 simplificada):
        - puntaje_tags = 5 si hay al menos 1 tag, 0 si no
        - puntaje_link = 5 si se encuentra al menos 1 link de atribución / documentación / normativa
        - accesibilidad = puntaje_tags + puntaje_link (max 10)

        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles

        Returns:
            float: score entre 0 y 10
        """
        metadata = metadata or self.metadata or {}

        # if verbose:
        #     print("\n=== DEBUG ACCESIBILIDAD (METADATA) ===")
        #     print("Metadata recibida para accesibilidad:")
        #     try:
        #         print(json.dumps(metadata, indent=2, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

        # Puntaje tags
        tags = metadata.get('tags') or []
        puntaje_tags = 5.0 if len(tags) > 0 else 0.0

        # Buscar links relevantes
        links = [
            metadata.get('attributionLink'),
            # Algunas APIs embeben info en metadata.custom_fields.*
            metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Documentación'),
            metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Normativa')
        ]
        # Normalizar None/''
        links_found = [l for l in links if l]
        puntaje_link = 5.0 if len(links_found) > 0 else 0.0

        accesibilidad = puntaje_tags + puntaje_link
        accesibilidad = max(0, min(10, accesibilidad))

        # if verbose:
        #     print(f"  ✓ tags_count: {len(tags)} -> puntaje_tags={puntaje_tags}")
        #     print(f"  ✓ links_found: {links_found} -> puntaje_link={puntaje_link}")
        #     print(f"  → accesibilidad (raw) = {accesibilidad}")

        return float(accesibilidad)


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
        
        # if verbose:
        #     print("\n=== DEBUG CONFIDENCIALIDAD (METADATA) ===")
        #     print("Metadata recibida para confidencialidad:")
        #     try:
        #         print(json.dumps(metadata, indent=2, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

        columns_meta = metadata.get('columns') or []
        # columnas pueden venir como lista de dicts con 'name' y 'description'
        total_columns = len(columns_meta)
        # print(f"Total columnas detectadas en metadata: {total_columns}")

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
            # print(f"\n  🔍 Analizando columna: '{name}'")
            # print(f"     Búsqueda de palabras clave solo en el nombre")

            found = False
            for kw in high_kw:
                if kw in name_lower:
                    detected.append((name, 'alto', 3, kw))
                    # print(f"     ✅ Coincidencia ALTO: palabra clave '{kw}' -> peso=3")
                    found = True
                    break
            if found:
                continue

            for kw in medium_kw:
                if kw in name_lower:
                    detected.append((name, 'medio', 2, kw))
                    # print(f"     ✅ Coincidencia MEDIO: palabra clave '{kw}' -> peso=2")
                    found = True
                    break
            if found:
                continue

            for kw in low_kw:
                if kw in name_lower:
                    detected.append((name, 'bajo', 1, kw))
                    # print(f"     ✅ Coincidencia BAJO: palabra clave '{kw}' -> peso=1")
                    found = True
                    break
            
            if not found:
                # print(f"     ❌ No hay coincidencia (columna no sensible)")
                pass

        N_conf = len(detected)
        # print(f"\n📊 RESUMEN DE DETECCIONES")
        # print(f"Columnas marcadas como confidenciales: {N_conf}/{total_columns}")
        # if N_conf > 0:
        #     for col_name, nivel, peso, keyword in detected:
        #         print(f"  ✓ '{col_name}': nivel={nivel}, peso={peso} (detectada por: '{keyword}')") 
        # else:
        #     print("  - Ninguna columna confidencial detectada")

        if total_columns == 0:
            print("No hay columnas en metadata -> retorno 10.0 por defecto")
            return 10.0

        propConf = N_conf / total_columns
        riesgo_total = sum(peso for (_, _, peso, _) in detected)

        # print(f"\n📐 CÁLCULO DE LA MÉTRICA")
        # print(f"  propConf = {N_conf} / {total_columns} = {propConf:.4f}")
        # print(f"  riesgo_total = {riesgo_total}")
        # print(f"  Fórmula: score = max(0, 10 - (propConf × riesgo_total))")
        # print(f"           score = max(0, 10 - ({propConf:.4f} × {riesgo_total}))")
        # print(f"           score = max(0, 10 - {propConf * riesgo_total:.4f})")

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

    def _fetch_colombia_departments(self) -> List[str]:
        """
        Obtiene y cachea la lista de departamentos desde la API Colombia.
        Si falla, retorna la lista de respaldo.
        """
        if self._api_colombia_cache.get('departments'):
            # print("ℹ️ Usando cache local de departamentos (API Colombia)")
            return self._api_colombia_cache['departments']

        url = 'https://api-colombia.com/api/v1/Department'
        try:
            # print(f"🔗 Consultando API Colombia departamentos: {url}")
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                names = []
                if isinstance(data, list):
                    for item in data:
                        # intentar campos comunes
                        name = item.get('name') or item.get('department') or item.get('nombre')
                        if name:
                            names.append(str(name).strip().title())
                # deduplicate and cache
                names = sorted(list(set(names)))
                if names:
                    # print(f"✅ API Colombia devolvió {len(names)} departamentos (cacheados)")
                    self._api_colombia_cache['departments'] = names
                    return names
                else:
                    # print("⚠️ API Colombia devolvió lista vacía de departamentos")
                    pass
        except Exception as e:
            # print(f"⚠️ Error llamando API Colombia departamentos: {e}")
            pass

        # fallback
        backup = [d.title() for d in self._colombia_departments_backup]
        # print(f"🔁 Usando fallback local de departamentos ({len(backup)} entradas)")
        self._api_colombia_cache['departments'] = backup
        return backup

    def _fetch_colombia_municipalities(self) -> Optional[set]:
        """
        Intenta obtener municipios desde la API usando el endpoint por departamento.
        Devuelve un set de nombres normalizados o None si no es posible.
        """
        if self._api_colombia_cache.get('municipalities') is not None:
            # print("ℹ️ Usando cache local de municipios (API Colombia)")
            return self._api_colombia_cache['municipalities']

        try:
            # Cache de departamentos para reutilizar
            if self._api_colombia_cache.get('departments') is None:
                dept_url = 'https://api-colombia.com/api/v1/Department'
                dept_resp = requests.get(dept_url, timeout=10)
                
                if dept_resp.status_code != 200:
                    self._api_colombia_cache['municipalities'] = None
                    return None

                departamentos = dept_resp.json()
                if not isinstance(departamentos, list):
                    self._api_colombia_cache['municipalities'] = None
                    return None
                    
                self._api_colombia_cache['departments'] = departamentos
            else:
                departamentos = self._api_colombia_cache['departments']

            all_municipalities = set()
            successful_depts = 0
            
            # Limitar a los primeros 10 departamentos para pruebas (opcional)
            for dept in departamentos[:]:  # Remover [:] para todos los departamentos
                dept_id = dept.get('id')
                dept_name = dept.get('name', 'Desconocido')
                
                if not dept_id:
                    continue
                    
                # Obtener municipios del departamento actual
                mun_url = f'https://api-colombia.com/api/v1/Department/{dept_id}/cities'
                try:
                    mun_resp = requests.get(mun_url, timeout=6)
                    if mun_resp.status_code == 200:
                        municipios = mun_resp.json()
                        if isinstance(municipios, list):
                            mun_count = 0
                            for municipio in municipios:
                                name = municipio.get('name')
                                if name:
                                    all_municipalities.add(str(name).strip().title())
                                    mun_count += 1
                            
                            successful_depts += 1
                            # print(f"  📍 {dept_name}: {mun_count} municipios")
                    
                except requests.exceptions.Timeout:
                    # print(f"⏰ Timeout en {dept_name}")
                    continue
                except Exception as e:
                    # print(f"⚠️ Error en {dept_name}: {e}")
                    continue

            if all_municipalities:
                # print(f"✅ Obtenidos {len(all_municipalities)} municipios de {successful_depts}/{len(departamentos)} departamentos")
                self._api_colombia_cache['municipalities'] = all_municipalities
                return all_municipalities
            else:
                # print("❌ No se pudieron obtener municipios")
                self._api_colombia_cache['municipalities'] = None
                return None

        except Exception as e:
            # print(f"❌ Error crítico: {e}")
            self._api_colombia_cache['municipalities'] = None
            return None
    def _detect_relevant_columns(self, metadata: Optional[Dict] = None) -> Dict[str, List[str]]:
        """
        Detecta columnas relevantes a partir de metadata o de self.df
        Retorna un dict tipo -> lista de nombres de columnas encontradas
        Tipos: departamento, municipio, año, latitud, longitud, correo
        """
        metadata = metadata or self.metadata or {}
        detected = {'departamento': [], 'municipio': [], 'año': [], 'latitud': [], 'longitud': [], 'correo': []}

        # Obtener lista de nombres desde metadata o desde df
        cols = []
        if metadata.get('columns'):
            for c in metadata.get('columns'):
                if isinstance(c, dict):
                    name = c.get('name') or c.get('fieldName')
                else:
                    name = c
                if name:
                    cols.append(str(name))
        if not cols and self.df is not None:
            cols = [str(c) for c in self.df.columns]

        patterns = {
            'departamento': ['departamento', 'depto', 'department', 'departament'],
            'municipio': ['municipio', 'ciudad', 'city', 'municipality'],
            'año': ['año', 'year', 'anio', 'ano'],
            'latitud': ['latitud', 'latitude', 'lat'],
            'longitud': ['longitud', 'longitude', 'lon', 'long'],
            'correo': ['correo', 'email', 'mail']
        }

        for col in cols:
            col_lower = str(col).lower()
            for key, pats in patterns.items():
                for p in pats:
                    if p in col_lower:
                        detected[key].append(col)
                        break

        # deduplicate
        for k in detected:
            detected[k] = list(dict.fromkeys(detected[k]))

        # # Debug print de columnas detectadas
        # print("🔎 Columnas detectadas por tipo:")
        # for k, v in detected.items():
        #     print(f"   - {k}: {v}")

        return detected

    def calculate_conformidad_from_metadata_and_data(self, metadata: Optional[Dict] = None, verbose: bool = True) -> Optional[float]:
        """
        Implementación avanzada de Conformidad según requerimientos.
        Retorna score en rango 0-1 (math.exp(-5 * (errores/total_validos))).
        Si no hay columnas relevantes o no hay datos validados, retorna None.
        """
        metadata = metadata or self.metadata or {}

        # if verbose:
        #     print("\n=== DEBUG CONFORMIDAD AVANZADA ===")

        # # Mostrar resumen de metadata recibida (claves importantes)
        # if verbose:
        #     try:
        #         cols_meta = metadata.get('columns') or []
        #         print(f"🛈 Metadata summary: name={metadata.get('name')}, id={metadata.get('id')}, columns_in_metadata={len(cols_meta)}")
        #     except Exception:
        #         print("🛈 Metadata summary: (no se pudo leer resumen)")

        detected = self._detect_relevant_columns(metadata)
        # Flatten detected columns list and check if any present
        any_found = any(len(v) > 0 for v in detected.values())
        if not any_found:
            # if verbose:
            #     print("⚠️ No se detectaron columnas relevantes para conformidad")
            return None

        # Require data present
        if self.df is None or len(self.df) == 0:
            # if verbose:
            #     print("⚠️ No hay datos cargados para validar conformidad")
            return None

        # Fetch reference data (and print what we received)
        departments_ref = set(self._fetch_colombia_departments())
        # print(f"📚 Referencia departamentos: {len(departments_ref)} items (ejemplo: {list(departments_ref)[:5]})")
        municipalities_ref = self._fetch_colombia_municipalities()
        # if municipalities_ref is None:
        #     print("📚 Referencia municipios: NO DISPONIBLE (se omitirá validación municipal)")
        # else:
        #     print(f"📚 Referencia municipios: {len(municipalities_ref)} items (ejemplo: {list(municipalities_ref)[:5]})")

        email_re = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")

        total_valids = 0
        total_errors = 0
        per_column = []

        # Helper to normalize text
        def normalize_title(v):
            try:
                return str(v).strip().title()
            except Exception:
                return str(v).strip()

        # For each detected column type, validate values
        for ctype, cols in detected.items():
            for col in cols:
                col_series = self.df.get(col)
                if col_series is None:
                    continue
                # # Print column diagnostics
                # try:
                #     dtype = str(col_series.dtype)
                #     non_null_mask = col_series.notna()
                #     col_values = col_series[non_null_mask]
                #     non_null_count = int(col_values.shape[0])
                #     unique_count = int(col_values.nunique(dropna=True))
                #     sample_vals = col_values.head(5).astype(str).tolist()
                #     try:
                #         top_counts = col_values.astype(str).value_counts().head(5).to_dict()
                #     except Exception:
                #         top_counts = {}
                #     print(f"\n➡ Validando columna='{col}' tipo_detectado={ctype} dtype={dtype} non_null={non_null_count} unique={unique_count}")
                #     print(f"   • Muestra head: {sample_vals}")
                #     print(f"   • Top valores: {top_counts}")
                # except Exception as e:
                #     print(f"⚠️ Error al obtener diagnosticos de columna {col}: {e}")

                non_null_mask = col_series.notna()
                col_values = col_series[non_null_mask]
                total = int(col_values.shape[0])
                errors = 0
                bad_examples = []

                if total == 0:
                    # nothing to validate for this column
                    per_column.append({'column': col, 'type': ctype, 'total': 0, 'errors': 0, 'examples': []})
                    continue

                if ctype == 'departamento':
                    for v in col_values.astype(str):
                        total_valids += 1
                        nv = normalize_title(v)
                        if nv not in departments_ref:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'municipio':
                    # Only validate if municipalities_ref available
                    if municipalities_ref is None:
                        # skip counting these rows as validated
                        if verbose:
                            print(f"ℹ️ Municipio validation not available; skipping column {col} from counts")
                        continue
                    for v in col_values.astype(str):
                        total_valids += 1
                        nv = normalize_title(v)
                        if nv not in municipalities_ref:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'año':
                    for v in col_values:
                        total_valids += 1
                        try:
                            n = int(str(v).strip())
                            if n < 1900 or n > 2025:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'latitud':
                    for v in col_values:
                        total_valids += 1
                        try:
                            f = float(str(v).strip())
                            if f < 0 or f > 13:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'longitud':
                    for v in col_values:
                        total_valids += 1
                        try:
                            f = float(str(v).strip())
                            if f < -81 or f > -66:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'correo':
                    for v in col_values.astype(str):
                        total_valids += 1
                        if not email_re.match(v.strip()):
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                total_errors += errors
                per_column.append({'column': col, 'type': ctype, 'total': total, 'errors': errors, 'examples': bad_examples})
                # print per-column result
                print(f"   → Resultado columna='{col}': total_validados={total}, errores={errors}, ejemplos_errores={bad_examples}")

        if total_valids == 0:
            if verbose:
                print("⚠️ No hay valores válidos para calcular conformidad")
            return None

        proporcion_errores = total_errors / total_valids
        score = math.exp(-5 * proporcion_errores)

        if verbose:
            print(f"✔ Total validados: {total_valids}, errores: {total_errors}, proporcion={proporcion_errores:.4f}")
            print(f"✔ Score (0-1): {score:.4f}")

        details = {
            'columns_validated': per_column,
            'total_validated': total_valids,
            'total_errors': total_errors,
            'error_rate': proporcion_errores
        }

        # Guardar en cache simple por si se reusa (no persistente entre ejecuciones)
        self.cached_scores['conformidad_advanced'] = {'score': score, 'details': details}

        return float(score)

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
        print("\n" + "="*70)
        print("🔍 INICIO DEL CÁLCULO DE UNICIDAD")
        print("="*70)
        
        # Validar que tengamos datos cargados
        if self.df is None or len(self.df) == 0:
            print("⚠️  No hay datos cargados. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        total_filas = len(self.df)
        total_columnas = len(self.df.columns)
        
        print(f"\n📦 INFORMACIÓN BÁSICA DEL DATASET")
        print(f"   • Total de filas (registros): {total_filas}")
        print(f"   • Total de columnas: {total_columnas}")
        print(f"   • Tamaño del dataset: {total_filas} x {total_columnas}")
        
        # ===== DETECCIÓN DE FILAS DUPLICADAS =====
        print(f"\n🔎 PASO 1: DETECCIÓN DE FILAS DUPLICADAS")
        print(f"   Analizando si hay filas con exactamente los mismos valores en TODAS las columnas...")

        # Construir claves serializables por fila para evitar errores con tipos no hashables
        def _cell_key(x):
            try:
                # pandas NA handling
                if pd.isna(x):
                    return None
            except Exception:
                pass
            try:
                # Intentar serializar con json para dicts/lists/u otros
                return json.dumps(x, sort_keys=True, default=str, ensure_ascii=False)
            except Exception:
                return str(x)

        try:
            row_keys = self.df.apply(lambda r: tuple(_cell_key(c) for c in r), axis=1)
            filas_duplicadas = int(row_keys.duplicated().sum())
        except Exception as e:
            # Fallback: intentar llamada segura por filas
            print(f"⚠️ Error construyendo claves de fila para detección: {e}")
            filas_duplicadas = int(self.df.duplicated().sum())

        proporcion_filas_dup = filas_duplicadas / total_filas if total_filas > 0 else 0

        print(f"\n   ✓ Filas duplicadas encontradas: {filas_duplicadas}")
        print(f"   ✓ Proporción de duplicados: {proporcion_filas_dup:.6f}")
        print(f"   ✓ Porcentaje de duplicados: {proporcion_filas_dup*100:.4f}%")
        print(f"   ✓ Filas ÚNICAS: {total_filas - filas_duplicadas}")
        print(f"   ✓ Tasa de unicidad (filas): {((1 - proporcion_filas_dup)*100):.4f}%")

        # Mostrar ejemplos de filas duplicadas si las hay
        if filas_duplicadas > 0:
            print(f"\n   ⚠️  ADVERTENCIA: Se encontraron {filas_duplicadas} filas duplicadas")
            try:
                duplicated_mask = row_keys.duplicated(keep=False)
                dup_rows = self.df[duplicated_mask]
                print(f"   Mostrando hasta 3 ejemplos de filas duplicadas:")
                for idx, row in dup_rows.head(3).iterrows():
                    try:
                        print(f"      - Fila {idx}: {dict(row)}")
                    except Exception:
                        print(f"      - Fila {idx}: (no se pudo serializar fila)")
            except Exception as e:
                print(f"      Error mostrando ejemplos: {e}")
        else:
            print(f"   ✅ NO se encontraron filas duplicadas - Excelente!")
        
        # ===== DETECCIÓN DE COLUMNAS DUPLICADAS =====
        print(f"\n🔎 PASO 2: DETECCIÓN DE COLUMNAS DUPLICADAS")
        print(f"   Analizando si hay columnas con exactamente los mismos valores en TODAS las filas...")
        
        columnas_duplicadas = 0
        pares_duplicados = []
        columnas_unicas = set()
        
        # Método CORREGIDO para detectar columnas duplicadas
        print(f"   Comparando todas las combinaciones de columnas...")
        print(f"   Total de comparaciones a hacer: {(total_columnas * (total_columnas - 1)) // 2}")
        
        # Construir claves serializables para cada columna (para evitar problemas con dtypes complejos)
        print(f"   Construyendo claves serializables por columna para comparación robusta...")
        column_keys = {}
        try:
            for col_name in self.df.columns:
                # serializar cada valor de la columna usando _cell_key definido arriba
                try:
                    col_vals = self.df[col_name]
                    col_key = tuple(_cell_key(v) for v in col_vals)
                except Exception:
                    # Fallback: convertir a string
                    col_key = tuple(str(v) for v in self.df[col_name].astype(object).fillna('NaN'))
                column_keys[col_name] = col_key
        except Exception as e:
            print(f"      ⚠️ Error construyendo claves de columna: {e}")

        # Comparar claves de columna en pares
        for i in range(len(self.df.columns)):
            col_i_name = self.df.columns[i]

            # Si esta columna ya fue marcada como duplicada, saltar
            if col_i_name in columnas_unicas:
                continue

            for j in range(i + 1, len(self.df.columns)):
                col_j_name = self.df.columns[j]

                # Si esta columna ya fue marcada como duplicada, saltar
                if col_j_name in columnas_unicas:
                    continue

                try:
                    key_i = column_keys.get(col_i_name)
                    key_j = column_keys.get(col_j_name)

                    if key_i is None or key_j is None:
                        # si no pudimos construir alguna clave, saltar comparación
                        continue

                    if key_i == key_j:
                        columnas_duplicadas += 1
                        pares_duplicados.append((col_i_name, col_j_name))
                        columnas_unicas.add(col_j_name)
                        print(f"      ⚠️  Columnas duplicadas: '{col_i_name}' <-> '{col_j_name}'")
                        continue
                except Exception as e:
                    print(f"      Error comparando '{col_i_name}' con '{col_j_name}': {e}")
        
        # Calcular proporción CORREGIDA
        # La proporción debe ser: columnas_duplicadas / total_columnas_posibles_duplicadas
        if total_columnas > 1:
            # Máximo número posible de columnas duplicadas es total_columnas - 1
            max_posibles_duplicadas = total_columnas - 1
            proporcion_columnas_dup = columnas_duplicadas / max_posibles_duplicadas if max_posibles_duplicadas > 0 else 0
        else:
            proporcion_columnas_dup = 0
        
        print(f"\n   ✓ Columnas duplicadas encontradas: {columnas_duplicadas}")
        print(f"   ✓ Proporción de columnas duplicadas: {proporcion_columnas_dup:.6f}")
        
        if columnas_duplicadas == 0:
            print(f"   ✅ NO se encontraron columnas duplicadas - Excelente!")
        else:
            print(f"   Pares encontrados: {pares_duplicados}")
        
        # ===== CÁLCULO DE UNICIDAD =====
        print(f"\n📐 PASO 3: CÁLCULO DEL SCORE DE UNICIDAD")
        print(f"   Parámetro nivel_riesgo: {nivel_riesgo}")
        
        print(f"\n   Fórmula:")
        print(f"      medida_filas = (1 - proporcion_filas_dup) ^ nivel_riesgo")
        print(f"      medida_columnas = (1 - proporcion_columnas_dup) ^ nivel_riesgo")
        print(f"      unicidad = [(medida_filas + medida_columnas) / 2] × 10")
        
        # Aplicar la fórmula con manejo de casos edge
        medida_filas = (1 - min(proporcion_filas_dup, 1.0)) ** nivel_riesgo
        medida_columnas = (1 - min(proporcion_columnas_dup, 1.0)) ** nivel_riesgo
        
        print(f"\n   Sustituyendo valores:")
        print(f"      medida_filas = (1 - {proporcion_filas_dup:.6f}) ^ {nivel_riesgo}")
        print(f"      medida_filas = {1 - proporcion_filas_dup:.6f} ^ {nivel_riesgo}")
        print(f"      medida_filas = {medida_filas:.6f}")
        
        print(f"\n      medida_columnas = (1 - {proporcion_columnas_dup:.6f}) ^ {nivel_riesgo}")
        print(f"      medida_columnas = {1 - proporcion_columnas_dup:.6f} ^ {nivel_riesgo}")
        print(f"      medida_columnas = {medida_columnas:.6f}")
        
        promedio_medidas = (medida_filas + medida_columnas) / 2
        print(f"\n      Promedio de medidas = ({medida_filas:.6f} + {medida_columnas:.6f}) / 2")
        print(f"      Promedio de medidas = {promedio_medidas:.6f}")
        
        unicidad = promedio_medidas * 10
        print(f"\n      unicidad (antes de limitar) = {promedio_medidas:.6f} × 10 = {unicidad:.6f}")
        
        unicidad = max(0, min(10, unicidad))
        print(f"      unicidad (después de limitar a [0, 10]) = {unicidad:.6f}")
        
        print(f"\n" + "="*70)
        print(f"🎯 RESULTADO FINAL DE UNICIDAD: {unicidad:.4f}/10")
        print("="*70 + "\n")
        
        return float(unicidad)




    def calculate_portabilidad(self) -> float:
        """
        Calcula el score de portabilidad basado en formatos disponibles en el dataset.
        
        Portabilidad mide si el recurso se puede descargar y usar sin depender de 
        software propietario, sin macros, contraseñas ni bloqueos.
        
        Returns:
            float: Score entre 0 y 10
        """
        print("\n" + "="*70)
        print("📦 INICIO DEL CÁLCULO DE PORTABILIDAD")
        print("="*70)
        
        # Validar datos cargados
        if self.df is None or len(self.df) == 0:
            print("❌ No hay datos cargados. Retornando 0.0")
            return 0.0
        
        total_recursos = len(self.df)
        print(f"📊 Analizando {total_recursos} recursos para portabilidad...")
        
        # Clasificación de formatos basada en la columna 'd_formato'
        # Considerando la falta de datos completos, asignamos puntajes conservadores
        
        formatos_muy_portables = {
            'Excel', 'Hoja de calculo', 'Hoja de calculo / Web'
            # Asumimos que son XLSX sin macros por defecto (optimista pero realista)
        }
        
        formatos_medianamente_portables = {
            'Web', 'Web/Pdf', 'Pdf/Web'
            # Web puede contener datos estructurados, pero requiere verificación
        }
        
        formatos_no_portables = {
            'Pdf'  # Formato cerrado, difícil reutilización
        }
        
        # Contadores
        count_muy_portables = 0
        count_medianos = 0
        count_no_portables = 0
        count_desconocidos = 0
        
        print(f"\n🔍 CLASIFICANDO FORMATOS:")
        
        # Analizar cada recurso según su formato
        for idx, row in self.df.iterrows():
            formato = str(row.get('d_formato', '')).strip()
            medio = str(row.get('c_medio_de_conservaci_n_y', '')).strip()
            
            # Clasificación
            if formato in formatos_muy_portables:
                count_muy_portables += 1
                print(f"   ✅ MUY PORTABLE: '{formato}' (medio: {medio})")
            elif formato in formatos_medianamente_portables:
                count_medianos += 1
                print(f"   ⚠️  MEDIANAMENTE: '{formato}' (medio: {medio})")
            elif formato in formatos_no_portables:
                count_no_portables += 1
                print(f"   ❌ NO PORTABLE: '{formato}' (medio: {medio})")
            else:
                count_desconocidos += 1
                print(f"   ❓ DESCONOCIDO: '{formato}' (medio: {medio})")
        
        # Ajuste por falta de datos completos - asumimos conservadoramente
        # que los formatos desconocidos son medianamente portables
        count_medianos += count_desconocidos
        
        print(f"\n📊 RESULTADOS DE CLASIFICACIÓN:")
        print(f"   • Muy portables: {count_muy_portables}/{total_recursos}")
        print(f"   • Medianamente portables: {count_medianos}/{total_recursos}")
        print(f"   • No portables: {count_no_portables}/{total_recursos}")
        if count_desconocidos > 0:
            print(f"   • Desconocidos (asumidos como medianos): {count_desconocidos}")
        
        # Cálculo del score con pesos
        peso_muy_portable = 1.0      # Excel/CSV/JSON - formatos ideales
        peso_medio = 0.5             # Web/formatos mixtos - requieren procesamiento
        peso_no_portable = 0.0       # PDF - no reutilizable directamente
        
        # Puntuación cruda lineal
        puntuacion_cruda = (
            (count_muy_portables * peso_muy_portable) + 
            (count_medianos * peso_medio) + 
            (count_no_portables * peso_no_portable)
        ) / total_recursos
        
        # Aplicar penalización cuadrática (similar a otros criterios)
        # Esto penaliza más los datasets con alta proporción de formatos no portables
        portabilidad = 10 * (1 - (1 - puntuacion_cruda) ** 1.2)
        
        # Ajuste adicional por falta de metadatos completos
        # Reducimos ligeramente el score porque no tenemos información sobre:
        # - Extensiones específicas de archivo
        # - Presencia de macros o contraseñas
        # - Tipos MIME exactos
        factor_ajuste_metadatos = 0.9  # Penalización del 10% por falta de datos completos
        
        portabilidad_ajustada = portabilidad * factor_ajuste_metadatos
        portabilidad_final = max(0, min(10, portabilidad_ajustada))
        
        print(f"\n📐 CÁLCULO DEL SCORE:")
        print(f"   Puntuación cruda: {puntuacion_cruda:.4f}")
        print(f"   Portabilidad (sin ajuste): {portabilidad:.4f}")
        print(f"   Ajuste por metadatos incompletos: ×{factor_ajuste_metadatos}")
        print(f"   Portabilidad final: {portabilidad_final:.4f}")
        
        # Evaluación cualitativa
        proporcion_muy_portables = (count_muy_portables / total_recursos) * 100
        proporcion_portables_total = ((count_muy_portables + count_medianos) / total_recursos) * 100
        
        print(f"\n📋 EVALUACIÓN CUALITATIVA:")
        print(f"   • Formatos muy portables: {proporcion_muy_portables:.1f}%")
        print(f"   • Formatos portables total: {proporcion_portables_total:.1f}%")
        
        if proporcion_muy_portables >= 70:
            print(f"   ✅ EXCELENTE: Alta proporción de formatos muy portables")
        elif proporcion_portables_total >= 60:
            print(f"   ⚠️  ACEPTABLE: Mayoría de formatos son portables")
        elif proporcion_portables_total >= 30:
            print(f"   🔶 REGULAR: Menos de la mitad en formatos portables")
        else:
            print(f"   ❌ DEFICIENTE: Muy pocos formatos portables")
        
        # Información sobre limitaciones
        print(f"\n💡 LIMITACIONES:")
        print(f"   • No hay información sobre extensiones específicas (.csv, .xlsx, etc.)")
        print(f"   • No hay datos sobre presencia de macros o contraseñas")
        print(f"   • No se conocen tipos MIME exactos")
        print(f"   • Score ajustado a la baja por falta de metadatos completos")
        
        print(f"\n" + "="*70)
        print(f"🎯 PORTABILIDAD FINAL: {portabilidad_final:.4f}/10")
        print("="*70)
        
        # Cachear el resultado
        self.cached_scores['portabilidad'] = portabilidad_final
        
        return float(portabilidad_final)





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
        """
        Calcula la métrica de Disponibilidad del dataset.
        
        Disponibilidad mide la capacidad del dataset de estar **siempre listo y accesible**
        para su uso. Se calcula como el promedio simple de Accesibilidad y Actualidad.
        
        La guía define disponibilidad como:
        
        disponibilidad = (accesibilidad + actualidad) / 2
        
        Interpretación:
        - Ambos son 10: disponibilidad = 10 (máximo, datos siempre listos)
        - Uno es 10 y otro 0: disponibilidad = 5 (parcial)
        - Ambos son 0: disponibilidad = 0 (no usable)
        
        Componentes:
        1. **Accesibilidad**: ¿Qué tan fácil es acceder al dataset?
           - Basada en tags y links en metadatos
        
        2. **Actualidad**: ¿Qué tan reciente es la información?
           - Basada en fecha de última actualización
        
        Returns:
            float: Score entre 0 y 10, donde 10 = dataset siempre disponible
        """
        print("\n" + "="*70)
        print("📡 INICIO DEL CÁLCULO DE DISPONIBILIDAD")
        print("="*70)
        
        # Validar metadata
        if self.metadata is None:
            print("⚠️  No hay metadatos disponibles. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        # ===== COMPONENTE 1: ACCESIBILIDAD =====
        print(f"\n🔗 COMPONENTE 1: ACCESIBILIDAD")
        print(f"   Evaluando tags y links en metadatos...")
        try:
            accesibilidad = self.calculate_accesibilidad_from_metadata(self.metadata, verbose=False)
            print(f"   ✓ Accesibilidad calculada: {accesibilidad:.4f}/10")
        except Exception as e:
            print(f"   ⚠️  Error calculando accesibilidad: {e}")
            accesibilidad = 5.0
            print(f"   → Usando valor neutral: {accesibilidad:.4f}/10")
        
        # ===== COMPONENTE 2: ACTUALIDAD =====
        print(f"\n📅 COMPONENTE 2: ACTUALIDAD")
        print(f"   Evaluando fecha de última actualización...")
        try:
            actualidad = self.calculate_actualidad(self.metadata, verbose=False)
            print(f"   ✓ Actualidad calculada: {actualidad:.4f}/10")
        except Exception as e:
            print(f"   ⚠️  Error calculando actualidad: {e}")
            actualidad = 5.0
            print(f"   → Usando valor neutral: {actualidad:.4f}/10")
        
        # ===== CÁLCULO DE DISPONIBILIDAD =====
        print(f"\n📐 PASO 3: CÁLCULO DEL SCORE DE DISPONIBILIDAD")
        print(f"   Fórmula:")
        print(f"      disponibilidad = (accesibilidad + actualidad) / 2")
        
        print(f"\n   Sustituyendo valores:")
        print(f"      disponibilidad = ({accesibilidad:.4f} + {actualidad:.4f}) / 2")
        
        disponibilidad = (accesibilidad + actualidad) / 2
        print(f"      disponibilidad = {disponibilidad:.4f}")
        
        # Limitar al rango [0, 10]
        disponibilidad = max(0, min(10, disponibilidad))
        
        # ===== INTERPRETACIÓN =====
        print(f"\n📊 INTERPRETACIÓN DEL RESULTADO:")
        if disponibilidad >= 9.0:
            print(f"   ✅ EXCELENTE ({disponibilidad:.2f}/10): Dataset siempre listo y accesible")
        elif disponibilidad >= 7.0:
            print(f"   ✔️  BUENO ({disponibilidad:.2f}/10): Dataset generalmente disponible")
        elif disponibilidad >= 5.0:
            print(f"   ⚠️  ACEPTABLE ({disponibilidad:.2f}/10): Disponibilidad parcial")
        elif disponibilidad >= 3.0:
            print(f"   ❌ DEFICIENTE ({disponibilidad:.2f}/10): Disponibilidad limitada")
        else:
            print(f"   ❌ CRÍTICO ({disponibilidad:.2f}/10): Dataset prácticamente no disponible")
        
        print(f"\n" + "="*70)
        print(f"🎯 RESULTADO FINAL DE DISPONIBILIDAD: {disponibilidad:.4f}/10")
        print("="*70 + "\n")
        
        return float(disponibilidad)

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
