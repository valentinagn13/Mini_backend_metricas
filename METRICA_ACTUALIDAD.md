# Métrica de Actualidad del Dataset

## Descripción General

La métrica de **Actualidad** evalúa qué tan reciente es la última actualización de un dataset en relación con su frecuencia de actualización esperada. Esta métrica es crítica para determinar si el dataset sigue siendo relevante y confiable para análisis y toma de decisiones.

## Objetivo

Medir si los datos se mantienen actualizados según la cadencia de publicación comprometida por el publicador del dataset.

---

## Fórmula de Cálculo

$$\text{Actualidad} = \begin{cases}
10.0 & \text{si } \Delta_{días} \leq F_{actualización} \\
0.0 & \text{si } \Delta_{días} > F_{actualización} \\
5.0 & \text{si hay datos incompletos}
\end{cases}$$

Donde:
- $\Delta_{días}$ = Número de días desde la última actualización hasta la fecha actual
- $F_{actualización}$ = Frecuencia esperada de actualización en días

---

## Campos de Metadata Requeridos

### 1. **Fecha de Actualización** (Requerido)

Puede provenir de diferentes fuentes según el origen de los datos:

| Campo | Tipo | Formato | Descripción |
|-------|------|---------|-------------|
| `fecha_actualizacion` | `string` | ISO 8601 | Fecha de última actualización del dataset (ej: `2025-11-01T10:30:00Z`) |
| `rowsUpdatedAt` | `integer` | Unix Timestamp (segundos o ms) | Timestamp de última actualización (común en Socrata) |

**Ejemplos válidos:**
```json
{
  "fecha_actualizacion": "2025-11-26T14:30:00Z"
}
```

```json
{
  "rowsUpdatedAt": 1733389800
}
```

### 2. **Frecuencia de Actualización** (Requerido)

| Campo | Tipo | Valores Aceptados | Ejemplo |
|-------|------|-------------------|---------|
| `frecuencia_actualizacion_dias` | `integer` | Número de días | `30` |
| `updateFrequency` | `string` | Ver tabla abajo | `"Mensual"` |
| `frecuencia_actualizacion` | `string` | Ver tabla abajo | `"30 días"` |

**Formatos de Frecuencia Aceptados:**

| Entrada | Días Resultantes | Notas |
|---------|------------------|-------|
| `1` o `"1"` | 1 | Diario |
| `7` o `"7"` | 7 | Semanal |
| `30` o `"30"` | 30 | Mensual |
| `365` o `"365"` | 365 | Anual |
| `"diario"` / `"daily"` | 1 | Case-insensitive |
| `"semanal"` / `"weekly"` | 7 | Case-insensitive |
| `"mensual"` / `"monthly"` | 30 | Case-insensitive |
| `"anual"` / `"annual"` / `"yearly"` | 365 | Case-insensitive |
| `"30 días"` / `"30 dias"` | 30 | Patrón regex |
| `"P30D"` | 30 | ISO 8601 Duration |
| `"P1M"` | 30 | ISO 8601 Duration |
| `"P1Y"` | 365 | ISO 8601 Duration |

---

## Implementación en Python

### Invocación Básica

```python
from data_quality_calculator import DataQualityCalculator

# Con metadata en la inicialización
metadata = {
    "fecha_actualizacion": "2025-11-20",
    "frecuencia_actualizacion_dias": 7  # Semanal
}

calc = DataQualityCalculator(dataset_url="", metadata=metadata)
score = calc.calculate_actualidad()
print(f"Score de Actualidad: {score}/10")  # Output: 10.0 (si está dentro del período)
```

### Invocación Sin Cargar Dataset

La métrica es **independiente de los datos del dataset**, solo requiere metadata:

```python
from data_quality_calculator import DataQualityCalculator

# Crear instancia sin URL ni datos
calc = DataQualityCalculator(dataset_url="")

# Pasar metadata directamente al cálculo
metadata_remota = {
    "rowsUpdatedAt": 1733389800,  # Timestamp Socrata
    "updateFrequency": "Mensual"
}

score = calc.calculate_actualidad(metadata=metadata_remota)
print(f"Actualidad: {score}")  # Se calcula sin descargar datos
```

### Integración con API REST

```python
from fastapi import FastAPI
from data_quality_calculator import DataQualityCalculator

app = FastAPI()
calculator = None

@app.post("/initialize")
async def initialize_dataset(dataset_id: str, load_full: bool = False):
    """
    Inicializar con metadata (sin cargar datos por defecto).
    La métrica de actualidad se puede calcular inmediatamente.
    """
    global calculator
    
    # Obtener metadatos desde Socrata (u otra fuente)
    metadata = obtener_metadatos(dataset_id)
    
    # Crear calculador con metadata
    calculator = DataQualityCalculator(dataset_id, metadata)
    
    # Calcular actualidad SIN esperar la carga completa de datos
    score = calculator.calculate_actualidad()
    
    return {"actualidad_score": score, "metadata_obtained": True}

@app.get("/actualidad")
async def get_actualidad():
    """Devuelve el score de actualidad sin necesidad de datos cargados."""
    score = calculator.calculate_actualidad()
    return {"score": round(score, 2)}
```

---

## Interpretación de Resultados

| Score | Estado | Significado |
|-------|--------|-------------|
| **10.0** | ✅ Actualizado | El dataset está dentro de su período de actualización esperado |
| **0.0** | ❌ Desactualizado | El dataset ha superado su período de actualización esperado |
| **5.0** | ⚠️ Incompleto | Faltan datos de fecha o frecuencia en los metadatos |

### Ejemplos de Interpretación

**Caso 1: Dataset Actualizado**
```
Fecha de actualización: 2025-11-20
Fecha actual: 2025-11-26
Diferencia: 6 días
Frecuencia esperada: 30 días

Resultado: 10.0 (Dentro del período)
```

**Caso 2: Dataset Desactualizado**
```
Fecha de actualización: 2025-10-01
Fecha actual: 2025-11-26
Diferencia: 56 días
Frecuencia esperada: 30 días

Resultado: 0.0 (Fuera del período)
```

---

## Ventajas de la Implementación Desacoplada

✅ **No requiere descargar datos completos** para calcular la métrica  
✅ **Respuesta inmediata** sin latencias de I/O  
✅ **Bajo costo de computo** (solo comparación de fechas)  
✅ **Útil para auditorías rápidas** de múltiples datasets  
✅ **Compatible con metadatos de diferentes fuentes** (Socrata, CKAN, OpenData, etc.)

---

## Manejo de Errores y Casos Edge

### Fecha Inválida
Si la fecha no puede parsearse, la métrica retorna **5.0** (incompleto).

```python
metadata = {
    "fecha_actualizacion": "fecha-invalida",
    "frecuencia_actualizacion_dias": 30
}
score = calc.calculate_actualidad(metadata)
# Output: 5.0
```

### Metadata Vacía
Si no hay fecha ni frecuencia, retorna **5.0**.

```python
score = calc.calculate_actualidad({})
# Output: 5.0
```

### Frecuencia No Reconocida
Si la frecuencia no se identifica, se asume **365 días** (anual).

```python
metadata = {
    "fecha_actualizacion": "2025-11-01",
    "updateFrequency": "frecuencia_desconocida"
}
score = calc.calculate_actualidad(metadata)
# Usa 365 días como fallback
```

---

## Integración con Otras Métricas

La actualidad contribuye a otras métricas:

- **Disponibilidad** = (Accesibilidad + Actualidad) / 2
- **Recuperabilidad** = (Accesibilidad + Metadatos + Actualidad) / 3

Cambios en la métrica de Actualidad afectan directamente a estas métricas agregadas.

---

## Referencias y Estándares

- **ISO 8601**: Formato internacional para fechas y duraciones
- **Unix Timestamp**: Estándar de Socrata y plataformas CKAN
- **OE1 3.4**: Especificación de Calidad de Datos (origen de esta métrica)

---

## Notas para Desarrolladores

1. **Timezone Awareness**: La comparación se realiza con `datetime.now()` (UTC nativo en Python)
2. **Precisión**: Solo se consideran días completos (no horas)
3. **Caching**: Los scores pueden cachearse si la metadata no cambia
4. **Performance**: O(1) - Complejidad constante, ideal para grandes volúmenes
