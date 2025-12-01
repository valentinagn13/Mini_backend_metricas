# Ejemplos de Uso - Data Quality Assessment Backend

## 🎯 Caso de Uso 1: Evaluación Rápida de Dataset

**Objetivo**: Obtener un score rápido de un dataset sin cargar datos completos

### Paso 1: Inicializar dataset
```bash
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "ijus-ubej",
    "load_full": false
  }'
```

**Respuesta**:
```json
{
  "message": "Dataset initialized successfully",
  "dataset_id": "ijus-ubej",
  "dataset_name": "Casos ingresados de Justicia Especializada en Infancia",
  "rows": 0,
  "columns": 15,
  "data_url": "https://www.datos.gov.co/resource/ijus-ubej.json",
  "metadata_obtained": true,
  "records_count": 0,
  "total_records_available": 45230,
  "limit_reached": false
}
```

### Paso 2: Obtener métricas basadas en metadata (sin datos)
```bash
# Actualidad - qué tan reciente
curl -X GET "http://localhost:8001/actualidad?dataset_id=ijus-ubej"

# Respuesta esperada
{
  "score": 8.5,
  "details": {
    "days_since_update": 12,
    "update_frequency_days": 30,
    "compliance_percentage": 85.0
  }
}
```

```bash
# Accesibilidad - facilidad de acceso
curl -X GET "http://localhost:8001/accesibilidad?dataset_id=ijus-ubej"

# Respuesta esperada
{
  "score": 9.0,
  "details": {
    "has_tags": true,
    "has_attribution_links": true,
    "tags_count": 5,
    "links_count": 2
  }
}
```

```bash
# Trazabilidad - completitud de metadata
curl -X GET "http://localhost:8001/trazabilidad?dataset_id=ijus-ubej"

# Respuesta esperada
{
  "score": 7.5,
  "details": {
    "metadata_fields_complete": 6,
    "total_fields_expected": 8,
    "completeness_percentage": 75.0
  }
}
```

### Paso 3: Disponibilidad (combinación de actualidad + accesibilidad)
```bash
curl -X GET "http://localhost:8001/disponibilidad?dataset_id=ijus-ubej"

# Respuesta esperada
{
  "score": 8.75,
  "details": {
    "accesibilidad_score": 9.0,
    "actualidad_score": 8.5
  }
}
```

**⏱️ Tiempo total**: ~500ms (solo peticiones HTTP)  
**💾 Memoria usada**: <10 MB (solo metadata en memoria)

---

## 🎯 Caso de Uso 2: Análisis Completo con Validación de Datos

**Objetivo**: Análisis profundo cargando datos reales

### Paso 1: Inicializar dataset
```bash
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej", "load_full": false}'
```

### Paso 2: Cargar datos completos
```bash
curl -X POST http://localhost:8001/load_data

# Respuesta
{
  "message": "Full data loaded successfully",
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

**⏱️ Tiempo**: ~2-5 segundos (depende del dataset)

### Paso 3: Calcular métricas que requieren datos

#### 3a. Completitud
```bash
curl -X GET "http://localhost:8001/completitud?dataset_id=ijus-ubej"

# Respuesta detallada
{
  "score": 8.2,
  "details": {
    "filas": 5000,
    "columnas": 15,
    "columnas_con_nulos": 3,
    "promedio_nulos_por_columna": "8.5%",
    "columnas_completas": 12,
    "score_por_columna": {
      "id": 10.0,
      "fecha": 9.8,
      "departamento": 7.5,
      "municipio": 8.0,
      "descripcion": 6.2
    }
  }
}
```

#### 3b. Unicidad (detección de duplicados)
```bash
curl -X GET "http://localhost:8001/unicidad?dataset_id=ijus-ubej&nivel_riesgo=1.5"

# Respuesta
{
  "score": 9.1,
  "details": {
    "filas_totales": 5000,
    "filas_duplicadas": 15,
    "filas_unicas": 4985,
    "columnas_duplicadas": 0,
    "proporcion_duplicadas": "0.3%",
    "duplicados_detectados": [
      {"indice": 123, "motivo": "Fila completa duplicada"},
      {"indice": 456, "motivo": "Fila completa duplicada"}
    ]
  }
}
```

#### 3c. Credibilidad
```bash
curl -X GET "http://localhost:8001/credibilidad?dataset_id=ijus-ubej"

# Respuesta
{
  "score": 8.7,
  "details": {
    "metadata_completeness": 8.5,
    "data_consistency": 9.0,
    "data_accuracy": 8.5,
    "trust_indicators": {
      "tiene_publicador": true,
      "tiene_licencia": true,
      "tiene_fuente": true,
      "es_actualizado": true
    }
  }
}
```

#### 3d. Conformidad (validación con estándares)
```bash
curl -X GET "http://localhost:8001/conformidad?dataset_id=ijus-ubej"

# Respuesta completa
{
  "score": 8.9,
  "details": {
    "relevantes_columnas": ["departamento", "municipio", "año", "correo"],
    "validaciones": {
      "departamentos": {
        "validos": 4950,
        "invalidos": 50,
        "porcentaje_valido": "99.0%"
      },
      "municipios": {
        "validos": 4900,
        "invalidos": 100,
        "porcentaje_valido": "98.0%"
      },
      "años": {
        "validos": 5000,
        "invalidos": 0,
        "porcentaje_valido": "100.0%"
      },
      "emails": {
        "validos": 4980,
        "invalidos": 20,
        "porcentaje_valido": "99.6%"
      }
    },
    "score_promedio": 8.9
  }
}
```

#### 3e. Portabilidad
```bash
curl -X GET "http://localhost:8001/portabilidad?dataset_id=ijus-ubej"

# Respuesta
{
  "score": 9.2,
  "details": {
    "formatos_disponibles": ["JSON", "CSV", "XML"],
    "formatos_portables": {
      "muy_portable": ["JSON", "CSV"],
      "mediano": ["XML"],
      "no_portable": []
    },
    "peso_portabilidad": 9.2,
    "es_descargable": true,
    "tiene_dependencias_propietarias": false
  }
}
```

### Paso 4: Recuperabilidad (combina múltiples métricas)
```bash
curl -X GET "http://localhost:8001/recuperabilidad?dataset_id=ijus-ubej"

# Respuesta
{
  "score": 8.8,
  "details": {
    "accesibilidad_score": 9.0,
    "metadatos_completos_score": 8.5,
    "metadatos_auditados_score": 8.9,
    "formula": "(9.0 + 8.5 + 8.9) / 3"
  }
}
```

**⏱️ Tiempo total**: ~5-10 segundos  
**💾 Memoria usada**: ~100-200 MB (depende del tamaño del dataset)

---

## 🎯 Caso de Uso 3: Diagnóstico Automatizado

**Objetivo**: Generar reporte completo de conformidad para debugging

### Usar herramienta de diagnóstico
```bash
python diagnostico_conformidad.py ijus-ubej

# Salida esperada
================================================================================
DIAGNÓSTICO DE CONFORMIDAD - Dataset: ijus-ubej
================================================================================

📊 INFORMACIÓN DEL DATASET
├─ Nombre: Casos ingresados de Justicia Especializada en Infancia
├─ Filas: 5000
├─ Columnas: 15
└─ URL: https://www.datos.gov.co/resource/ijus-ubej.json

🔍 COLUMNAS RELEVANTES DETECTADAS
├─ Departamentos: ['departamento']
├─ Municipios: ['municipio']
├─ Años: ['año']
├─ Coordenadas: ['latitud', 'longitud']
└─ Emails: ['correo_contacto']

✅ VALIDACIÓN DE CONFORMIDAD
├─ Score Final: 8.9/10
├─ Departamentos válidos: 4950/5000 (99.0%)
├─ Municipios válidos: 4900/5000 (98.0%)
├─ Años válidos: 5000/5000 (100.0%)
├─ Coordenadas válidas: 4995/5000 (99.9%)
└─ Emails válidos: 4980/5000 (99.6%)

🚨 PROBLEMAS IDENTIFICADOS
├─ Fila 123: Departamento inválido "Cundinamarca Oeste"
├─ Fila 456: Municipio no encontrado "San José del Guaviare"
├─ Fila 789: Email mal formado "contacto@.com"
├─ Fila 1001: Latitud fuera de rango "-95.5"
└─ ...
```

---

## 🎯 Caso de Uso 4: Integración con Python/Script

### Script para obtener todos los scores
```python
import requests
import json

BASE_URL = "http://localhost:8001"
DATASET_ID = "ijus-ubej"

# 1. Inicializar
print("🚀 Inicializando dataset...")
response = requests.post(
    f"{BASE_URL}/initialize",
    json={"dataset_id": DATASET_ID, "load_full": False}
)
print(json.dumps(response.json(), indent=2))

# 2. Cargar datos
print("\n📥 Cargando datos...")
response = requests.post(f"{BASE_URL}/load_data")
print(json.dumps(response.json(), indent=2))

# 3. Obtener todas las métricas
metricas = [
    "actualidad",
    "conformidad",
    "completitud",
    "credibilidad",
    "portabilidad",
    "disponibilidad",
    "trazabilidad",
    "recuperabilidad",
    "accesibilidad",
    "confidencialidad",
    "unicidad"
]

scores = {}
print("\n📊 Calculando métricas...")
for metrica in metricas:
    response = requests.get(
        f"{BASE_URL}/{metrica}",
        params={"dataset_id": DATASET_ID}
    )
    data = response.json()
    scores[metrica] = data["score"]
    print(f"  {metrica}: {data['score']}/10")

# 4. Guardar resultados
with open("quality_report.json", "w") as f:
    json.dump(scores, f, indent=2)

print("\n✅ Reporte guardado en quality_report.json")
print(f"📈 Score promedio: {sum(scores.values()) / len(scores):.2f}/10")
```

**Salida esperada**:
```
actualidad: 8.5/10
conformidad: 8.9/10
completitud: 8.2/10
credibilidad: 8.7/10
portabilidad: 9.2/10
disponibilidad: 8.75/10
trazabilidad: 7.5/10
recuperabilidad: 8.8/10
accesibilidad: 9.0/10
confidencialidad: 8.0/10
unicidad: 9.1/10

📈 Score promedio: 8.62/10
```

---

## 🎯 Caso de Uso 5: Comparativa de Datasets

**Objetivo**: Comparar calidad entre varios datasets

```bash
#!/bin/bash

DATASETS=("ijus-ubej" "abc-1234" "xyz-5678")

for dataset in "${DATASETS[@]}"; do
    echo "Evaluando: $dataset"
    
    # Inicializar
    curl -s -X POST http://localhost:8001/initialize \
      -H "Content-Type: application/json" \
      -d "{\"dataset_id\": \"$dataset\"}" > /dev/null
    
    # Obtener score
    SCORE=$(curl -s -X GET "http://localhost:8001/actualidad?dataset_id=$dataset" | \
            grep -o '"score":[0-9.]*' | cut -d: -f2)
    
    echo "  Score Actualidad: $SCORE"
done

# Salida esperada:
# Evaluando: ijus-ubej
#   Score Actualidad: 8.5
# Evaluando: abc-1234
#   Score Actualidad: 7.2
# Evaluando: xyz-5678
#   Score Actualidad: 9.1
```

---

## 📋 Códigos de Error Comunes

### Error 400: Dataset not initialized
```bash
curl -X GET "http://localhost:8001/actualidad?dataset_id=ijus-ubej"

# ❌ Error (sin inicializar primero)
{
  "detail": "Dataset not initialized. Call /initialize first."
}

# ✅ Solución
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej"}'
```

### Error 400: Dataset mismatch
```bash
# ✅ Inicializar dataset A
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej"}'

# ❌ Intentar calcular para dataset B
curl -X GET "http://localhost:8001/actualidad?dataset_id=abc-1234"

# Error
{
  "detail": "Dataset mismatch. Initialized: ijus-ubej, Requested: abc-1234"
}

# ✅ Solución: Reinicializar o usar mismo dataset_id
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "abc-1234"}'
```

### Error 400: Data not loaded
```bash
# ❌ Calcular métrica que requiere datos sin cargar
curl -X GET "http://localhost:8001/completitud?dataset_id=ijus-ubej"

# Error
{
  "detail": "Data not loaded. Call POST /load_data first."
}

# ✅ Solución
curl -X POST http://localhost:8001/load_data
curl -X GET "http://localhost:8001/completitud?dataset_id=ijus-ubej"
```

### Error 500: Socrata connection failed
```bash
# ❌ Sin variables de entorno configuradas
# Error
{
  "detail": "Error connecting to Socrata: Invalid API key"
}

# ✅ Solución
# Verificar .env con:
# - SOCRATA_API_KEY válido
# - SOCRATA_USERNAME y PASSWORD correctos
# - SOCRATA_DOMAIN accesible

# Luego reiniciar servidor
python main.py
```

---

## 📊 Matriz de Decisión: Qué Métrica Usar

| Pregunta | Métrica Recomendada | Requiere Datos |
|----------|-------------------|---|
| ¿Qué tan reciente es? | `actualidad` | ❌ |
| ¿Es fácil acceder? | `accesibilidad` | ❌ |
| ¿Se puede descargar? | `portabilidad` | ❌ |
| ¿Está documentado? | `trazabilidad` | ❌ |
| ¿Siempre disponible? | `disponibilidad` | ❌ |
| ¿Datos seguros? | `confidencialidad` | ❌ |
| ¿Tiene valores nulos? | `completitud` | ✅ |
| ¿Datos son válidos? | `conformidad` | ⚠️ |
| ¿Hay duplicados? | `unicidad` | ✅ |
| ¿Es confiable? | `credibilidad` | ✅ |
| ¿Se puede recuperar? | `recuperabilidad` | ✅ |

---

**Última actualización**: 30 de noviembre de 2025
