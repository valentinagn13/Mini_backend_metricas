# 🚀 INICIO RÁPIDO - Métrica de Conformidad Mejorada

## ✅ Lo que fue Cambiado

1. **Score = 10.0** si NO hay columnas relevantes (antes: 0)
2. **Sin API Externa** - Usa listas locales de departamentos y municipios
3. **Validación robusta** - Departamentos, municipios, años, coordenadas, emails

---

## 🔥 Inicio Rápido

### 1. Iniciar el servidor

```bash
cd "c:\Users\galvi\OneDrive\Escritorio\HACKATON\project-bolt-sb1-fcgeqr6o\project"
python main.py
```

Espera hasta ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 2. En otra terminal, hacer una prueba

```bash
# Reemplaza "dataset_id" con un ID real de DATOS.GOV.CO

# Inicializar dataset
curl -X POST http://localhost:8001/initialize ^
  -H "Content-Type: application/json" ^
  -d "{\"dataset_id\": \"dataset_id\"}"

# Cargar datos
curl -X POST http://localhost:8001/load_data

# Calcular conformidad
curl -X GET "http://localhost:8001/conformidad"
```

### 3. Usar el diagnóstico automático

```bash
python diagnostico_conformidad.py dataset_id
```

---

## 📊 Qué Esperar

### Sin columnas relevantes
```json
{
  "score": 10.0,
  "details": null
}
```
✅ Perfecto - Sin columnas para validar

### Con columnas y datos válidos
```json
{
  "score": 9.5,
  "details": {
    "total_validated": 2500,
    "total_errors": 12,
    "error_rate": 0.0048
  }
}
```
✅ Excelente - Datos válidos

### Con columnas y datos inválidos
```json
{
  "score": 1.2,
  "details": {
    "total_validated": 2500,
    "total_errors": 2400,
    "error_rate": 0.96
  }
}
```
⚠️ Deficiente - Necesita limpieza

---

## 📝 Validación Automática

Si tu dataset tiene estas columnas, se valida automáticamente:

| Columna | Se valida si se llama | Valores válidos |
|---------|----------------------|-----------------|
| **Departamento** | "departamento", "depto" | Antioquia, Bogotá D.C., etc. |
| **Municipio** | "municipio", "ciudad" | ~1,100 municipios colombianos |
| **Año** | "año", "year" | 1900-2025 |
| **Latitud** | "latitud", "lat" | 0-13 |
| **Longitud** | "longitud", "lon" | -81 a -66 |
| **Correo** | "correo", "email" | usuario@dominio.ext |

---

## 🐛 Si Algo Falla

### Error: "Score = 0"
❌ **Antes:** Era normal
✅ **Ahora:** Significa que hay muchos errores en validación

**Solución:** Revisa tus datos en las columnas detectadas

### Error: "Port 8001 already in use"
```bash
# En PowerShell
Get-Process | Where-Object {$_.Name -like "*python*"}
Stop-Process -Name python -Force
```

### Error: "Module not found"
```bash
# Verifica estar en el directorio correcto
cd "c:\Users\galvi\OneDrive\Escritorio\HACKATON\project-bolt-sb1-fcgeqr6o\project"
```

---

## 📚 Documentación Completa

- **MEJORAS_CONFORMIDAD.md** - Detalles técnicos
- **EXPLICACION_CONFORMIDAD.md** - Cómo funciona
- **GUIA_PRUEBAS_CONFORMIDAD.md** - Casos de prueba
- **RESUMEN_MEJORAS_CONFORMIDAD.md** - Resumen ejecutivo

---

## ✨ Nuevas Características

✅ Sin depender de APIs externas  
✅ Score predecible (10.0 por defecto)  
✅ Validación local y rápida  
✅ Script de diagnóstico incluido  
✅ Documentación completa  

---

## 🎯 Próximos Pasos

1. ✅ Inicia el servidor
2. ✅ Prueba con un dataset conocido
3. ✅ Usa `diagnostico_conformidad.py` para entender resultados
4. ✅ Lee la documentación si necesitas detalles
5. ✅ ¡Disfruta de la métrica mejorada!

---

**¡Listo! 🚀**

