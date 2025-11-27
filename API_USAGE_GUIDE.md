# API de Evaluación de Calidad de Datos - Guía de Uso

## Arquitectura

El backend mantiene un estado global (`calculator`) que almacena el dataset inicializado actualmente. Todos los endpoints operan sobre este dataset.

## Flujo Correcto de Uso

### 1. Inicializar Dataset
```
POST /initialize
Content-Type: application/json

{
  "dataset_id": "ijus-ubej",
  "load_full": false
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Dataset initialized successfully",
  "dataset_id": "ijus-ubej",
  "dataset_name": "Evaluación de tierras para el cultivo tecnificado de Zanahoria",
  "rows": 0,
  "columns": 10,
  "data_url": "https://www.datos.gov.co/resource/ijus-ubej.json",
  "metadata_obtained": true,
  "records_count": 0,
  "total_records_available": 0,
  "limit_reached": false
}
```

### 2. Calcular Métrica de Actualidad
```
GET /actualidad?dataset_id=ijus-ubej
```

**Parámetros:**
- `dataset_id` (requerido): Debe coincidir con el dataset inicializado

**Respuesta exitosa (200):**
```json
{
  "score": 10.0,
  "details": null
}
```

**Errores posibles:**
- `400 - Dataset not initialized`: No llamaste a `/initialize` primero
- `400 - Dataset mismatch`: El `dataset_id` no coincide con el inicializado

### 3. Cargar Datos Completos (Opcional)
```
POST /load_data
```

**Cuando usar:**
- Cuando necesites calcular métricas que requieren los datos (completitud, conformidad, etc.)
- Después de `/initialize`

**Respuesta exitosa (200):**
```json
{
  "message": "Full data loaded successfully",
  "dataset_id": "ijus-ubej",
  "dataset_name": "...",
  "rows": 24657,
  "columns": 10,
  ...
}
```

## Ejemplos de Flujo Completo

### Ejemplo 1: Solo Actualidad (Sin Descargar Datos)
```bash
# 1. Inicializar
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej", "load_full": false}'

# 2. Calcular actualidad (muy rápido)
curl -X GET 'http://localhost:8001/actualidad?dataset_id=ijus-ubej'
```

### Ejemplo 2: Análisis Completo (Con Datos)
```bash
# 1. Inicializar
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej", "load_full": true}'

# 2. Calcular actualidad
curl -X GET 'http://localhost:8001/actualidad?dataset_id=ijus-ubej'

# 3. Otras métricas (cuando se implementen)
curl -X GET 'http://localhost:8001/completitud?dataset_id=ijus-ubej'
```

## Cambios Realizados en Esta Versión

### ✅ Validación de Dataset Consistencia
- **Antes**: `/actualidad` no validaba qué dataset se usaba
- **Ahora**: `/actualidad?dataset_id=XYZ` valida que XYZ coincida con el inicializado

### ✅ Parámetro dataset_id en GET
- **Antes**: `GET /actualidad` (sin parámetros)
- **Ahora**: `GET /actualidad?dataset_id=ijus-ubej` (con validación)

### ✅ Mensajes de Error Claros
```
"Dataset mismatch. Initialized: ijus-ubej, Requested: 8dbv-wsjq"
```

## Notas Importantes

1. **Una sola sesión activa**: El backend solo puede trabajar con UN dataset a la vez
2. **Validación obligatoria**: Siempre pasar `dataset_id` en endpoints GET para garantizar consistencia
3. **Sin descargas innecesarias**: Por defecto (`load_full=false`), solo se obtienen metadatos
4. **Rápido para actualidad**: Tarda ~100ms sin descargar 24K+ registros

## Estado del Dataset

Después de `/initialize` sin cargar datos:
```
rows: 0 (no cargados)
columns: 10 (extraídos de metadatos)
metadata_obtained: true
```

Después de `/load_data`:
```
rows: 24657 (datos cargados)
columns: 10
metadata_obtained: true
```

## Troubleshooting

### "Dataset not initialized"
→ Primero llamar a `POST /initialize` con un `dataset_id`

### "Dataset mismatch"
→ Asegurar que el `dataset_id` en el GET coincide con el usado en POST `/initialize`

### "Error obteniendo metadatos: 404"
→ El `dataset_id` no existe en `datos.gov.co`

### La métrica de actualidad siempre devuelve valores inconsistentes
→ Verificar que estés usando el mismo `dataset_id` en `/initialize` y `/actualidad?dataset_id=XYZ`
