# Explicación Detallada: Métrica de Conformidad

## 🎯 ¿Qué es la Conformidad?

La **conformidad** mide qué tan bien se ajustan los datos a **patrones y formatos esperados**. Es decir, valida que los valores en columnas específicas cumplan con reglas de validación específicas según su tipo de dato.

---

## 📊 Fórmula de Cálculo

```
score = exp(-5 × (errores / total_validados))

Donde:
- errores = cantidad de valores que NO cumplen las reglas
- total_validados = cantidad total de valores validados
- exp = función exponencial natural
```

**Interpretación:**
- Score **cercano a 1.0** (máximo): Datos muy conformes (pocos errores)
- Score **cercano a 0.0** (mínimo): Datos no conformes (muchos errores)

---

## 🔍 Proceso Paso a Paso

### PASO 1: Detección de Columnas Relevantes
El sistema busca en los **nombres de columnas** patrones que coincidan con tipos específicos:

| Tipo | Patrones de búsqueda |
|------|----------------------|
| **departamento** | "departamento", "depto", "department" |
| **municipio** | "municipio", "ciudad", "city" |
| **año** | "año", "year", "anio" |
| **latitud** | "latitud", "latitude", "lat" |
| **longitud** | "longitud", "longitude", "lon", "long" |
| **correo** | "correo", "email", "mail" |

**Ejemplo:** Si tu dataset tiene columnas llamadas "departamento", "municipio", "año" → Se detectarán esas 3 columnas.

---

### PASO 2: Validación de Valores

Para CADA columna detectada, se valida cada valor según su tipo:

#### 🏛️ **DEPARTAMENTO**
- **Regla:** El valor debe ser un nombre de departamento colombiano válido
- **Lista válida:** Amazonas, Antioquia, Arauca, Atlántico, Bogotá D.C., Bolívar, Boyacá, Caldas, etc. (32 departamentos)
- **Normalización:** Se convierte a título (primera letra mayúscula)
- **Errores:** Si no coincide exactamente con la lista

#### 🏙️ **MUNICIPIO**
- **Regla:** El valor debe ser un municipio colombiano válido
- **Fuente:** Se obtiene de la API de Colombia (https://service.colombiaapi.io/)
- **Aproximadamente:** 1,100+ municipios válidos
- **Normalización:** Se convierte a título
- **Errores:** Si no coincide con la lista de municipios

#### 📅 **AÑO**
- **Regla:** Debe ser un número entre 1900 y 2025
- **Errores:** Textos, números negativos, años fuera del rango

#### 🗺️ **LATITUD**
- **Regla:** Número entre 0 y 13 (coordenadas geográficas de Colombia)
- **Errores:** Texto no convertible a número, valores fuera de rango

#### 🗺️ **LONGITUD**
- **Regla:** Número entre -81 y -66 (coordenadas geográficas de Colombia)
- **Errores:** Texto no convertible a número, valores fuera de rango

#### 📧 **CORREO**
- **Regla:** Formato válido de email (usuario@dominio.extensión)
- **Patrón regex:** `^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$`
- **Errores:** Formatos inválidos sin @, sin dominio, etc.

---

## ⚠️ RAZONES POR LAS QUE RETORNA 0

### Razón 1: **NO se detectan columnas relevantes**
```
Si tu dataset NO tiene columnas con nombres que contengan:
✗ "departamento", "depto"
✗ "municipio", "ciudad"
✗ "año", "year"
✗ "latitud", "lat"
✗ "longitud", "lon"
✗ "correo", "email"

→ El sistema retorna NULL (se interpreta como 0)
```

**Ejemplo problema:**
- Si tu columna se llama "col_1", "field_A", "dato" → No se detecta
- Si se llama "DEPARTAMENTO" (mayúsculas) → SÍ se detecta (búsqueda case-insensitive)
- Si se llama "dept_name" → NO se detecta (no contiene "departamento" ni "depto")

---

### Razón 2: **NO hay datos cargados**
```python
if self.df is None or len(self.df) == 0:
    return None  # → Se interpreta como 0
```

**Solución:** Debes llamar a `POST /load_data` ANTES de llamar a `/conformidad`

---

### Razón 3: **Muchos errores en los datos**
```
Si la mayoría de valores son inválidos:
- Ejemplo: Columna "año" contiene textos como "2024a", "año-2023"
- Entonces: errores ≈ total_validados
- Proporción: errores/total ≈ 1.0
- Score: exp(-5 × 1.0) = exp(-5) ≈ 0.0067 → Casi 0
```

---

### Razón 4: **API de Colombia no disponible** (para municipios)
```
Si la API https://service.colombiaapi.io/ falla:
- Se usa lista de respaldo de departamentos
- Para municipios: Se omite validación (retorna None/0)
```

---

## 📋 Ejemplo Completo de Cálculo

### Dataset de ejemplo:
```
departamento | municipio  | año  | latitud | longitud
Antioquia    | Medellín   | 2023 | 6.2     | -75.5
Antioquia    | Medellín   | 2024 | 6.2     | -75.5
Antioquia    | Medellín   | 2025 | 6.2     | -75.5
Antioquia    | XXX        | 2026 | 6.2     | -75.5   ← ERROR (año fuera de rango)
Antioquia    | Medellín   | 2023 | 6.2     | -75.5
```

### Cálculo:
```
Columnas detectadas: departamento, municipio, año, latitud, longitud

Validación:
- departamento: 5 valores, 0 errores ✓
- municipio: 5 valores, 1 error (XXX no es municipio válido) ✗
- año: 5 valores, 1 error (2026 > 2025) ✗
- latitud: 5 valores, 0 errores ✓
- longitud: 5 valores, 0 errores ✓

Totales:
- total_validados = 25
- total_errores = 2
- proporcion_errores = 2/25 = 0.08

score = exp(-5 × 0.08) = exp(-0.4) ≈ 0.67
```

---

## 🔧 Cómo Verificar por qué tu Dataset da 0

### 1. **Verifica que el dataset tenga datos cargados**
```bash
POST /load_data
# Debe retornar rows > 0
```

### 2. **Verifica los nombres de tus columnas**
```bash
POST /initialize?dataset_id=tu_dataset_id
# Revisa el nombre en "dataset_name" y el número de "columns"
```

### 3. **Agrega debug al código**
En `main.py`, endpoint `/conformidad`, descomenta estos prints:

```python
# Descomenta alrededor de línea 1168
detected = self._detect_relevant_columns(metadata)
print(f"🔎 Detectadas: {detected}")  # ← VE QUÉ COLUMNAS ENCONTRÓ
```

---

## ✅ Soluciones para Mejorar el Score

### Solución 1: Asegurar que haya columnas detectables
Renombra tus columnas para que contengan los patrones:
```
❌ col_1 → ✅ año_datos
❌ field_A → ✅ departamento
❌ dept → ✅ departamento_residence  (contiene "departamento")
```

### Solución 2: Limpiar datos inválidos
```python
# Si tienes "año" con valores como "2024a", "NA", etc.
df['año'] = pd.to_numeric(df['año'], errors='coerce')
df = df[df['año'].notna()]
```

### Solución 3: Validar formato correo
```python
# Si tienes emails inválidos
import re
email_pattern = r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$"
df['correo'] = df['correo'].apply(
    lambda x: x if re.match(email_pattern, str(x)) else None
)
```

### Solución 4: Usar coordenadas válidas para Colombia
```python
# Latitudes válidas: 0° a 13°
# Longitudes válidas: -81° a -66°
df = df[(df['latitud'] >= 0) & (df['latitud'] <= 13)]
df = df[(df['longitud'] >= -81) & (df['longitud'] <= -66)]
```

---

## 📊 Resumen Visual

```
┌─────────────────────────────────────────────────┐
│   Flujo de Cálculo de Conformidad               │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. ¿Datos cargados? (load_data)               │
│     NO → Retorna NULL (0)                       │
│     SÍ ↓                                        │
│                                                 │
│  2. ¿Detecta columnas relevantes?               │
│     NO → Retorna NULL (0)                       │
│     SÍ ↓                                        │
│                                                 │
│  3. Valida CADA valor según tipo                │
│     Cuenta errores                              │
│     ↓                                           │
│                                                 │
│  4. score = exp(-5 × errores/total)             │
│     ↓                                           │
│     Retorna valor entre 0 y 1                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Diagnóstico Rápido

Si obtienes **score = 0**, verifica en orden:

| # | Verificar | Comando/Acción |
|---|-----------|---|
| 1 | ¿Datos cargados? | `POST /load_data` luego `GET /completitud` (si da score > 0, hay datos) |
| 2 | ¿Columnas detectables? | Busca en tus columnas: "departamento", "municipio", "año", "latitud", "longitud", "correo" |
| 3 | ¿Datos válidos? | Exporta datos y revisa si cumplen con los formatos esperados |
| 4 | ¿API de Colombia disponible? | Prueba: `curl https://service.colombiaapi.io/api/v1/Location/departments` |
| 5 | Habilita debug | Descomenta prints en líneas ~1168 de `data_quality_calculator.py` |

