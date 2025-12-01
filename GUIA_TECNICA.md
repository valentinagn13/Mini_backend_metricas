# Guía Técnica - Data Quality Assessment Backend

## 📐 Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Cliente (Frontend/CLI)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Server                           │
│  - main.py (17 endpoints)                                    │
│  - CORS Middleware                                           │
│  - Request Validation (Pydantic)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌─────────┐     ┌──────────────┐  ┌──────────────┐
   │ Metadata│     │ Data Loading │  │ Calculation  │
   │ Cache   │     │ (Sodapy)     │  │ Engine       │
   └─────────┘     └──────────────┘  └──────────────┘
        │                ▼                ▼
        │          ┌────────────────────────────┐
        └─────────►│  DataQualityCalculator     │
                   │  (data_quality_calculator) │
                   │  - 17 métricas             │
                   │  - Validadores            │
                   │  - Parsers                │
                   └────────────┬───────────────┘
                                │
                    ┌───────────┼────────────┐
                    ▼           ▼            ▼
              ┌──────────┐  ┌────────┐  ┌────────┐
              │ Socrata  │  │Spacy   │  │Sklearn │
              │API       │  │(NLP)   │  │(ML)    │
              └──────────┘  └────────┘  └────────┘
                    │
                    ▼
         ┌─────────────────────────┐
         │  datos.gov.co (Socrata) │
         │  - Metadata API         │
         │  - Resource API (datos) │
         └─────────────────────────┘
```

## 🔄 Flujos Principales

### Flujo 1: Inicialización de Dataset

```python
POST /initialize
├─ dataset_id: str (ej: "ijus-ubej")
└─ load_full: bool (default: False)
    │
    ├─ obtener_metadatos_socrata(dataset_id)
    │  └─ GET {SOCRATA_BASE_URL}/api/views/{dataset_id}
    │     └─ Retorna: nombre, descripción, tags, columnas, etc.
    │
    ├─ DataQualityCalculator.__init__(dataset_id, metadata)
    │  └─ Inicializa: dataset_id, metadata, df=None
    │     └─ Carga listas estáticas: departamentos, municipios (en memoria)
    │
    └─ Retorna: DatasetInfoResponse
       ├─ dataset_name
       ├─ rows (0 si no load_full)
       ├─ columns
       ├─ data_url
       ├─ metadata_obtained: bool
       └─ total_records_available
```

### Flujo 2: Carga de Datos (Opcional)

```python
POST /load_data
│
├─ calculator.load_data(limit=50000)
│  ├─ Sodapy client (autenticado)
│  │  └─ client.get(dataset_id, limit=50000)
│  │
│  ├─ Paginación automática (Sodapy maneja internamente)
│  │  └─ Ej: 50000 registros = ~500 requests de 100 cada uno
│  │
│  ├─ df = pd.DataFrame.from_records(results)
│  │
│  └─ _optimize_dtypes()
│     ├─ int64 → int8/int16/int32 (si es posible)
│     ├─ float64 → float32
│     └─ object → category (si hay <10% únicos)
│
└─ Retorna: DataFrame optimizado en memoria
   └─ self.df (ahora disponible para cálculos)
```

### Flujo 3: Cálculo de Métrica (Ejemplo: Actualidad)

```python
GET /actualidad?dataset_id="ijus-ubej"
│
├─ Validación
│  └─ if calculator.dataset_id != dataset_id → Error 400
│
├─ calculator.calculate_actualidad(metadata)
│  │
│  ├─ Obtener "fecha_actualizacion" del metadata
│  │  └─ Parsear a datetime
│  │
│  ├─ Calcular días desde actualización
│  │  └─ (now - fecha_actualizacion).days
│  │
│  ├─ Obtener "frecuencia_actualizacion_dias" (si existe)
│  │  └─ Si no existe: inferir de campo "periodicidad" (ej: "Mensual" → 30 días)
│  │
│  ├─ Aplicar fórmula:
│  │  └─ Si días_desde_actualización ≤ frecuencia_esperada:
│  │     ├─ score = 10
│  │     └─ Else:
│  │        ├─ penalización = 0.5 * (días_exceso / frecuencia_esperada)
│  │        └─ score = max(0, 10 - penalización)
│  │
│  └─ Retornar detalles: {"days_since_update": N, "frequency_days": M, ...}
│
└─ Retorna: ScoreResponse
   ├─ score: 8.5 (0-10)
   └─ details: {...}
```

### Flujo 4: Validación de Conformidad (Caso Complejo)

```python
GET /conformidad?dataset_id="ijus-ubej"
│
├─ Si NO hay datos cargados:
│  ├─ Intentar cargar muestra (5000 registros)
│  └─ Si falla: score = 10.0 (sin columnas para validar)
│
├─ _detect_relevant_columns(metadata)
│  ├─ Buscar en columnas por patrones:
│  │  ├─ "depart*" → departamentos
│  │  ├─ "munic*" → municipios
│  │  ├─ "año|year|fecha" → años
│  │  ├─ "lat*|latitud" → latitudes
│  │  ├─ "lon*|longitud" → longitudes
│  │  └─ "correo|email" → emails
│  │
│  └─ Retorna: {"departamentos": [...], "municipios": [...], ...}
│
├─ Si NO hay columnas relevantes:
│  └─ score = 10.0 (nada que validar)
│
├─ Si SÍ hay columnas relevantes:
│  ├─ Para cada fila:
│  │  ├─ Validar departamentos contra lista de 32 oficiales
│  │  ├─ Validar municipios contra lista de 1,122 oficiales
│  │  ├─ Validar años: 1900 ≤ año ≤ 2100
│  │  ├─ Validar coordenadas: -90 ≤ lat ≤ 90, -180 ≤ lon ≤ 180
│  │  └─ Validar emails: regex RFC 5322
│  │
│  ├─ Contar valores válidos vs totales
│  │  └─ proporción_valida = válidos / total
│  │
│  ├─ Aplicar fórmula:
│  │  └─ score = proporción_valida * 10
│  │     └─ Rango: 0 (ninguno válido) - 10 (todos válidos)
│  │
│  └─ Retornar detalles: {"valid_count": 450, "total_count": 500, ...}
│
└─ Retorna: ScoreResponse
   ├─ score: 9.0
   └─ details: {...}
```

## 🧮 Fórmulas de Métricas Clave

### Actualidad (Timeliness)
```
días_desde_actualización = hoy - fecha_última_actualización
frecuencia_esperada = metadata.frecuencia_actualizacion_dias

Si días_desde_actualización ≤ frecuencia_esperada:
    score = 10
Else:
    penalización = 0.5 * (días_exceso / frecuencia_esperada)
    score = max(0, 10 - penalización)
```

### Completitud (Completeness)
```
nulos_por_columna = count(NULL) en cada columna
proporción_nulos = nulos_por_columna / total_filas

Para cada columna:
    score_columna = (1 - proporción_nulos) * 10

score_final = promedio(score_columna para todas las columnas)
```

### Disponibilidad (Availability)
```
disponibilidad = (accesibilidad + actualidad) / 2
```

### Recuperabilidad (Recoverability)
```
recuperabilidad = (accesibilidad + metadatos_completos + metadatos_auditados) / 3
```

### Unicidad (Uniqueness)
```
filas_duplicadas = count(filas exactamente iguales)
columnas_duplicadas = count(columnas exactamente iguales)

proporción_duplicadas = (filas_duplicadas + columnas_duplicadas) / total

penalización = nivel_riesgo * proporción_duplicadas
score = max(0, 10 - penalización)
```

### Credibilidad (Credibility)
```
credibilidad = (metadata_completeness * 0.4 +
                exactitud_data * 0.3 +
                consistencia_data * 0.3)
```

## 📊 Validadores Especializados

### 1. Validador de Departamentos Colombianos
```python
DEPARTAMENTOS_VALIDOS = [
    'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 
    'Bolívar', 'Boyacá', 'Caldas', 'Caquetá', 'Casanare', 'Cauca', 
    'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 'Guainía',
    'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 
    'Norte de Santander', 'Putumayo', 'Quindío', 'Risaralda', 
    'San Andrés y Providencia', 'Santander', 'Sucre', 'Tolima', 
    'Valle del Cauca', 'Vaupés', 'Vichada'
]
# Total: 32 departamentos

Validación case-insensitive con normalización de tildes
```

### 2. Validador de Municipios
```python
# 1,122 municipios colombianos
# Estructura: {nombre_municipio: departamento}

Validación case-insensitive con normalización de tildes
```

### 3. Validador de Coordenadas Geográficas
```python
def _is_valid_latitude(value) -> bool:
    try:
        lat = float(value)
        return -90 <= lat <= 90
    except:
        return False

def _is_valid_longitude(value) -> bool:
    try:
        lon = float(value)
        return -180 <= lon <= 180
    except:
        return False
```

### 4. Validador de Emails
```python
# Regex RFC 5322 simplificado:
# ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

Validación con manejo de excepciones
```

## 🔐 Manejo de Errores

### Error 400: Bad Request
```json
{
  "detail": "Dataset not initialized. Call /initialize first."
}
```
**Causas**: 
- Llamar métrica sin inicializar
- Dataset_id no coincide

### Error 400: Dataset Mismatch
```json
{
  "detail": "Dataset mismatch. Initialized: ijus-ubej, Requested: xyz-abc"
}
```
**Solución**: Reinicializar con nuevo dataset_id

### Error 500: Data Loading Failed
```json
{
  "detail": "Error loading data: [details de la excepción]"
}
```
**Causas**:
- Timeout en Socrata
- Credenciales inválidas
- Falta de conectividad

## 🚀 Optimizaciones Implementadas

### 1. Lazy Loading de Datos
- **Problema**: Datasets de 100K registros saturaban memoria
- **Solución**: No cargar datos por defecto; solo al llamar `/load_data`
- **Beneficio**: Endpoints de metadata son <100ms

### 2. Caché de Metadatos
- **Implementación**: `calculator.cached_scores = {}`
- **Uso**: Evitar recalcular mismos scores
- **Limitación**: Se limpia al reinicializar

### 3. Optimización de Tipos de Datos
```python
# Antes: int64 usa 8 bytes por valor
# Después: int8 usa 1 byte (si valores 0-127)
# Ahorro: 8x para datos pequeños, ~50% promedio

Automatización en _optimize_dtypes():
- int64 → int8/int16/int32
- float64 → float32
- object → category
```

### 4. Paginación Automática (Sodapy)
- **Internamente**: Sodapy pagina automáticamente (100 rec/req)
- **Transparencia**: Usuario ve un único DataFrame
- **Control**: Configurable via `DEFAULT_RECORDS_LIMIT`

## 🔌 Integración de Dependencias Externas

### Socrata (Sodapy)
```python
from sodapy import Socrata

client = Socrata(
    domain="www.datos.gov.co",
    app_token="API_KEY",
    username="user",
    password="pass"
)

# Obtener metadatos
metadata = requests.get(f"https://www.datos.gov.co/api/views/{dataset_id}").json()

# Obtener datos
data = client.get(dataset_id, limit=50000)
```

### Pandas
```python
# Conversión de registros a DataFrame
df = pd.DataFrame.from_records(data)

# Optimización automática
df = df.astype({'column': 'category'})
```

### Scikit-learn (TfidfVectorizer)
```python
# Para cálculo de similitud de texto en conformidad
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform([text1, text2])
similarity = cosine_similarity(tfidf_matrix)[0][1]
```

### Spacy
```python
# Para NLP avanzado (opcional)
import spacy
nlp = spacy.load("es_core_news_sm")
doc = nlp("Texto a procesar")
```

## 📈 Monitoreo y Debugging

### Logs Automáticos
```
🚀 Inicializando dataset con ID: ijus-ubej
🔍 Obteniendo metadatos desde: https://www.datos.gov.co/api/views/ijus-ubej
✅ Metadatos obtenidos exitosamente
🔗 Obteniendo datos (sodapy) para dataset: ijus-ubej
🎯 Registros obtenidos (sodapy): 5000
📊 DataFrame creado: 5000 filas, 15 columnas
```

### Indicadores de Estado
- `metadata_obtained: bool` - Metadatos disponibles
- `limit_reached: bool` - Datos truncados (50K máximo)
- `records_count: int` - Registros cargados
- `total_records_available: int` - Disponibles en Socrata

---

**Versión**: 1.0  
**Última actualización**: 30 de noviembre de 2025
