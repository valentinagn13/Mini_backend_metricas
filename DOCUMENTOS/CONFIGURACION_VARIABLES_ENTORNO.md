# 🔐 Configuración de Variables de Entorno

## Descripción General

Este proyecto usa **variables de entorno** para mantener las credenciales y configuraciones sensibles **fuera del código**. Esto es una práctica de seguridad esencial para:

- ✅ Evitar exponer credenciales en Git
- ✅ Permitir diferentes configuraciones por ambiente (desarrollo, staging, producción)
- ✅ Facilitar el despliegue en diferentes infraestructuras
- ✅ Cumplir con estándares de seguridad

## Archivos Relacionados

| Archivo | Propósito | En Git |
|---------|----------|--------|
| `.env` | **SECRETO**: Variables de entorno reales con credenciales | ❌ NO (añadir a `.gitignore`) |
| `.env.example` | **PÚBLICO**: Plantilla con estructura y documentación | ✅ SÍ (para referencia) |

## Instalación Inicial

### 1️⃣ Instalar Dependencia

```bash
pip install python-dotenv
```

### 2️⃣ Crear Archivo `.env`

```bash
# Opción A: Copiar del ejemplo
cp .env.example .env

# Opción B: Crear manualmente
echo ".env" >> .gitignore  # Asegurar que no se commit
```

### 3️⃣ Editar `.env` con Credenciales Reales

```bash
# Abre .env con tu editor favorito
nano .env
# o
code .env
```

Reemplaza los valores de ejemplo con los reales:

```env
SOCRATA_API_KEY=tu_api_key_real
SOCRATA_USERNAME=tu_email@real.com
SOCRATA_PASSWORD=tu_password_real
```

### 4️⃣ Verificar `.gitignore`

Asegúrate de que `.env` está en el `.gitignore`:

```bash
echo ".env" >> .gitignore
```

## Variables Disponibles

### 🖥️ Configuración del Servidor

```env
HOST=0.0.0.0                    # Host de escucha
PORT=8001                       # Puerto
ENV=development                 # Ambiente: development, staging, production
DEBUG=False                      # Modo debug
```

**Ejemplos de Uso:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", 8001))
```

### 🔓 Credenciales Socrata (SENSIBLE ⚠️)

```env
SOCRATA_DOMAIN=www.datos.gov.co
SOCRATA_API_KEY=tu_api_key               # ⚠️ SECRETO
SOCRATA_USERNAME=correo@ejemplo.com      # ⚠️ SECRETO
SOCRATA_PASSWORD=tu_contraseña           # ⚠️ SECRETO
```

**Cómo obtener:**

1. Registrate en https://www.datos.gov.co
2. Ve a "Settings" → "Developer Settings"
3. Copia tu API Key
4. Usa ese email y tu contraseña

### 🌐 URLs Base

```env
SOCRATA_BASE_URL=https://www.datos.gov.co
SOCRATA_API_ENDPOINT=/api/views
SOCRATA_RESOURCE_ENDPOINT=/resource
```

### 📊 Datos

```env
DEFAULT_RECORDS_LIMIT=50000     # Máximo de registros a cargar
TIMEOUT_REQUEST=30              # Timeout en segundos
```

### 🔄 CORS

```env
CORS_ORIGINS=*
CORS_CREDENTIALS=true
CORS_METHODS=*
CORS_HEADERS=*
```

**Ejemplo Restrictivo (Producción):**

```env
CORS_ORIGINS=https://ejemplo.com
CORS_CREDENTIALS=true
CORS_METHODS=GET,POST,OPTIONS
CORS_HEADERS=Content-Type,Authorization
```

### 📝 Logging

```env
LOG_LEVEL=INFO
LOG_FILE=./logs/api.log
```

## Cómo Se Usan en el Código

### ✅ Forma Correcta (Con Variables de Entorno)

```python
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Acceder a las variables
socrata_domain = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
api_key = os.getenv("SOCRATA_API_KEY")
username = os.getenv("SOCRATA_USERNAME")
password = os.getenv("SOCRATA_PASSWORD")

# Usar en Socrata
from sodapy import Socrata
client = Socrata(socrata_domain, api_key, username=username, password=password)
```

### ❌ Forma Incorrecta (SIN Variables de Entorno)

```python
# NUNCA hagas esto
client = Socrata(
    "www.datos.gov.co",
    "sAmoC9S1twqLnpX9YUmmSTqgp",        # ⚠️ EXPUESTO EN GIT
    username="valen@yopmail.com",       # ⚠️ EXPUESTO EN GIT
    password="p4wHD7Y.SDGiQmP"          # ⚠️ EXPUESTO EN GIT
)
```

## Archivos Modificados

### 📝 `main.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración desde variables de entorno
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8001))
SOCRATA_DOMAIN = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
# ... más variables ...
```

### 📝 `data_quality_calculator.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

SOCRATA_DOMAIN = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
SOCRATA_API_KEY = os.getenv("SOCRATA_API_KEY", "")
SOCRATA_USERNAME = os.getenv("SOCRATA_USERNAME", "")
SOCRATA_PASSWORD = os.getenv("SOCRATA_PASSWORD", "")
```

### 📝 Archivos de Prueba

- `test_example.py` - Actualizado para usar variables de entorno
- `test_backend_consistency.py` - Actualizado para usar variables de entorno
- `Untitled-1.py` - Actualizado para usar variables de entorno

## Seguridad: Checklist

- [x] ✅ Credenciales sacadas del código fuente
- [x] ✅ `.env` agregado a `.gitignore`
- [x] ✅ `.env.example` tiene valores de ejemplo
- [x] ✅ Usar `python-dotenv` para cargar variables
- [x] ✅ Documentación completa sobre configuración
- [x] ✅ Diferentes configuraciones por ambiente soportadas

## Comandos Útiles

### Verificar que `.env` NO está en Git

```bash
git status
# Debería mostrar ".env" como ignorado (no listado)

git check-ignore .env
# Si retorna .env, significa que está correctamente ignorado
```

### Ver Variables de Entorno Cargadas

```python
import os
from dotenv import load_dotenv

load_dotenv()

for key in ["HOST", "PORT", "SOCRATA_DOMAIN", "SOCRATA_USERNAME"]:
    print(f"{key}={os.getenv(key, 'NO CONFIGURADO')}")
```

### Actualizar `.env` Después de Cambios

Si `.env.example` cambia, actualiza tu `.env`:

```bash
# Ver qué nuevas variables hay
diff -u .env.example .env

# Copiar nuevas variables del ejemplo
cat .env.example >> .env.new
```

## Ambientes Recomendados

### 🔧 Desarrollo Local

```env
HOST=localhost
PORT=8001
ENV=development
DEBUG=True
CORS_ORIGINS=*
```

### 🧪 Staging/Pruebas

```env
HOST=0.0.0.0
PORT=8001
ENV=staging
DEBUG=False
CORS_ORIGINS=https://staging.ejemplo.com
DEFAULT_RECORDS_LIMIT=10000
```

### 🚀 Producción

```env
HOST=0.0.0.0
PORT=8001
ENV=production
DEBUG=False
CORS_ORIGINS=https://ejemplo.com
DEFAULT_RECORDS_LIMIT=5000
TIMEOUT_REQUEST=60
LOG_LEVEL=WARNING
```

## Troubleshooting

### 🔴 Problema: "Variable de entorno no encontrada"

**Solución:**

```python
import os
from dotenv import load_dotenv

# Asegúrate de llamar a load_dotenv() ANTES de acceder a variables
load_dotenv()

valor = os.getenv("MI_VARIABLE")
```

### 🔴 Problema: ".env" se cometió accidentalmente a Git

**Solución:**

```bash
# Eliminar del historio de Git (pero mantener localmente)
git rm --cached .env
git commit -m "Remove .env from tracking"

# O regenerar credenciales si fue comprometido
# 1. Cambiar credenciales en datos.gov.co
# 2. Actualizar .env
# 3. Hacer push
```

### 🔴 Problema: Variables no se cargan en Docker

**Solución:** En Docker, usar:

```dockerfile
# Dockerfile
ENV HOST=0.0.0.0
ENV PORT=8001
# O pasar variables al ejecutar
docker run -e HOST=0.0.0.0 -e PORT=8001 ...
```

## Referencias

- 📖 [python-dotenv Documentation](https://python-dotenv.readthedocs.io/)
- 🔐 [OWASP: Secrets Management](https://owasp.org/www-community/attacks/Sensitive_Data_Exposure)
- 🐳 [12 Factor App: Store config in environment](https://12factor.net/config)

---

**Última actualización:** 2025-11-30  
**Status:** ✅ Implementado  
**Responsable:** Sistema Automático de Calidad
