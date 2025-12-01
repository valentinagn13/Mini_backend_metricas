# Data Quality Assessment Backend

## 🎯 Descripción Rápida

Backend en **FastAPI** que expone **17 métricas de calidad de datos** para datasets desde **datos.gov.co**. Se conecta directamente a la API Socrata, obtiene metadatos, carga datos bajo demanda y calcula scores de calidad en escala 0-10.

## ✨ Qué Permite

- ✅ Inicializar datasets desde Socrata (obtiene metadatos automáticamente)
- ✅ Cargar datos completos bajo demanda (lazy loading, 50,000 registros máximo)
- ✅ Calcular 17 dimensiones de calidad: actualidad, completitud, conformidad, credibilidad, portabilidad, disponibilidad, trazabilidad, recuperabilidad, accesibilidad, confidencialidad, unicidad y más
- ✅ Validar conformidad con estándares colombianos (departamentos, municipios, formatos)
- ✅ Detectar duplicados (filas y columnas)
- ✅ Retornar scores y detalles técnicos de cada métrica

## 📊 Datos Usados

Se conecta **en tiempo real** a la API Socrata de `datos.gov.co` usando credenciales en variables de entorno. **No almacena copias locales** — todo se procesa en memoria bajo demanda. Soporta paginación automática para datasets grandes.

## 🔧 Variables de Entorno Requeridas

```env
# Credenciales Socrata (obligatorio)
SOCRATA_DOMAIN=www.datos.gov.co
SOCRATA_API_KEY=sAmoC9S1twqLnpX9YUmmSTqgp
SOCRATA_USERNAME=valen@yopmail.com
SOCRATA_PASSWORD=p4wHD7Y.SDGiQmP

# Configuración del servidor
HOST=0.0.0.0
PORT=8001
ENV=development
DEBUG=False

# URLs
SOCRATA_BASE_URL=https://www.datos.gov.co
SOCRATA_API_ENDPOINT=/api/views
SOCRATA_RESOURCE_ENDPOINT=/resource

# Datos
DEFAULT_RECORDS_LIMIT=50000    # Máximo de registros a cargar
TIMEOUT_REQUEST=30              # Timeout en segundos

# CORS
# RECOMENDADO en producción: especificar dominios conocidos en lugar de `*`.
# Por defecto de ejemplo apuntamos a `https://datacensus.site`.
CORS_ORIGINS=https://datacensus.site
CORS_CREDENTIALS=true
CORS_METHODS=*
CORS_HEADERS=*
```

**Nota crítica**: El `SOCRATA_API_KEY` es obligatorio. Sin él, la API rechazará conexiones.

## 🚀 Cómo Ejecutar

### Instalar dependencias
```bash
pip install -r requirements.txt
python -m spacy download es_core_news_sm  # Opcional, para NLP
```

### Iniciar servidor
```bash
# Opción 1: Directo
python main.py

# Opción 2: Con uvicorn (más control)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Servidor disponible en: `http://localhost:8001`

### Probar con un dataset

```bash
# Inicializar dataset
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej", "load_full": false}'

# Cargar datos (opcional pero recomendado)
curl -X POST http://localhost:8001/load_data

# Calcular métrica de actualidad
curl -X GET "http://localhost:8001/actualidad?dataset_id=ijus-ubej"

# Calcular métrica de conformidad
curl -X GET "http://localhost:8001/conformidad?dataset_id=ijus-ubej"

# Calcular métrica de completitud (requiere datos cargados)
curl -X GET "http://localhost:8001/completitud?dataset_id=ijus-ubej"
```

### Usar herramienta de diagnóstico

```bash
python diagnostico_conformidad.py ijus-ubej
```

Genera reporte detallado de validación de conformidad para un dataset específico.

## 🏗️ Herramientas Incluidas

| Archivo | Propósito |
|---------|-----------|
| **main.py** | Servidor FastAPI con 17 endpoints de métricas |
| **data_quality_calculator.py** | Motor de cálculos (implementa todas las métricas) |
| **diagnostico_conformidad.py** | Herramienta standalone para análisis de conformidad |
| **test_*.py** | Suite de pruebas automáticas |
| **requirements.txt** | Dependencias Python |

## 📋 Endpoints Principales

| Endpoint | Método | Requiere Datos | Descripción |
|----------|--------|---|-----------|
| `/initialize` | POST | ❌ | Inicializa dataset y carga metadatos |
| `/load_data` | POST | ❌ | Carga datos completos (50K máx) |
| `/actualidad` | GET | ❌ | Score de actualidad (0-10) |
| `/conformidad` | GET | ⚠️ | Score de conformidad (0-10) |
| `/completitud` | GET | ✅ | Score de completitud (0-10) |
| `/credibilidad` | GET | ✅ | Score de credibilidad (0-10) |
| `/portabilidad` | GET | ❌ | Score de portabilidad (0-10) |
| `/disponibilidad` | GET | ❌ | Score de disponibilidad (0-10) |
| `/trazabilidad` | GET | ❌ | Score de trazabilidad (0-10) |
| `/recuperabilidad` | GET | ✅ | Score de recuperabilidad (0-10) |
| `/accesibilidad` | GET | ❌ | Score de accesibilidad (0-10) |
| `/confidencialidad` | GET | ❌ | Score de confidencialidad (0-10) |
| `/unicidad` | GET | ✅ | Score de unicidad (detecta duplicados) |

*Leyenda: ❌ = solo metadata | ⚠️ = opcional | ✅ = datos requeridos*

## 🔌 Stack Tecnológico

- **FastAPI** 0.104.1 - Framework HTTP
- **Uvicorn** 0.24.0 - Servidor ASGI
- **Pandas** 2.1.3 - Análisis de datos
- **NumPy** 1.26.2 - Computación numérica
- **Sodapy** - Cliente Socrata
- **Scikit-learn** 1.3.2 - Machine learning (similitud de texto)
- **Spacy** 3.7.2 - NLP en español
- **Pydantic** 2.5.0 - Validación de datos

## ⚙️ Características Técnicas

### Lazy Loading
- Por defecto **no carga datos completos** (evita saturación de memoria)
- Endpoint `/load_data` carga bajo demanda
- Endpoints que solo necesitan metadata son instantáneos

### Validación de Dataset ID
- Cada request valida que el `dataset_id` coincida con el inicializado
- Previene inconsistencias al cambiar de dataset
- Retorna error 400 con mensaje descriptivo si hay mismatch

### Paginación Automática
- Sodapy maneja internamente la paginación a Socrata
- Límite máximo configurable: `DEFAULT_RECORDS_LIMIT=50000`
- Indicador `limit_reached=true` si dataset es más grande

### Optimización de Memoria
- Convierte automáticamente tipos de datos (int8, float32, etc.)
- Reduce consumo de memoria hasta 50% en datasets grandes

## 📝 Validación de Conformidad

El endpoint `/conformidad` valida:
- **Departamentos**: Contra lista oficial de 32 departamentos colombianos
- **Municipios**: Contra lista de 1,122 municipios
- **Años**: Solo años válidos (1900-2100)
- **Coordenadas**: Latitud (-90 a 90), Longitud (-180 a 180)
- **Emails**: Formato RFC 5322 válido

**Lógica especial**:
- Score = 10.0 si **no hay columnas relevantes para validar**
- Score se basa en proporción de valores válidos si hay columnas

## 🚨 Limitaciones

| Limitación | Detalle |
|-----------|---------|
| Registros máx | 50,000 (configurable en `DEFAULT_RECORDS_LIMIT`) |
| Timeout | 30 segundos por request (configurable) |
| Conectividad | Requiere acceso a internet (datos.gov.co) |
| Autenticación | API Key Socrata obligatoria (en `.env`) |
| Memoria | Datasets >100K columnas pueden causar issues |

## 🔐 Seguridad & Producción

```bash
# Deployment con Gunicorn
pip install gunicorn
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001
```

**Para producción**:
- ✅ Cambiar `DEBUG=False` en `.env`
- ✅ Especificar `CORS_ORIGINS` a dominios conocidos (no `*`)
- ✅ Usar reverse proxy (nginx) frente a Gunicorn
- ✅ Variables de entorno en secrets manager (no en git)
- ✅ Habilitar logging a archivo
- ✅ Considerar rate limiting

## 📚 Documentación Complementaria

- `DOCUMENTACION_PROYECTO.md` - Documentación técnica completa
- `DOCUMENTOS/DOCUMENTACION_TECNICA_METRICAS.md` - Fórmulas detalladas de cada métrica
- `DOCUMENTOS/API_USAGE_GUIDE.md` - Guía de uso con ejemplos
- `DOCUMENTOS/GUIA_PRUEBAS_CONFORMIDAD.md` - Especificaciones de validación

---

**Versión**: 1.0  
**Última actualización**: 30 de noviembre de 2025
