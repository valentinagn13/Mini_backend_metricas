# Ubicación del Campo de Frecuencia de Actualización en JSON de Socrata

## Respuesta Corta

El campo de **frecuencia de actualización** se obtiene de:

```json
metadata.custom_fields["Información de Datos"]["Frecuencia de Actualización"]
```

## Estructura del JSON Completo

La API de Socrata devuelve un JSON con esta estructura para los metadatos:

```
{
  "id": "8dbv-wsjq",
  "name": "Registro de Activos de Información Colpensiones",
  "rowsUpdatedAt": 1735320928,              ← Timestamp de última actualización
  "metadata": {
    "custom_fields": {
      "Información de la Entidad": { ... },
      "Información de Datos": {
        "Cobertura Geográfica": "Nacional",
        "Idioma": "Español",
        "Frecuencia de Actualización": "Anual",  ← CAMPO CLAVE
        "URL Documentación": "...",
        "Fecha Emisión (aaaa-mm-dd)": "2023",
        "URL Normativa": "..."
      }
    },
    ...
  },
  ...
}
```

## Ruta de Acceso en el Código Python

```python
# Obteniendo los metadatos desde la API
metadata = requests.get(f"https://www.datos.gov.co/api/views/{dataset_id}").json()

# Accediendo al campo de frecuencia
frecuencia = metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('Frecuencia de Actualización')

# Resultado en este ejemplo:
# frecuencia = "Anual"
```

## Campos Clave para la Métrica de Actualidad

| Campo | Ubicación | Tipo | Ejemplo | Propósito |
|-------|-----------|------|---------|-----------|
| **Fecha de última actualización** | `rowsUpdatedAt` (raíz del JSON) | Unix timestamp | `1735320928` | Saber cuándo se actualizaron los datos |
| **Frecuencia esperada** | `metadata.custom_fields["Información de Datos"]["Frecuencia de Actualización"]` | String | `"Anual"` | Comparar si está dentro del período |

## Ejemplo de Extracción en main.py

```python
def extract_update_frequency(metadata: Dict) -> str:
    """Extrae la frecuencia de actualización del JSON de metadatos de Socrata"""
    try:
        # Intentar acceder a la ruta anidada
        frecuencia = (
            metadata
            .get('metadata', {})
            .get('custom_fields', {})
            .get('Información de Datos', {})
            .get('Frecuencia de Actualización', 'Por defecto')
        )
        return frecuencia
    except:
        return 'No especificada'

# Uso en la API
metadata = obtener_metadatos_socrata(dataset_id)
frecuencia = extract_update_frequency(metadata)
print(f"📅 Frecuencia: {frecuencia}")  # Output: "Frecuencia: Anual"
```

## Campos Disponibles en "Información de Datos"

Según el dataset ejemplo (8dbv-wsjq), estos son los campos que puede contener:

```json
"Información de Datos": {
  "Cobertura Geográfica": "Nacional",           // Alcance geográfico
  "Idioma": "Español",                          // Idioma de los datos
  "Frecuencia de Actualización": "Anual",       // ✅ EL QUE USAMOS
  "URL Documentación": "https://...",           // Enlace a documentación
  "Fecha Emisión (aaaa-mm-dd)": "2023",        // Cuándo se emitió
  "URL Normativa": "https://..."                // Normativa relacionada
}
```

## Valores Comunes de Frecuencia

- "Anual"
- "Mensual"
- "Semanal"
- "Diario"
- "Por demanda"
- "Más de tres años"
- "Semestral"
- "Trimestral"
- "Cada 30 días"
- etc.

## Nota Importante

⚠️ **No todos los datasets tienen este campo lleno**. Algunos pueden tener:
- Campo vacío
- Campo ausente
- Valor `null`

Por eso en el código implementamos un **fallback a 5.0** (puntuación neutral) cuando no se encuentra información.

## Cómo lo Usa calculate_actualidad

```python
def calculate_actualidad(self, metadata: Optional[Dict] = None) -> float:
    metadata = metadata or self.metadata or {}
    
    # 1. Obtener frecuencia
    frecuencia_str = (
        metadata.get('metadata', {})
        .get('custom_fields', {})
        .get('Información de Datos', {})
        .get('Frecuencia de Actualización')
    )
    
    # 2. Obtener fecha de última actualización
    rows_updated_at = metadata.get('rowsUpdatedAt')
    
    # 3. Convertir frecuencia a días
    frecuencia_dias = self._convertir_frecuencia_a_dias(frecuencia_str)
    
    # 4. Calcular diferencia de días
    diferencia_dias = (datetime.now() - datetime.fromtimestamp(rows_updated_at)).days
    
    # 5. Comparar y devolver puntuación
    return 10.0 if diferencia_dias <= frecuencia_dias else 0.0
```

## Validación en tu Código

Si quieres verificar que el campo existe en los metadatos que recibes:

```python
import json

metadata = obtener_metadatos_socrata(dataset_id)

# Imprimir para debug
print(json.dumps(metadata, indent=2, ensure_ascii=False))

# Acceder seguro
info_datos = metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {})
print(f"Frecuencia: {info_datos.get('Frecuencia de Actualización', 'No disponible')}")
print(f"Última actualización: {metadata.get('rowsUpdatedAt', 'No disponible')}")
```
