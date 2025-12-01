# 📊 DOCUMENTACIÓN TÉCNICA - METRICAS DE CALIDAD DE DATOS

## Tabla de Contenidos
1. [Resumen General](#resumen-general)
2. [Metricas Implementadas](#metricas-implementadas)
3. [Flujo de Operación](#flujo-de-operación)
4. [Detalles Técnicos por Metrica](#detalles-técnicos-por-métrica)

---

## 🎯 Resumen General

Este proyecto es un **API de Evaluación de Calidad de Datos** que calcula **14 métricas de calidad** para datasets publicados en la plataforma **datos.gov.co**. Cada métrica evalúa un aspecto diferente de la calidad de datos siguiendo las directrices de la **Guía MinTIC 2025**.

### Características Principales:
- ✅ **Cálculos basados en metadata**: La mayoría de métricas no requieren cargar datos completos
- ✅ **Opción de carga completa**: Algunos endpoints requieren `/load_data` para análisis profundos
- ✅ **Evaluación 0-10**: Todas las métricas devuelven scores normalizados
- ✅ **API REST**: Endpoints simples y RESTful
- ✅ **Paginación optimizada**: Manejo eficiente de grandes datasets

---

## 📋 Metricas Implementadas

| # | Métrica | Escala | Requiere Datos | Descripción |
|---|---------|--------|-----------------|-------------|
| 1 | **Actualidad** | 0-10 | No | ¿Qué tan reciente es la información? |
| 2 | **Accesibilidad** | 0-10 | No | ¿Qué tan fácil es acceder al dataset? |
| 3 | **Confidencialidad** | 0-10 | No | ¿Están protegidos los datos sensibles? |
| 4 | **Completitud** | 0-10 | Sí* | ¿Cuántos valores están presente? |
| 5 | **Conformidad** | 0-1 | Sí* | ¿Cumple estándares y convenciones? |
| 6 | **Trazabilidad** | 0-10 | No | ¿Se puede auditar la información? |
| 7 | **Disponibilidad** | 0-10 | No | ¿Está siempre listo y accesible? |
| 8 | **Portabilidad** | 0-10 | Sí* | ¿Se puede mover entre sistemas? |
| 9 | **Credibilidad** | 0-10 | Sí* | ¿Es confiable la fuente? |
| 10 | **Recuperabilidad** | 0-10 | Sí* | ¿Se puede recuperar fácilmente? |
| 11 | **Unicidad** | 0-10 | Sí* | ¿Hay duplicados o datos repetidos? |
| 12 | **Relevancia** | 0-10 | No | ¿Proporciona valor decisional? |
| 13 | **Precisión** | 0-10 | Sí* | ¿Nivel apropiado de desagregación? |
| 14 | **Consistencia** | 0-10 | Sí* | ¿Hay coherencia en los datos? |

*Nota: "Sí*" significa que opcionalmente requiere datos si está disponible, pero intenta funcionar con solo metadata

---

## 🔄 Flujo de Operación

### Paso 1: Inicialización
```
POST /initialize
{
  "dataset_id": "ijus-ubej",
  "load_full": false  // Por defecto no carga datos completos
}
```

**Qué sucede:**
- Obtiene metadatos desde Socrata API
- Crea instancia de `DataQualityCalculator`
- Guarda el `dataset_id` para validaciones posteriores
- Opcionalmente carga datos si `load_full=true`

---

### Paso 2: Cálculos de Métricas (Solo Metadata)
```
GET /actualidad?dataset_id=ijus-ubej
GET /accesibilidad?dataset_id=ijus-ubej
GET /confidencialidad?dataset_id=ijus-ubej
GET /trazabilidad?dataset_id=ijus-ubej
GET /disponibilidad?dataset_id=ijus-ubej
```

**Características:**
- ✅ No requieren carga previa de datos
- ✅ Respuesta instantánea
- ✅ Válidan que el `dataset_id` coincida con inicialización

---

### Paso 3: Carga de Datos (Para Análisis Profundo)
```
POST /load_data
```

**Qué sucede:**
- Descarga hasta 50,000 registros del dataset
- Optimiza tipos de datos
- Prepara DataFrame para análisis
- Permite cálculos que requieren datos reales

---

### Paso 4: Cálculos Avanzados (Con Datos)
```
GET /completitud?dataset_id=ijus-ubej
GET /unicidad?dataset_id=ijus-ubej&nivel_riesgo=1.5
GET /conformidad?dataset_id=ijus-ubej
GET /credibilidad?dataset_id=ijus-ubej
```

**Características:**
- ⚠️ Requieren `/load_data` previo
- ⚠️ Devuelven error 400 si datos no están cargados
- ✅ Análisis profundo con información real

---

## 📐 Detalles Técnicos por Métrica

### 1. 🕐 ACTUALIDAD

**Definición:** Mide qué tan reciente es la información del dataset respecto a su frecuencia de actualización.

**Escala:** 0-10
- `10.0` = Datos dentro de su frecuencia de actualización
- `0.0` = Datos desactualizados (fuera de frecuencia)
- `5.0` = Información indeterminada

**Fórmula:**
```
Si frecuencia = "No aplica":
  actualidad = 5.0

Si frecuencia = "Nunca":
  actualidad = 0.0

Si frecuencia = "Más de tres años":
  actualidad = 10.0

Si frecuencia = "Solo una vez" Y hace <= 5 años:
  actualidad = 10.0

Si (fecha_actual - fecha_actualizacion) <= frecuencia_dias:
  actualidad = 10.0

Si (fecha_actual - fecha_actualizacion) > frecuencia_dias:
  actualidad = 0.0
```

**Fuentes de Datos:**
- Metadata: `fecha_actualizacion`, `frecuencia_actualizacion`
- Fallback: Socrata `rowsUpdatedAt`, `frequency`

**Ejemplo:**
```
Dataset actualizado: 2025-11-15
Frecuencia: 30 días
Fecha actual: 2025-11-28 (13 días después)
Resultado: 10.0 ✅ (dentro de frecuencia)

Dataset actualizado: 2025-10-01
Frecuencia: 30 días
Fecha actual: 2025-11-28 (58 días después)
Resultado: 0.0 ❌ (fuera de frecuencia)
```

**Endpoint:** `GET /actualidad`

---

### 2. 📍 ACCESIBILIDAD

**Definición:** Evalúa qué tan fácil es acceder y descubrir el dataset mediante metadatos y documentación.

**Escala:** 0-10
- `10.0` = Excelente accesibilidad (tags + documentación)
- `5.0` = Accesibilidad parcial (solo una fuente)
- `0.0` = Baja accesibilidad (sin metadata)

**Fórmula:**
```
puntaje_tags = 5.0 si len(tags) > 0 else 0.0
puntaje_links = 5.0 si existen links (documentación/normativa) else 0.0

accesibilidad = puntaje_tags + puntaje_links
accesibilidad = min(max(0, accesibilidad), 10)
```

**Links Evaluados:**
- `attributionLink` (enlace de atribución)
- `metadata.custom_fields['Información de Datos']['URL Documentación']`
- `metadata.custom_fields['Información de Datos']['URL Normativa']`

**Ejemplo:**
```
Tags: ["salud", "covid-19", "estadísticas"]  → puntaje_tags = 5.0
Links encontrados:
  - https://ejemplo.com/docs  → puntaje_links = 5.0

accesibilidad = 5.0 + 5.0 = 10.0 ✅
```

**Endpoint:** `GET /accesibilidad`

---

### 3. 🔐 CONFIDENCIALIDAD

**Definición:** Mide el riesgo de exposición de datos sensibles o personales.

**Escala:** 0-10
- `10.0` = Sin datos sensibles (máxima confidencialidad)
- `5.0` = Datos sensibles moderados
- `0.0` = Muchos datos críticos expuestos

**Fórmula:**
```
Detectar columnas sensibles por palabras clave:

ALTO riesgo (peso=3):
  - documento, cédula, pasaporte, contraseña, tarjeta, cuenta bancaria
  - historial médico, diagnóstico, password, DNI

MEDIO riesgo (peso=2):
  - dirección, teléfono, celular, email, correo

BAJO riesgo (peso=1):
  - nombre, apellido, edad, sexo, fecha nacimiento

propConf = N_columnas_sensibles / N_columnas_totales
riesgo_total = suma(pesos de columnas sensibles)

confidencialidad = max(0, 10 - (propConf × riesgo_total))
```

**Ejemplo:**
```
Total columnas: 20
Columnas sensibles detectadas:
  - cedula: peso=3
  - email: peso=2
  - edad: peso=1

N_conf = 3
propConf = 3/20 = 0.15
riesgo_total = 3 + 2 + 1 = 6

confidencialidad = 10 - (0.15 × 6) = 10 - 0.9 = 9.1 ✅
```

**Endpoint:** `GET /confidencialidad`

---

### 4. ✅ COMPLETITUD

**Definición:** Evalúa qué porcentaje de celdas del dataset tienen valores (no nulos).

**Escala:** 0-10
- `10.0` = Dataset completamente lleno
- `5.0` = 50% de valores completos
- `0.0` = Muchos valores faltantes

**Fórmula:**
```
total_filas = len(df)
total_columnas = len(df.columns)
total_celdas = total_filas × total_columnas
total_nulos = df.isna().sum().sum()

proporcion_nulos = total_nulos / total_celdas
proporcion_completo = 1 - proporcion_nulos

completitud = proporcion_completo × 10

Penalización por columnas muy incompletas (>50% nulos):
  - Cada columna con >50% nulos: -0.5 puntos
```

**Ejemplo:**
```
Dataset: 1000 filas, 10 columnas
Total celdas: 10,000
Valores nulos: 500 (5%)

proporcion_completo = 1 - 0.05 = 0.95
completitud = 0.95 × 10 = 9.5 ✅

Si 3 columnas tienen >50% nulos:
  completitud = 9.5 - (3 × 0.5) = 8.0
```

**Requiere:** `POST /load_data` previo

**Endpoint:** `GET /completitud`

---

### 5. 📋 CONFORMIDAD

**Definición:** Evalúa si el dataset cumple con estándares de formato, estructura y convenciones.

**Escala:** 0-1 (o 0-10 en escala normalizada)

**Análisis Realizado:**
```
1. Validación de Formatos Geográficos
   - Departamentos de Colombia (validados contra API)
   - Municipios de Colombia
   - Códigos DANE

2. Validación de Formatos de Fechas
   - Detecta formatos ISO 8601
   - Formatos YYYY-MM-DD
   - Análisis de consistencia

3. Validación de Tipos de Datos
   - Numéricos vs strings
   - Booleanos
   - Fechas

4. Validación de Patrones
   - Emails: regex de validación
   - URLs: formato válido
   - Números de teléfono
```

**Fórmula General:**
```
conformidad = (columnas_validas / columnas_relevantes) × 1.0

Si no hay columnas relevantes:
  conformidad = 0.0
```

**Ejemplo:**
```
Dataset con columnas:
  - departamento: "Antioquia" ✅ (válido)
  - municipio: "Bogotá" ⚠️ (inconsistente con departamento)
  - fecha: "2025-11-30" ✅ (ISO 8601)
  - email: "usuario@example.com" ✅ (válido)

Validaciones pasadas: 3/4
conformidad = 0.75 (en escala 0-1)
```

**Requiere:** Opcionalmente datos (carga automática si es necesario)

**Endpoint:** `GET /conformidad`

---

### 6. 📍 TRAZABILIDAD

**Definición:** Mide la capacidad de auditar y rastrear la procedencia y cambios en los datos.

**Escala:** 0-10

**Fórmula:**
```
trazabilidad = (medida_metadatos_diligenciados × 0.75) +
               (medida_acceso_auditado × 0.20) +
               (medida_titulo_sin_fecha × 0.05)

Donde:

medida_metadatos_diligenciados:
  - Campos esperados: id, name, description, owner, tags, etc. (20 campos)
  - Proporción completada: campos_diligenciados / campos_totales
  - Penalización cuadrática: (1 - proporción)²
  - Score: (1 - penalización) × 10

medida_acceso_auditado:
  - Verifica: fecha_actualización, propietario, publicador, contacto
  - Ponderación con pesos (0.4, 0.3, 0.2, 0.1)
  - Score: suma_pesos × 10

medida_titulo_sin_fecha:
  - Si título NO tiene año: 10.0
  - Si título tiene año: 0.0
```

**Ejemplo:**
```
Campos diligenciados: 15/20
Proporción: 0.75
Penalización: (1-0.75)² = 0.0625
medida_metadatos = (1-0.0625) × 10 = 9.375

Campos críticos: 3/5 presentes = 0.6 × 10 = 6.0
Título sin fecha: "COVID-19 Colombia" ✅ = 10.0

trazabilidad = (9.375 × 0.75) + (6.0 × 0.20) + (10.0 × 0.05)
             = 7.03 + 1.2 + 0.5 = 8.73 ✅
```

**Endpoint:** `GET /trazabilidad`

---

### 7. 🌐 DISPONIBILIDAD

**Definición:** Evalúa la capacidad del dataset de estar siempre listo y accesible para su uso.

**Escala:** 0-10

**Fórmula:**
```
disponibilidad = (accesibilidad + actualidad) / 2

Escala de interpretación:
  - 10: Datos siempre listos y accesibles (máximo)
  - 7-9: Dataset generalmente disponible (bueno)
  - 5-6: Disponibilidad parcial (aceptable)
  - 3-4: Disponibilidad limitada (deficiente)
  - 0-2: Datos prácticamente no disponibles (crítico)
```

**Ejemplo:**
```
Accesibilidad: 8.0 (buena documentación)
Actualidad: 10.0 (reciente)

disponibilidad = (8.0 + 10.0) / 2 = 9.0 ✅ (excelente)
```

**Endpoint:** `GET /disponibilidad`

---

### 8. 📦 PORTABILIDAD

**Definición:** Mide si el dataset se puede descargar y usar sin depender de software propietario.

**Escala:** 0-10

**Análisis Realizado:**
```
1. Clasificación de Formatos
   MUY PORTABLE (peso=10):
     - JSON, CSV, XML, JSONL, GeoJSON
   
   MEDIANAMENTE PORTABLE (peso=6):
     - Excel (XLSX), ODS
   
   NO PORTABLE (peso=2):
     - PDF, DOC, imágenes
     - Formatos propietarios

2. Criterios de No Portabilidad
   ❌ Contiene macros
   ❌ Requiere contraseña
   ❌ Tiene bloqueos de edición
   ❌ Comprimido en ZIP (sin open source)

3. Cálculo de Score
   portabilidad = (suma_pesos_formatos / (N_formatos × 10)) × 10
   
   Si tiene restricciones: portabilidad × 0.5
```

**Ejemplo:**
```
Formatos disponibles:
  - CSV: peso=10 ✅
  - JSON: peso=10 ✅
  - Excel: peso=6 ⚠️

suma_pesos = 10 + 10 + 6 = 26
portabilidad = (26 / (3 × 10)) × 10 = 8.67 ✅
```

**Requiere:** `POST /load_data` previo

**Endpoint:** `GET /portabilidad`

---

### 9. 🔗 CREDIBILIDAD

**Definición:** Evalúa la confiabilidad del dataset basada en la calidad de metadatos y procedencia.

**Escala:** 0-10

**Componentes:**
```
1. Validez de Metadatos (40%)
   - Campos completos y actualizados
   - Consistencia entre campos
   - Ausencia de valores por defecto genéricos

2. Procedencia (30%)
   - Organización conocida/verificada
   - Fuente documentada
   - Historial de publicación

3. Validaciones de Datos (20%)
   - Correlación entre campos
   - Outliers razonables
   - Consistencia temporal

4. Información de Contacto (10%)
   - Email de contacto presente
   - Teléfono disponible
   - Responsable identificado
```

**Fórmula:**
```
credibilidad = (validez_metadatos × 0.40) +
               (validez_procedencia × 0.30) +
               (validaciones_datos × 0.20) +
               (info_contacto × 0.10)

credibilidad = credibilidad × 10  (escala 0-10)
```

**Requiere:** Opcionalmente datos

**Endpoint:** `GET /credibilidad`

---

### 10. 🔄 RECUPERABILIDAD

**Definición:** Mide qué tan fácil es recuperar y reconstruir el dataset y su contexto.

**Escala:** 0-10

**Fórmula:**
```
recuperabilidad = (accesibilidad + 
                   metadatos_completos + 
                   metadatos_auditados) / 3

Donde:

metadatos_completos (0-1):
  - Verifica: título, descripción, etiquetas, schema, contexto
  - Score: campos_presentes / 5

metadatos_auditados (0-1):
  - Verifica: versionado, procedencia, técnicos, contacto, licencia
  - Score: campos_presentes / 5

Normalización final:
  recuperabilidad = recuperabilidad × 10
```

**Ejemplo:**
```
Accesibilidad: 8.0
Metadatos completos: 0.8 (4/5 campos)
Metadatos auditados: 0.6 (3/5 campos)

recuperabilidad = (8.0 + (0.8×10) + (0.6×10)) / 3 = 8.0 ✅
```

**Requiere:** `POST /load_data` previo

**Endpoint:** `GET /recuperabilidad`

---

### 11. 🔑 UNICIDAD

**Definición:** Detecta y cuantifica filas y columnas duplicadas en el dataset.

**Escala:** 0-10
- `10.0` = Sin duplicados (máxima unicidad)
- `5.0` = Duplicados moderados
- `0.0` = Muchos duplicados

**Tipos de Duplicados Detectados:**
```
1. FILAS DUPLICADAS EXACTAS
   - Filas con idénticos valores en TODAS las columnas
   - Penalización: (N_duplicados / N_total_filas) × 10

2. COLUMNAS DUPLICADAS EXACTAS
   - Columnas con idénticos valores en TODAS las filas
   - Penalización: (N_columnas_dup / N_total_columnas) × 5

3. QUASI-DUPLICADOS (por parámetro nivel_riesgo)
   - Filas que coinciden en columnas clave
   - Penalización escalada por nivel_riesgo
```

**Fórmula:**
```
penalizacion_filas = (num_dup_filas / num_total_filas) × 10 × nivel_riesgo
penalizacion_columnas = (num_dup_columnas / num_total_columnas) × 5

unicidad = max(0, 10 - penalizacion_filas - penalizacion_columnas)
```

**Parámetros:**
```
nivel_riesgo:
  - 1.0: Penalización suave (datos explorativos)
  - 1.5: Penalización media (RECOMENDADO)
  - 2.0: Penalización estricta (datos críticos)
```

**Ejemplo:**
```
Dataset: 1000 filas, 15 columnas
Filas duplicadas exactas: 50
Columnas duplicadas: 2

penalizacion_filas = (50 / 1000) × 10 × 1.5 = 0.75
penalizacion_columnas = (2 / 15) × 5 = 0.67

unicidad = 10 - 0.75 - 0.67 = 8.58 ✅
```

**Requiere:** `POST /load_data` previo

**Endpoint:** `GET /unicidad?nivel_riesgo=1.5`

---

### 12. ⭐ RELEVANCIA

**Definición:** Evalúa si el dataset proporciona valor para la toma de decisiones.

**Escala:** 0-10

**Criterios:**
```
1. Categorización (70%)
   - Dataset está bien categorizado
   - Etiquetas son descriptivas
   - Clasificación clara

2. Volumen de Datos (30%)
   - Mínimo 50 filas para relevancia básica
   - Más filas = mayor relevancia
   - Fórmula: relevancia_volumen = (filas / 50) × 10
```

**Fórmula:**
```
medida_categoria = 7.0  (si categorizado)
medida_filas = min(10.0, (num_filas / 50) × 10)

relevancia = (medida_categoria + medida_filas) / 2
relevancia = min(10.0, relevancia)
```

**Ejemplo:**
```
Dataset: bien categorizado, 500 filas
medida_categoria = 7.0
medida_filas = (500 / 50) × 10 = 100.0 → min(10.0) = 10.0

relevancia = (7.0 + 10.0) / 2 = 8.5 ✅
```

**Endpoint:** `GET /relevancia` (no implementado en endpoints actuales)

---

### 13. ⚙️ PRECISIÓN

**Definición:** Evalúa el nivel apropiado de desagregación y detalle en los datos.

**Escala:** 0-10

**Análisis:**
```
1. Análisis de Cardinalidad
   - Columnas categóricas: verificar valores únicos
   - Si muchos valores únicos: mayor precisión
   - Si pocos valores únicos: menor precisión

2. Granularidad Temporal
   - Datos diarios: máxima precisión
   - Datos mensuales: media precisión
   - Datos anuales: baja precisión

3. Información Geográfica
   - Nivel de detalle: país, región, municipio, vereda
   - Mayor detalle = mayor precisión
```

**Fórmula (General):**
```
precision = (cardinalidad_promedio / cardinalidad_maxima) × 10

Donde cardinalidad_maxima se ajusta según tipo de dato
```

**Endpoint:** `GET /precision` (no implementado en endpoints actuales)

---

### 14. 🔗 CONSISTENCIA

**Definición:** Mide la coherencia y falta de contradicciones en los datos.

**Escala:** 0-10

**Validaciones:**
```
1. Coherencia Referencial
   - Claves foráneas válidas
   - Referencias cruzadas consistentes

2. Rango de Valores
   - Valores numéricos dentro de rangos esperados
   - Fechas lógicamente ordenadas

3. Correlación entre Campos
   - Si departamento=X, municipio debe ser de X
   - Relacionales coherentes

4. Tipo de Dato Consistente
   - Columna numérica no tiene strings
   - Fechas en formato consistente
```

**Fórmula:**
```
N_validaciones_pasadas = cantidad de validaciones sin conflicto
N_validaciones_totales = cantidad total de validaciones

consistencia = (N_pasadas / N_totales) × 10
```

**Ejemplo:**
```
Dataset: 1000 filas
Validaciones:
  - Rangos numéricos: 1000/1000 pasadas ✅
  - Fechas ordenadas: 995/1000 pasadas ⚠️ (5 inconsistencias)
  - Referencias: 1000/1000 pasadas ✅

consistencia = (2995 / 3000) × 10 = 9.98 ✅
```

**Requiere:** `POST /load_data` previo

**Endpoint:** `GET /consistencia` (no implementado en endpoints actuales)

---

## 🔧 Arquitectura Técnica

### Estructura de Clases

```python
class DataQualityCalculator:
    # Inicialización
    __init__(dataset_id, metadata)
    
    # Carga de datos
    async load_data(limit=50000)
    _optimize_dtypes()
    
    # Métricas (solo metadata)
    calculate_actualidad()
    calculate_accesibilidad_from_metadata()
    calculate_confidencialidad_from_metadata()
    calculate_trazabilidad()
    calculate_disponibilidad()
    
    # Métricas (con datos opcionales)
    calculate_conformidad_from_metadata_and_data()
    calculate_credibilidad()
    calculate_recuperabilidad()
    
    # Métricas (requieren datos)
    calculate_completitud()
    calculate_unicidad()
    calculate_portabilidad()
    calculate_consistencia()
    calculate_precision()
```

### Endpoints REST

```
POST   /initialize              → Inicializa dataset y obtiene metadata
POST   /load_data               → Carga datos completos (hasta 50K registros)

GET    /actualidad              → Score actualidad (0-10)
GET    /accesibilidad           → Score accesibilidad (0-10)
GET    /confidencialidad        → Score confidencialidad (0-10) + detalles
GET    /completitud             → Score completitud (0-10)
GET    /conformidad             → Score conformidad (0-1) + detalles
GET    /trazabilidad            → Score trazabilidad (0-10)
GET    /disponibilidad          → Score disponibilidad (0-10)
GET    /portabilidad            → Score portabilidad (0-10)
GET    /credibilidad            → Score credibilidad (0-10)
GET    /recuperabilidad         → Score recuperabilidad (0-10)
GET    /unicidad                → Score unicidad (0-10)
```

---

## 📊 Ejemplo de Flujo Completo

```bash
# 1. Inicializar
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "ijus-ubej",
    "load_full": false
  }'

Respuesta:
{
  "message": "Dataset initialized successfully",
  "dataset_id": "ijus-ubej",
  "dataset_name": "Procesos Judiciales",
  "rows": 0,
  "columns": 0,
  "metadata_obtained": true
}

# 2. Calcular métricas (solo metadata)
curl http://localhost:8001/actualidad?dataset_id=ijus-ubej
→ {"score": 10.0}

curl http://localhost:8001/accesibilidad?dataset_id=ijus-ubej
→ {"score": 8.5, "details": {...}}

# 3. Cargar datos (para análisis profundos)
curl -X POST http://localhost:8001/load_data
Respuesta:
{
  "message": "Full data loaded successfully",
  "rows": 50000,
  "columns": 45
}

# 4. Calcular métricas avanzadas
curl http://localhost:8001/unicidad?dataset_id=ijus-ubej&nivel_riesgo=1.5
→ {"score": 9.2}

curl http://localhost:8001/completitud?dataset_id=ijus-ubej
→ {"score": 8.8}
```

---

## 🔍 Optimizaciones Implementadas

1. **Paginación Inteligente**: 
   - Descarga máximo 50K registros
   - Detecta última página automáticamente
   - Evita timeout en datasets grandes

2. **Caché de Conversiones**:
   - Frecuencias convertidas a días (cálculos posteriores rápidos)
   - Departamentos de Colombia (API local)

3. **Optimización de Tipos**:
   - Convierte strings largos a categorías
   - Reduce memoria consumida

4. **Validación de Consistencia**:
   - Cada endpoint valida `dataset_id`
   - Previene mezcla de datasets
   - Errores claros si hay mismatch

---

## 📈 Matriz de Requisitos

| Métrica | Metadata | Datos | Async | Cache |
|---------|----------|-------|-------|-------|
| Actualidad | ✅ | ❌ | ❌ | ✅ |
| Accesibilidad | ✅ | ❌ | ❌ | ❌ |
| Confidencialidad | ✅ | ❌ | ❌ | ❌ |
| Completitud | ✅ | ✅* | ❌ | ❌ |
| Conformidad | ✅ | ✅* | ❌ | ✅ |
| Trazabilidad | ✅ | ❌ | ❌ | ✅ |
| Disponibilidad | ✅ | ❌ | ❌ | ❌ |
| Portabilidad | ✅ | ✅ | ❌ | ❌ |
| Credibilidad | ✅ | ✅* | ❌ | ❌ |
| Recuperabilidad | ✅ | ✅ | ❌ | ❌ |
| Unicidad | ✅ | ✅ | ❌ | ❌ |

*Nota: ✅* significa que es opcional pero mejorado si está disponible

---

## 🚀 Uso Recomendado

### Para Evaluación Rápida:
```
1. POST /initialize (load_full=false)
2. GET /actualidad
3. GET /accesibilidad
4. GET /confidencialidad
5. GET /trazabilidad
6. GET /disponibilidad
```
**Tiempo:** < 2 segundos

### Para Evaluación Completa:
```
1. POST /initialize (load_full=false)
2. POST /load_data
3. GET todas las métricas
```
**Tiempo:** 5-15 segundos (según tamaño dataset)

---

## 📝 Validaciones de Entrada

Todos los endpoints requieren:
```
dataset_id (string):
  - No nulo
  - Coincide con dataset inicializado
  - Formato válido (alphanuméricas + guiones)
```

---
