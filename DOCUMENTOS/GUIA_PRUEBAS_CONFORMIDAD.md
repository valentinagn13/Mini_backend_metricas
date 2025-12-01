# 🧪 Guía de Pruebas - Métrica de Conformidad Mejorada

## Paso 1: Iniciar el servidor

```bash
cd "c:\Users\galvi\OneDrive\Escritorio\HACKATON\project-bolt-sb1-fcgeqr6o\project"
python main.py
```

Deberías ver:
```
🌐 Iniciando servidor Data Quality API en puerto 8001...
📚 Características: Paginación habilitada para datasets grandes
INFO:     Started server process [XXXX]
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## Paso 2: Pruebas Básicas

### Test 1: Dataset SIN columnas relevantes
```bash
# Inicializar (cualquier dataset que no tenga departamento, municipio, año, etc.)
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "un_dataset_sin_columnas_relevantes"}'

# Cargar datos
curl -X POST http://localhost:8001/load_data

# Calcular conformidad
curl -X GET "http://localhost:8001/conformidad"
```

**Resultado esperado:**
```json
{
  "score": 10.0,
  "details": null
}
```

✅ **Significado:** Sin columnas para validar → Score perfecto (10.0)

---

### Test 2: Dataset CON columnas relevantes (datos válidos)
```bash
# Inicializar dataset con columnas: departamento, municipio, año
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "dataset_con_datos_validos"}'

# Cargar datos
curl -X POST http://localhost:8001/load_data

# Calcular conformidad
curl -X GET "http://localhost:8001/conformidad"
```

**Resultado esperado:**
```json
{
  "score": 9.5,  // o similar (cercano a 10)
  "details": {
    "columns_validated": [
      {
        "column": "departamento",
        "type": "departamento",
        "total": 1000,
        "errors": 2,
        "examples": ["Departamento Inventado"]
      }
    ],
    "total_validated": 3000,
    "total_errors": 5,
    "error_rate": 0.00167
  }
}
```

✅ **Significado:** Datos mayoritariamente válidos → Score alto

---

### Test 3: Dataset CON columnas relevantes (datos inválidos)
```bash
# Usar dataset con datos malformados
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "dataset_con_datos_invalidos"}'

# Cargar datos
curl -X POST http://localhost:8001/load_data

# Calcular conformidad
curl -X GET "http://localhost:8001/conformidad"
```

**Resultado esperado:**
```json
{
  "score": 2.5,  // o similar (bajo)
  "details": {
    "columns_validated": [...],
    "total_validated": 1000,
    "total_errors": 950,
    "error_rate": 0.95
  }
}
```

⚠️ **Significado:** Muchos datos inválidos → Score bajo

---

## Paso 3: Usar el Script de Diagnóstico

```bash
# Ejecutar diagnóstico completo para un dataset
python diagnostico_conformidad.py pbhj-r8dg

# Salida esperada:
# ==================================================================
# 🔍 DIAGNÓSTICO DE CONFORMIDAD v2.0 - Dataset: pbhj-r8dg
# ==================================================================
#
# 📋 PASO 1: Inicializando dataset...
# ✅ Dataset inicializado
#    - Nombre: Dataset de Prueba
#    - Columnas detectadas: 15
#
# 📦 PASO 2: Cargando datos completos...
# ✅ Datos cargados
#    - Filas: 2500
#    - Columnas: 15
#
# 🔎 PASO 3: Analizando columnas para detección...
#    Columnas encontradas: 15
#    - Ejemplos: ['id', 'departamento', 'municipio', 'año', ...]
#
#    📍 Columnas DETECTADAS para validación:
#       ✅ departamento      → ['departamento']
#       ✅ municipio         → ['municipio']
#       ✅ año               → ['año']
#       ❌ latitud           → (no encontrado)
#       ❌ longitud          → (no encontrado)
#       ❌ correo            → (no encontrado)
#
# 📊 PASO 4: Calculando conformidad...
# ✅ Score de conformidad: 8.75
#
# ==================================================================
# 📊 RESUMEN FINAL
# ==================================================================
#
# Dataset: pbhj-r8dg
# Score: 8.75
# Columnas detectadas: 3
```

---

## Cambios Respecto a la Versión Anterior

| Aspecto | Antes (v1.0) | Después (v2.0) |
|--------|-------------|--------------|
| Sin columnas relevantes | Score = 0 ❌ | Score = 10.0 ✅ |
| Fuente de datos | API Externa (colombia.com) | Listas Locales |
| Dependencias | Requería API | Sin dependencias externas |
| Errores por API | Falla → Score = 0 | No aplica |
| Confiabilidad | Media (depende API) | Alta (datos locales) |
| Velocidad | Lenta (espera API) | Rápida (búsqueda local) |

---

## 🎯 Casos de Prueba Específicos

### Caso 1: Dataset Vacío
```bash
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "dataset_vacio"}'

curl -X POST http://localhost:8001/load_data
curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score = 0.0 (sin datos para validar)

---

### Caso 2: Departamentos Válidos
```bash
# Dataset donde la columna "departamento" tiene valores como:
# Antioquia, Bogotá D.C., Valle del Cauca, etc.

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score > 8.0 (departamentos válidos)

---

### Caso 3: Departamentos Inválidos
```bash
# Dataset donde la columna "departamento" tiene valores como:
# "Departamento XYZ", "Bogota" (sin acentos), "ANTIOQUIA" (no normaliza bien)

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score < 3.0 (muchos errores)

---

### Caso 4: Años Válidos
```bash
# Columna "año" con valores entre 1900-2025

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score > 9.0

---

### Caso 5: Años Inválidos
```bash
# Columna "año" con valores como: "2099", "1800", "2024a", "XX"

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score < 2.0

---

### Caso 6: Correos Válidos
```bash
# Columna "correo" con valores como: usuario@ejemplo.com, nombre@dominio.co

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score > 9.0

---

### Caso 7: Correos Inválidos
```bash
# Columna "correo" con valores como: "usuario @ejemplo.com", "email@", "noesmail"

curl -X GET "http://localhost:8001/conformidad"
```
**Esperado:** score < 2.0

---

## ✅ Checklist de Validación

- [ ] Servidor inicia sin errores
- [ ] Test 1: Score = 10.0 cuando no hay columnas relevantes
- [ ] Test 2: Score alto (>8) cuando datos son válidos
- [ ] Test 3: Score bajo (<3) cuando datos son inválidos
- [ ] Script de diagnóstico funciona correctamente
- [ ] No hay llamadas a API externa (verificar con monitor de red)
- [ ] Listas locales funcionan para departamentos y municipios
- [ ] Validaciones funcionan para año, latitud, longitud, correo

---

## 🐛 Troubleshooting

### Problema: "No module named 'data_quality_calculator'"
**Solución:** Verifica que estés en el directorio correcto
```bash
cd "c:\Users\galvi\OneDrive\Escritorio\HACKATON\project-bolt-sb1-fcgeqr6o\project"
```

### Problema: Puerto 8001 ya está en uso
**Solución:** Termina el proceso anterior o usa otro puerto
```bash
# En PowerShell, encuentra el proceso
Get-Process | Where-Object {$_.Name -like "*python*"}

# Termina el proceso
Stop-Process -Name python -Force
```

### Problema: "Error connecting to API"
**Solución:** No debería haber errores de API ya que se usan listas locales. Si ocurre, verifica:
```bash
# Los metadatos aún se obtienen de Socrata (DATOS.GOV.CO), no de Colombia API
# Verifica conectividad a https://www.datos.gov.co
```

---

## 📊 Métricas de Éxito

- ✅ Sin API externa = menos errores
- ✅ Score = 10.0 por defecto = comportamiento esperado
- ✅ Validación local = respuestas consistentes
- ✅ Diagnóstico funcional = fácil debugging

