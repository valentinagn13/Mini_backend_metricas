# 🎯 Quick Reference - Data Quality Assessment Backend

## 🚀 Inicio Rápido (2 minutos)

### Instalación
```bash
pip install -r requirements.txt
python main.py
```

### Test Rápido
```bash
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej"}'

curl http://localhost:8001/actualidad?dataset_id=ijus-ubej
```

---

## 📡 Endpoints - Tabla Rápida

| Endpoint | Método | Requiere Datos | Score | Descripción |
|----------|--------|---|-------|-------------|
| `/` | GET | ❌ | - | Health check |
| `/initialize` | POST | ❌ | - | Cargar metadatos |
| `/load_data` | POST | ❌ | - | Cargar datos (50K) |
| `/actualidad` | GET | ❌ | 0-10 | ¿Qué tan reciente? |
| `/accesibilidad` | GET | ❌ | 0-10 | ¿Fácil acceso? |
| `/confidencialidad` | GET | ❌ | 0-10 | ¿Datos seguros? |
| `/portabilidad` | GET | ❌ | 0-10 | ¿Se descarga fácil? |
| `/disponibilidad` | GET | ❌ | 0-10 | ¿Siempre disponible? |
| `/trazabilidad` | GET | ❌ | 0-10 | ¿Bien documentado? |
| `/conformidad` | GET | ⚠️ | 0-10 | ¿Cumple estándares? |
| `/completitud` | GET | ✅ | 0-10 | ¿Faltan valores? |
| `/credibilidad` | GET | ✅ | 0-10 | ¿Es confiable? |
| `/unicidad` | GET | ✅ | 0-10 | ¿Hay duplicados? |
| `/recuperabilidad` | GET | ✅ | 0-10 | ¿Se recupera bien? |

---

## 🔑 Variables de Entorno Críticas

```env
# ⚠️ REQUERIDAS
SOCRATA_API_KEY=YOUR_KEY                 # ← CRÍTICA
SOCRATA_USERNAME=user@example.com
SOCRATA_PASSWORD=password

# Recomendadas
HOST=0.0.0.0                              # ← Para producción
PORT=8001
DEBUG=False                               # ← Cambiar a False en prod
CORS_ORIGINS=https://tudominio.com        # ← Específico en prod

# Opcionales (valores por defecto están bien)
DEFAULT_RECORDS_LIMIT=50000
TIMEOUT_REQUEST=30
LOG_LEVEL=INFO
```

---

## 🚨 Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `Dataset not initialized` | No llamaste `/initialize` | `POST /initialize` primero |
| `Dataset mismatch` | `dataset_id` no coincide | Usar mismo `dataset_id` en todos |
| `Data not loaded` | No llamaste `/load_data` | `POST /load_data` primero |
| `API Key invalid` | Credenciales Socrata malas | Verificar `.env` |
| `Timeout` | Dataset muy grande | Aumentar `TIMEOUT_REQUEST` |

---

## 📊 Flujo Típico

```
1. POST /initialize
   └─ Recibe: {"dataset_id": "ijus-ubej"}
   └─ Retorna: metadata info

2. GET /actualidad?dataset_id=ijus-ubej
   └─ Retorna: {"score": 8.5, "details": {...}}

3. GET /conformidad?dataset_id=ijus-ubej
   └─ Retorna: {"score": 8.9, "details": {...}}

(Opcional para métricas que usen datos):

4. POST /load_data
   └─ Carga 50K registros

5. GET /completitud?dataset_id=ijus-ubej
   └─ Retorna: {"score": 8.2, "details": {...}}
```

---

## 🎯 ¿Cuál Métrica Usar?

```
¿Qué tan reciente?           → /actualidad
¿Fácil de acceder?           → /accesibilidad
¿Datos son seguros?          → /confidencialidad
¿Se puede descargar?         → /portabilidad
¿Siempre disponible?         → /disponibilidad
¿Está documentado?           → /trazabilidad
¿Tiene valores nulos?        → /completitud
¿Es confiable?               → /credibilidad
¿Hay duplicados?             → /unicidad
¿Cumple estándares?          → /conformidad
¿Se puede recuperar?         → /recuperabilidad
```

---

## 💻 Comandos Útiles

### Inicializar dataset
```bash
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ijus-ubej", "load_full": false}'
```

### Obtener score (sin datos)
```bash
curl http://localhost:8001/actualidad?dataset_id=ijus-ubej
```

### Cargar datos
```bash
curl -X POST http://localhost:8001/load_data
```

### Obtener score (con datos)
```bash
curl http://localhost:8001/completitud?dataset_id=ijus-ubej
```

### Ver logs
```bash
tail -f logs/api.log
```

---

## 🐳 Docker

### Build
```bash
docker build -t quality-api:1.0 .
```

### Run
```bash
docker run --env-file .env -p 8001:8001 quality-api:1.0
```

---

## 📚 Documentación

| Documento | Para Qué |
|-----------|----------|
| **README.md** | Primeros pasos |
| **DOCUMENTACION_PROYECTO.md** | Referencia completa |
| **GUIA_TECNICA.md** | Detalles técnicos |
| **EJEMPLOS_USO.md** | Ejemplos prácticos |
| **DEPLOYMENT.md** | Deployment producción |
| **DOCUMENTACION_INDEX.md** | Navegar documentación |

---

## ⚡ Performance Tips

✅ **Rápido** (~100ms)
- GET /actualidad (solo metadata)
- GET /accesibilidad (solo metadata)

⚠️ **Medio** (~2-5s)
- POST /load_data (carga 50K registros)

🐌 **Lento** (~5-30s)
- GET /completitud (si dataset > 10K registros)
- GET /unicidad (detección de duplicados)

---

## 🔒 Producción Checklist

```
☐ DEBUG=False
☐ CORS_ORIGINS especificado
☐ API Key Socrata válida
☐ Logs a archivo
☐ Nginx reverse proxy
☐ SSL certificate
☐ Monitoreo habilitado
☐ Backup de .env en secrets manager
☐ Rate limiting configurado
☐ Alertas configuradas
```

---

## 📊 Score Interpretation

```
10.0 │ ████████████████ Excelente (95-100%)
8.0  │ █████████████    Muy bueno (80-94%)
6.0  │ ██████████       Bueno (60-79%)
4.0  │ ███████          Aceptable (40-59%)
2.0  │ ④               Deficiente (20-39%)
0.0  │                 Crítico (0-19%)
```

---

## 🔧 Debugging

### Ver qué dataset está inicializado
```bash
# En logs, buscar:
grep "Inicializando dataset" logs/api.log
```

### Ver detalles de métrica
```bash
curl http://localhost:8001/conformidad?dataset_id=ijus-ubej | python -m json.tool
```

### Test de conectividad Socrata
```bash
curl https://www.datos.gov.co/api/views/ijus-ubej
```

---

## 🎓 Equivalencias en Otros Backends

| Nuestro | Main-Backend | Función |
|---------|---|---|
| DataQualityCalculator | AssetInventoryAnalyzer | Motor de cálculos |
| `/initialize` | (sin equivalente directo) | Setup |
| `/actualidad` | `metrics.maintenance_activity` | Frescura de datos |
| `/completitud` | `metrics.content_coverage` | Integridad |
| Sodapy + Socrata | asset_inventory.json | Fuente de datos |

---

## 📞 Troubleshooting Rápido

| Problema | Pasos |
|----------|-------|
| No funciona | 1. Ver logs: `tail -f logs/api.log` 2. Verificar `.env` 3. Reiniciar |
| Muy lento | 1. Reducir `DEFAULT_RECORDS_LIMIT` 2. Verificar conectividad |
| Error 400 | 1. Reinicializar dataset 2. Usar mismo `dataset_id` |
| API rechaza | 1. Verificar API Key 2. Verificar internet |

---

## 🔗 URLs Importantes

- **API Local**: http://localhost:8001
- **datos.gov.co**: https://www.datos.gov.co
- **Socrata API Docs**: https://dev.socrata.com
- **FastAPI Docs**: https://fastapi.tiangolo.com

---

## 📋 Respuesta Típica

```json
{
  "score": 8.5,
  "details": {
    "metric_value": 42,
    "total_value": 100,
    "percentage": 84.0,
    "status": "good"
  }
}
```

---

**Última actualización**: 30 de noviembre de 2025  
**Imprime o guarda como bookmark** ⭐
