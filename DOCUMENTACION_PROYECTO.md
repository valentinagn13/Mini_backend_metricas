# Data Quality Assessment Backend

## Descripción General

Este backend proporciona una **API en FastAPI** para exponer métricas de calidad de datos basadas en criterios internacionales (ISO 8601, DCAT, esquemas de gobernanza de datos). Está diseñado para evaluar datasets desde **datos.gov.co** usando la API Socrata y calcula hasta **17 dimensiones de calidad** en tiempo real.

**Qué permite**: Inicializa datasets desde Socrata, obtiene metadatos, carga datos bajo demanda (lazy loading), y calcula métricas de calidad como: actualidad, conformidad, completitud, credibilidad, portabilidad, disponibilidad, trazabilidad, recuperabilidad, accesibilidad, confidencialidad, unicidad y más.

**Datos usados**: Se conecta directamente a la API Socrata de **datos.gov.co** usando credenciales de entorno. Los datos se cargan bajo demanda mediante paginación (límite configurable de 50,000 registros por defecto). No almacena datos locales permanentemente; todo es procesado en memoria.

## Flujo de Operación

```
1. POST /initialize (dataset_id)
   ↓
   → Obtiene metadatos desde Socrata
   → Inicializa calculadora de calidad
   → Retorna info del dataset (columnas, filas, URL)
   
2. POST /load_data (opcional)
   ↓
   → Carga dataset completo (paginado)
   → Optimiza tipos de datos
   → Prepara para cálculos que requieren datos reales
   
3. GET /[métrica]?dataset_id=...
   ↓
   → Valida que dataset coincida
   → Calcula score (0-10)
   → Retorna detalles del cálculo
```

## Métricas Implementadas (17 dimensiones)

| Métrica | Endpoint | Requiere Datos | Descripción |
|---------|----------|---|-------------|
| **Actualidad** | `/actualidad` | ❌ Solo metadata | Qué tan reciente es la información (últimas actualizaciones) |
| **Conformidad** | `/conformidad` | ⚠️ Opcional | Adherencia a estándares (códigos geográficos, emails, años válidos) |
| **Completitud** | `/completitud` | ✅ Sí | Proporción de valores no nulos por columna |
| **Credibilidad** | `/credibilidad` | ✅ Sí | Confiabilidad basada en metadata y validación de datos |
| **Portabilidad** | `/portabilidad` | ❌ Solo metadata | Facilidad para descargar/usar datos sin dependencias propietarias |
| **Disponibilidad** | `/disponibilidad` | ❌ Solo metadata | Capacidad de estar siempre accesible (promedio de accesibilidad + actualidad) |
| **Trazabilidad** | `/trazabilidad` | ❌ Solo metadata | Completitud de metadata y auditoría (source, publisher, tags) |
| **Recuperabilidad** | `/recuperabilidad` | ✅ Sí | Promedio de accesibilidad, metadata completa y auditada |
| **Accesibilidad** | `/accesibilidad` | ❌ Solo metadata | Facilidad para acceder al dataset (tags, links, documentación) |
| **Confidencialidad** | `/confidencialidad` | ❌ Solo metadata | Protección de datos sensibles (análisis de columnas) |
| **Unicidad** | `/unicidad` | ✅ Sí | Detecta filas y columnas duplicadas |
| **Exactitud Sintáctica** | Integrado | ✅ Sí | Corrección estructural de datos |
| **Exactitud Semántica** | Integrado | ✅ Sí | Corrección contextual de valores |
| **Consistencia** | Integrado | ✅ Sí | Coherencia sin contradicciones |
| **Precisión** | Integrado | ✅ Sí | Nivel apropiado de desagregación |
| **Comprensibilidad** | Integrado | ✅ Sí | Claridad de documentación y etiquetas |
| **Relevancia** | Integrado | ❌ Solo metadata | Valor para toma de decisiones |

## Herramientas Incluidas

### 1. **main.py** (Servidor API)
- Expone endpoints FastAPI con paginación automática
- Gestiona conexiones a Socrata
- Valida dataset_id en cada request para consistencia
- Soporta lazy loading de datos

### 2. **data_quality_calculator.py** (Motor de cálculos)
- Implementa 17 métricas de calidad
- Valida conformidad con listas de departamentos/municipios colombianos
- Utiliza TfidfVectorizer para análisis de similitud de texto
- Calcula métricas de unicidad, completitud, credibilidad

### 3. **diagnostico_conformidad.py** (Herramienta de diagnóstico)
- Script standalone para diagnosticar un dataset específico
- Ideal para debugging y análisis manual
- Muestra detalles de validación por fila

### 4. **test_*.py** (Suite de pruebas)
- `test_actualidad.py` - Valida cálculo de actualidad
- `test_accesibilidad.py` - Valida cálculo de accesibilidad
- `test_unicidad.py` - Valida detección de duplicados
- `test_backend_consistency.py` - Valida consistencia de dataset_id

## Variables de Entorno

```env
# CONFIGURACIÓN DEL SERVIDOR
HOST=0.0.0.0                                    # Dirección de escucha (0.0.0.0 = todas las interfaces)
PORT=8001                                       # Puerto del servidor
ENV=development                                 # Ambiente (development/production)
DEBUG=False                                     # Modo debug de Uvicorn

# CREDENCIALES SOCRATA / datos.gov.co
SOCRATA_DOMAIN=www.datos.gov.co                 # Dominio base de Socrata
SOCRATA_API_KEY=sAmoC9S1twqLnpX9YUmmSTqgp       # API Key para autenticación Socrata
SOCRATA_USERNAME=valen@yopmail.com              # Usuario Socrata
SOCRATA_PASSWORD=p4wHD7Y.SDGiQmP                # Contraseña Socrata

# URLs BASE
SOCRATA_BASE_URL=https://www.datos.gov.co       # URL base para construir enlaces
SOCRATA_API_ENDPOINT=/api/views                 # Endpoint para metadata
SOCRATA_RESOURCE_ENDPOINT=/resource             # Endpoint para datos

# CONFIGURACIÓN DE DATOS
DEFAULT_RECORDS_LIMIT=50000                     # Máximo de registros a cargar por request
TIMEOUT_REQUEST=30                              # Timeout en segundos para requests HTTP

# CONFIGURACIÓN DE CORS
CORS_ORIGINS=*                                  # Orígenes permitidos (use * para desarrollo)
CORS_CREDENTIALS=true                           # Permitir cookies/auth headers
CORS_METHODS=*                                  # Métodos HTTP permitidos
CORS_HEADERS=*                                  # Headers HTTP permitidos

# CONFIGURACIÓN DE LOGGING
LOG_LEVEL=INFO                                  # Nivel de logs (DEBUG/INFO/WARNING/ERROR)
LOG_FILE=./logs/api.log                         # Ruta del archivo de log
```

**Notas importantes**:
- Las credenciales Socrata se cargan desde `.env` al iniciar (nunca versionar en git)
- `SOCRATA_API_KEY` es crítico: sin él, la API de Socrata rechazará requests
- `DEFAULT_RECORDS_LIMIT=50000` es un balance entre memoria y completitud de análisis
- Para producción cambiar `DEBUG=False` y `CORS_ORIGINS` a dominios específicos

## Cómo Ejecutar

### Instalación de dependencias
```bash
pip install -r requirements.txt
python -m spacy download es_core_news_sm  # (Opcional, para NLP avanzado)
```

### Iniciar servidor
```bash
# Opción 1: Directo
python main.py

# Opción 2: Con uvicorn (más control)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

El servidor estará disponible en `http://localhost:8001`

### Probar un dataset (ejemplo)
```bash
# Terminal 1: Iniciar servidor
python main.py

# Terminal 2: Inicializar dataset
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej"}'

# Cargar datos (opcional pero recomendado para cálculos de completitud/credibilidad)
curl -X POST http://localhost:8001/load_data

# Obtener métrica de actualidad
curl -X GET "http://localhost:8001/actualidad?dataset_id=ijus-ubej"

# Obtener métrica de conformidad
curl -X GET "http://localhost:8001/conformidad?dataset_id=ijus-ubej"
```

### Usar diagnóstico automático
```bash
python diagnostico_conformidad.py ijus-ubej
```

## Stack Tecnológico

| Componente | Versión | Propósito |
|-----------|---------|----------|
| **FastAPI** | 0.104.1 | Framework HTTP/REST |
| **Uvicorn** | 0.24.0 | Servidor ASGI |
| **Pandas** | 2.1.3 | Manipulación de datos y análisis |
| **NumPy** | 1.26.2 | Computación numérica |
| **Sodapy** | Latest | Cliente Socrata para conexión a API |
| **Scikit-learn** | 1.3.2 | TfidfVectorizer para análisis de similitud |
| **Spacy** | 3.7.2 | Procesamiento de lenguaje natural (NLP) |
| **Pydantic** | 2.5.0 | Validación de esquemas (request/response) |
| **Requests** | 2.31.0 | HTTP client para Socrata API |
| **Python-dateutil** | 2.8.2 | Parsing de fechas y duraciones |

## Estructuras de Request/Response

### POST /initialize
**Request**:
```json
{
  "dataset_id": "ijus-ubej",
  "load_full": false
}
```

**Response**:
```json
{
  "message": "Dataset initialized successfully",
  "dataset_id": "ijus-ubej",
  "dataset_name": "Casos ingresados de Justicia Especializada en Infancia",
  "rows": 5000,
  "columns": 15,
  "data_url": "https://www.datos.gov.co/resource/ijus-ubej.json",
  "metadata_obtained": true,
  "records_count": 5000,
  "total_records_available": 45230,
  "limit_reached": false
}
```

### GET /[métrica]?dataset_id=...
**Response**:
```json
{
  "score": 8.5,
  "details": {
    "days_since_update": 15,
    "update_frequency_days": 30,
    "compliance_percentage": 85.0
  }
}
```

## Características Técnicas Clave

### Lazy Loading
- **Problema resuelto**: Datasets muy grandes causaban saturación de memoria
- **Solución**: Por defecto no se cargan datos completos. Solo se cargan al llamar `/load_data`
- **Beneficio**: API rápida para endpoints que solo necesitan metadata

### Validación de Dataset ID
- Cada endpoint valida que el `dataset_id` coincida con el inicializado
- Previene inconsistencias si se cambia de dataset sin reinicializar
- Retorna error 400 con mensaje descriptivo en caso de mismatch

### Paginación Automática
- Sodapy maneja internamente la paginación a Socrata (100 registros/request)
- Límite máximo configurable: `DEFAULT_RECORDS_LIMIT=50000`
- Previene timeouts en datasets muy grandes

### Optimización de Tipos de Datos
- Convierte automáticamente columnas a tipos más eficientes (int8, float32, etc.)
- Reduce consumo de memoria hasta 50% en datasets grandes

### CORS Configurado
- Por defecto permite orígenes cualquiera (`*`) para desarrollo
- Fácil ajuste para producción especificando dominios en `.env`

## Limitaciones y Consideraciones

1. **Limite de registros**: Por defecto 50,000. Datasets más grandes se truncan (use `limit_reached=true` como indicador)
2. **Timeout**: 30 segundos por request HTTP. Para datasets muy grandes, aumentar `TIMEOUT_REQUEST`
3. **Memoria**: Datasets con >100,000 columnas pueden causar issues. Validar en producción
4. **Credenciales**: Requiere acceso a Socrata (API Key válida en `.env`)
5. **Conectividad**: Necesita conexión a internet para acceder a datos.gov.co

## Deployment en Producción

```bash
# Con gunicorn + uvicorn workers
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --access-logfile - \
  --error-logfile -
```

**Recomendaciones**:
- Usar reverse proxy (nginx) frente a Gunicorn
- Habilitar logs a archivo (actualizar `LOG_FILE`)
- Cambiar `DEBUG=False` en `.env`
- Especificar `CORS_ORIGINS` a dominios conocidos
- Usar variables de entorno securizadas (no en git)

## Archivos Documentación Complementaria

- `DOCUMENTOS/DOCUMENTACION_TECNICA_METRICAS.md` - Detalles de fórmulas de cada métrica
- `DOCUMENTOS/API_USAGE_GUIDE.md` - Guía de uso con ejemplos
- `DOCUMENTOS/GUIA_PRUEBAS_CONFORMIDAD.md` - Especificaciones de validación de conformidad
- `DOCUMENTOS/METRICA_ACTUALIDAD.md` - Análisis detallado de métrica de actualidad

---

**Última actualización**: 30 de noviembre de 2025  
**Versión API**: 1.0  
**Licencia**: Según corresponda al proyecto
