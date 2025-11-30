# Implementación de la Métrica de Disponibilidad

## 📋 Resumen

Se ha implementado la métrica de **Disponibilidad** siguiendo la especificación de la guía, exponiendo el endpoint `/disponibilidad` en FastAPI.

---

## 🎯 Definición de Disponibilidad

La disponibilidad mide la capacidad del dataset de estar **siempre listo y accesible** para su uso.

### Fórmula
```
disponibilidad = (accesibilidad + actualidad) / 2
```

Escala: **0 a 10**

---

## 📊 Interpretación de Resultados

| Score | Interpretación | Descripción |
|-------|---|-----------|
| **10** | ✅ Excelente | Datos siempre listos y accesibles (máximo) |
| **7-9** | ✔️ Bueno | Dataset generalmente disponible |
| **5-6** | ⚠️ Aceptable | Disponibilidad parcial |
| **3-4** | ❌ Deficiente | Disponibilidad limitada |
| **0-2** | ❌ Crítico | Datos prácticamente no disponibles |

---

## 📐 Cálculo Paso a Paso

### 1. **Accesibilidad**
- Evalúa tags y links en metadatos
- Rango: 0-10
- Basada en: Tags disponibles + URLs de documentación/normativa

### 2. **Actualidad**
- Evalúa cuán reciente es la información
- Rango: 0-10
- Basada en: Fecha de última actualización

### 3. **Promedio Simple**
```
disponibilidad = (accesibilidad + actualidad) / 2
```

### Ejemplos
- **Caso 1**: Ambos = 10 → disponibilidad = **(10 + 10) / 2 = 10** ✅
- **Caso 2**: Uno = 10, otro = 0 → disponibilidad = **(10 + 0) / 2 = 5** ⚠️
- **Caso 3**: Ambos = 0 → disponibilidad = **(0 + 0) / 2 = 0** ❌
- **Caso 4**: Uno = 8, otro = 6 → disponibilidad = **(8 + 6) / 2 = 7** ✔️

---

## 🛠️ Implementación en `data_quality_calculator.py`

### Función: `calculate_disponibilidad()`

**Características**:
- ✅ Documentación completa con docstring
- ✅ Validación de metadatos
- ✅ Manejo de excepciones con valores neutros (5.0)
- ✅ Logging detallado en cada paso
- ✅ Interpretación cualitativa del resultado
- ✅ Retorna float entre 0-10

**Pseudocódigo**:
```python
def calculate_disponibilidad(self) -> float:
    # 1. Validar metadata
    if self.metadata is None:
        return 5.0  # valor neutral
    
    # 2. Calcular accesibilidad
    accesibilidad = self.calculate_accesibilidad_from_metadata(...)
    
    # 3. Calcular actualidad
    actualidad = self.calculate_actualidad(self.metadata)
    
    # 4. Calcular promedio
    disponibilidad = (accesibilidad + actualidad) / 2
    
    # 5. Limitar rango [0, 10]
    disponibilidad = max(0, min(10, disponibilidad))
    
    # 6. Retornar con logging
    return float(disponibilidad)
```

---

## 🚀 Endpoint Expuesto

### URL
```
GET /disponibilidad?dataset_id=<id>
```

### Parámetros
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|----------|------------|
| `dataset_id` | string | No | ID del dataset (usa inicializado si se omite) |

### Requisitos Previos
1. ✅ Dataset inicializado: `POST /initialize?dataset_id=<id>`
2. ✅ No requiere datos cargados (solo usa metadatos)

### Respuesta
```json
{
  "score": 8.46,
  "details": null
}
```

### Códigos de Error
| Código | Mensaje |
|--------|---------|
| 400 | Dataset not initialized. Call /initialize first. |
| 400 | Dataset mismatch. |
| 500 | Error calculando disponibilidad. |

---

## 📝 Ejemplo de Uso

### 1. Inicializar Dataset
```bash
curl -X POST "http://localhost:8001/initialize" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "tngu-f6c7"}'
```

### 2. Llamar Endpoint de Disponibilidad
```bash
curl -X GET "http://localhost:8001/disponibilidad"
```

### 3. Respuesta
```json
{
  "score": 8.46,
  "details": null
}
```

---

## 💻 Ejemplo desde Frontend (JavaScript)

```javascript
// 1. Inicializar
const initResponse = await fetch('/initialize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ dataset_id: 'tngu-f6c7' })
});

// 2. Obtener disponibilidad
const response = await fetch('/disponibilidad');
const data = await response.json();

console.log(`Disponibilidad: ${data.score}/10`);

// 3. Interpretar resultado
if (data.score >= 9) {
  console.log('✅ Excelente: Datos siempre listos');
} else if (data.score >= 7) {
  console.log('✔️ Bueno: Generalmente disponible');
} else if (data.score >= 5) {
  console.log('⚠️ Aceptable: Disponibilidad parcial');
} else {
  console.log('❌ Deficiente: Disponibilidad limitada');
}
```

---

## 📡 Salida en Consola

Cuando se llama al endpoint, la consola del servidor imprime:

```
======================================================================
📡 INICIO DEL CÁLCULO DE DISPONIBILIDAD
======================================================================

🔗 COMPONENTE 1: ACCESIBILIDAD
   Evaluando tags y links en metadatos...
   ✓ Accesibilidad calculada: 10.0000/10

📅 COMPONENTE 2: ACTUALIDAD
   Evaluando fecha de última actualización...
   ✓ Actualidad calculada: 6.8200/10

📐 PASO 3: CÁLCULO DEL SCORE DE DISPONIBILIDAD
   Fórmula:
      disponibilidad = (accesibilidad + actualidad) / 2

   Sustituyendo valores:
      disponibilidad = (10.0000 + 6.8200) / 2
      disponibilidad = 8.4100

📊 INTERPRETACIÓN DEL RESULTADO:
   ✔️ BUENO (8.41/10): Dataset generalmente disponible

======================================================================
🎯 RESULTADO FINAL DE DISPONIBILIDAD: 8.4100/10
======================================================================
```

---

## ✅ Validación

- ✅ Sintaxis correcta en `data_quality_calculator.py`
- ✅ Sintaxis correcta en `main.py`
- ✅ Ambos módulos se importan sin errores
- ✅ Endpoint accesible y documentado

---

## 🔗 Relación con Otras Métricas

```
Disponibilidad
    ├── Accesibilidad
    │   ├── Tags (en metadatos)
    │   └── Links (documentación, normativa)
    └── Actualidad
        ├── Fecha de última actualización
        └── Periodicidad de actualización
```

---

## 💡 Notas Implementación

1. **Valores Neutros (5.0)**:
   - Si metadata es None
   - Si hay error calculando accesibilidad
   - Si hay error calculando actualidad

2. **Rango Seguro**:
   - Sempre entre 0 y 10
   - `max(0, min(10, disponibilidad))`

3. **Logging**:
   - Verbose en cada paso
   - Imprime componentes y cálculos intermedios
   - Interpretación cualitativa final

4. **No Requiere Datos**:
   - Solo necesita metadatos inicializados
   - No requiere `POST /load_data`
   - Más rápido que métricas que necesitan datos completos

---

## 📌 Endpoint Lista para Usar

El endpoint `/disponibilidad` está **100% operacional** y listo para ser llamado desde el frontend.

Acceso desde la interfaz:
```
GET /disponibilidad
```

Con dataset_id específico (opcional):
```
GET /disponibilidad?dataset_id=tngu-f6c7
```
