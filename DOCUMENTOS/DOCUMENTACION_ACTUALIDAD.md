# Métrica de Actualidad del Dataset

## 1. Definición

La **métrica de Actualidad** evalúa qué tan recientes son los datos de un dataset en comparación con su frecuencia de actualización declarada. Esta métrica determina si la información del dataset se mantiene al día según el cronograma esperado de actualizaciones.

## 2. Objetivo

Garantizar que los usuarios tengan acceso a información oportuna y relevante. Un dataset desactualizado reduce su valor y confiabilidad para la toma de decisiones.

## 3. Componentes Principales

### 3.1 Fecha de Actualización
- **Origen**: Campo `rowsUpdatedAt` en los metadatos de Socrata (timestamp UNIX)
- **Significado**: Fecha en la que se actualizaron por última vez los datos del dataset
- **Formato**: Se convierte de timestamp UNIX a formato datetime de Python

### 3.2 Frecuencia de Actualización
- **Origen**: Campo `custom_fields["Frecuencia de Actualización"]` o `updateFrequency` en los metadatos
- **Ejemplo de valores**: 
  - "Anual"
  - "Mensual"
  - "Semanal"
  - "Diario"
  - "Más de tres años"
  - "Cada 30 días"
  - "Por demanda"

## 4. Fórmula de Cálculo

### 4.1 Conversión de Frecuencia a Días

Primero, se convierte la frecuencia de actualización a un número de días:

| Frecuencia (insensible a mayúsculas) | Días |
|--------------------------------------|------|
| "anual" | 365 |
| "semestral" | 180 |
| "cuatrimestral" | 120 |
| "trimestral" | 90 |
| "bimestral" | 60 |
| "mensual" | 30 |
| "semanal" | 7 |
| "diario" | 1 |
| "por demanda" | 365 |
| Valores numéricos (ej: "30 días") | Se extrae el número |

### 4.2 Cálculo Principal

```
Diferencia (días) = Fecha Actual - Fecha de Última Actualización

SI Diferencia ≤ Frecuencia (en días):
    Actualidad = 10.0  (Datos actualizados dentro del período esperado)

SI Diferencia > Frecuencia (en días):
    Actualidad = 0.0   (Datos desactualizados, fuera del período)

CASO ESPECIAL: SI "Más de tres años" (insensible a mayúsculas/caracteres):
    Actualidad = 10.0  (Se considera que esta frecuencia es válida)
```

### 4.2.1 Comportamiento por Caso de Frecuencia (detallado)

A continuación se listan las frecuencias admitidas por el sistema, el número de días equivalente y el comportamiento que la métrica devuelve en cada caso (reglas aplicadas por `calculate_actualidad`):

- **Trienio / Trienal**: 1095 días (3 × 365).
    - Comportamiento: Se compara la diferencia en días; si la última actualización fue hace ≤ 1095 días → **10.0**, si fue > 1095 días → **0.0**.

- **Semestral**: 182 días (aprox. 6 meses).
    - Comportamiento: ≤ 182 días → **10.0**, > 182 días → **0.0**.

- **Trimestral**: 90 días.
    - Comportamiento: ≤ 90 días → **10.0**, > 90 días → **0.0**.

- **Mensual**: 30 días.
    - Comportamiento: ≤ 30 días → **10.0**, > 30 días → **0.0**.

- **Diaria / Diario**: 1 día.
    - Comportamiento: ≤ 1 día → **10.0**, > 1 día → **0.0**.

- **Semanal / Semanales**: 7 días.
    - Comportamiento: ≤ 7 días → **10.0**, > 7 días → **0.0**.

- **Quincenal**: 15 días.
    - Comportamiento: ≤ 15 días → **10.0**, > 15 días → **0.0**.

- **Cuatrimestral**: 120 días.
    - Comportamiento: ≤ 120 días → **10.0**, > 120 días → **0.0**.

- **Anual / Año**: 365 días.
    - Comportamiento: ≤ 365 días → **10.0**, > 365 días → **0.0**.

- **Más de tres años**: tratado como 4 años (1460 días) en la normalización, pero además el código aplica una regla explícita: si la cadena de frecuencia contiene la secuencia equivalente a "más de tres años", se considera aceptable y retorna **10.0** inmediatamente (independientemente de la fecha de actualización).
    - Nota: la conversión mapea "más de tres años" → 1460 días; además la comprobación textual da prioridad y devuelve **10.0**.

- **No aplica**: indeterminado.
    - Comportamiento: la métrica trata esto como falta de aplicabilidad e **interpreta el caso como indeterminado**, devolviendo **5.0** (puntuación neutral).

- **Nunca**: se interpreta como que el dataset nunca se actualiza.
    - Comportamiento: devuelve **0.0** (dataset declarado como no actualizado).

- **Solo una vez**: casos en que se indica que el dataset fue publicado una sola vez.
    - Comportamiento: hay una regla especial en la que si la última actualización fue dentro de los últimos 5 años (≤ 5 × 365 días) se considera aceptable → **10.0**; si fue hace más de 5 años → **0.0**.

Estas reglas están implementadas en `_convertir_frecuencia_a_dias` y en `calculate_actualidad` con los fallbacks descritos en esta documentación.

### 4.3 Casos de Fallo

Si no se encuentra información de frecuencia o fecha de actualización:
```
Actualidad = 5.0  (Puntuación por defecto/neutral)
```

## 5. Escala de Puntuación

| Puntuación | Interpretación |
|-----------|----------------|
| 10.0 | ✅ Datos completamente actualizados dentro del período esperado |
| 5.0 | ⚠️ Información incompleta o no disponible |
| 0.0 | ❌ Datos completamente desactualizados, fuera del período esperado |

## 6. Ejemplo Práctico

**Escenario 1: Dataset actualizado recientemente**
- Fecha de última actualización: 2025-11-20
- Fecha actual: 2025-11-26
- Frecuencia: "Mensual" (30 días)
- Diferencia: 6 días
- **Resultado**: 6 días ≤ 30 días → **Actualidad = 10.0** ✅

**Escenario 2: Dataset desactualizado**
- Fecha de última actualización: 2024-06-01
- Fecha actual: 2025-11-26
- Frecuencia: "Semanal" (7 días)
- Diferencia: ~543 días
- **Resultado**: 543 días > 7 días → **Actualidad = 0.0** ❌

**Escenario 3: Frecuencia "Más de tres años"**
- Frecuencia: "MÁS DE TRES AÑOS" (cualquier variación de caso)
- **Resultado**: Coincidencia especial → **Actualidad = 10.0** ✅

## 7. Importancia en la Calidad de Datos

La métrica de **Actualidad** es crucial porque:

1. **Relevancia**: Los datos anticuados pueden llevar a decisiones incorrectas
2. **Confiabilidad**: Un dataset con datos actualizados regularmente genera confianza
3. **Cumplimiento**: Asegura que los datos cumplan con los compromisos de actualización del publicador
4. **Trazabilidad**: Permite auditar si se mantiene el cronograma de actualizaciones

## 8. Implementación Técnica

### 8.1 Método Principal

```python
def calculate_actualidad(self, metadata: Optional[Dict] = None) -> float:
    """
    Calcula la métrica de actualidad usando metadatos.
    
    Args:
        metadata: Diccionario con metadatos (opcional). 
                 Si no se provee, usa self.metadata
    
    Returns:
        float: Puntuación entre 0 y 10
    """
```

### 8.2 Independencia del Dataset

**Característica importante**: Esta métrica **NO requiere descargar ni procesar los datos**. Solo necesita acceso a los metadatos, lo que la hace:
- ⚡ **Rápida**: Ejecución en milisegundos
- 💾 **Eficiente**: No consume memoria del dataset
- 🔄 **Escalable**: Puede calcularse para miles de datasets sin sobrecarga

### 8.3 Endpoints de la API

```
POST /initialize
Parámetros: `{ "dataset_id": "8dbv-wsjq", "load_full": false }`
- `dataset_id` (string): Identificador del dataset en Socrata
- `load_full` (boolean, opcional, default `false`): si es `true` se descargan y procesan todas las filas
Resultado: Obtiene metadatos y crea el contexto del calculador. Por defecto NO descarga todos los datos (modo metadata-only).

POST /load_data
Parámetros: ninguno (usa el dataset ya inicializado)
Resultado: Carga todas las filas del dataset en memoria para métricas que requieren datos completos y devuelve información (filas, columnas, limit_reached).

GET /actualidad
Parámetros de query: `dataset_id` (recomendado)
- Si se provee `dataset_id`: se valida que coincida con el `dataset_id` inicializado; si no coincide, devuelve `400 Dataset mismatch`.
- Si NO se provee `dataset_id`: por compatibilidad hacia atrás el endpoint usa el `dataset_id` ya inicializado y funciona (evita 422). Sin embargo, **recomendamos pasar siempre `dataset_id` explícitamente**.
Resultado: Devuelve `{ "score": 10.0 }` con la puntuación de actualidad calculada solo a partir de metadatos.
```

**Ejemplos de uso (recomendado)**

PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8001/initialize -ContentType "application/json" -Body '{"dataset_id":"ijus-ubej","load_full":false}'

Invoke-RestMethod -Method Get -Uri "http://localhost:8001/actualidad?dataset_id=ijus-ubej"
```

cURL:
```bash
curl -X POST http://localhost:8001/initialize -H "Content-Type: application/json" -d '{"dataset_id":"ijus-ubej","load_full":false}'
curl "http://localhost:8001/actualidad?dataset_id=ijus-ubej"
```

## 9. Integración con Otras Métricas

La Actualidad se utiliza en:

- **Disponibilidad**: (Accesibilidad + Actualidad) / 2
- **Recuperabilidad**: (Accesibilidad + Metadatos Completos + Metadatos Auditados) / 3
- **All Scores**: Included en el cálculo general de calidad del dataset

## 10. Notas y Consideraciones

### 10.1 Sensibilidad de Frecuencia

La detección de frecuencia es **insensible a mayúsculas y caracteres especiales**:
- "anual" = "ANUAL" = "Anual" = "aNuAl" → Todas se tratan como 365 días

### 10.2 Valores Numéricos


## 10.5 Ubicación exacta del campo "Frecuencia de Actualización" en Socrata

Cuando los metadatos provienen de Socrata (p. ej. `www.datos.gov.co`), la frecuencia suele estar anidada en la estructura `metadata` dentro del JSON de vista. Ejemplo de acceso en Python:

```python
# Path recomendado (preferir este):
frecuencia = metadata.get('metadata', {}) \
                   .get('custom_fields', {}) \
                   .get('Información de Datos', {}) \
                   .get('Frecuencia de Actualización')

# Fallbacks útiles:
frecuencia = frecuencia or metadata.get('updateFrequency') or metadata.get('frecuencia_actualizacion')
```

Usar esta ruta evita falsos negativos cuando la frecuencia está en `custom_fields` (caso frecuente en vistas Socrata).
- "actualización cada 7 d" → 7

### 10.3 Caso Especial: "Más de tres años"

Si la frecuencia contiene la secuencia "más de tres años", se asigna automáticamente 10.0:
- Esto indica que el dataset tiene baja frecuencia de cambios
- Se considera válido cualquier estado de actualización

### 10.4 Fallback

Si los metadatos no contienen información suficiente:
- Se retorna **5.0** como puntuación neutral
- Permite que el análisis continúe sin fallos

## 11. Mejoras Futuras

- Implementar alertas cuando un dataset está próximo a desactualizarse
- Permitir configurar umbrales personalizados de actualización
- Integrar con calendarios de actualización esperados
- Generar reportes históricos de cumplimiento de actualización
