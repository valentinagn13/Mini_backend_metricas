# Guía de Deployment - Data Quality Assessment Backend

## ✅ Pre-Deployment Checklist

### 1. Verificación de Código
- [ ] Todos los tests pasan: `pytest tests/`
- [ ] Sin errores de sintaxis: `python -m py_compile *.py`
- [ ] Sin imports sin usar
- [ ] Documentación actualizada
- [ ] README.md completo

### 2. Variables de Entorno
- [ ] `.env` contiene todas las variables requeridas
- [ ] `.env` NO está versionado en git (revisar `.gitignore`)
- [ ] Credenciales Socrata están correctas
- [ ] `SOCRATA_API_KEY` es válida
- [ ] URLs base correctas

### 3. Dependencias
- [ ] `requirements.txt` actualizado: `pip freeze > requirements.txt`
- [ ] Versiones pinned (ej: `fastapi==0.104.1` no `fastapi>=0.100`)
- [ ] Modelos Spacy descargados: `python -m spacy download es_core_news_sm`

### 4. Base de Datos (si aplica)
- [ ] Listas de departamentos/municipios actualizadas
- [ ] Validadores compilados (si están en caché)

### 5. Seguridad
- [ ] DEBUG=False en producción
- [ ] CORS_ORIGINS especificado (no `*`)
- [ ] Log files en directorio escribible
- [ ] Credenciales fuera del repo

### 6. Performance
- [ ] DEFAULT_RECORDS_LIMIT apropiado para recursos
- [ ] TIMEOUT_REQUEST calibrado
- [ ] Logs no demasiado verbosos (LOG_LEVEL=INFO)

### 7. Documentación
- [ ] DOCUMENTACION_PROYECTO.md
- [ ] README.md
- [ ] GUIA_TECNICA.md
- [ ] EJEMPLOS_USO.md
- [ ] Comentarios en código crítico

---

## 🚀 Deployment en Desarrollo (Local)

### Paso 1: Clonar y configurar
```bash
# Clonar repositorio
git clone https://github.com/valentinagn13/Mini_backend_metricas.git
cd Mini_backend_metricas

# Crear entorno virtual
python -m venv .venv

# Activar entorno
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
python -m spacy download es_core_news_sm
```

### Paso 2: Configurar .env
```bash
# Copiar template
cp .env.example .env  # (si existe)

# O crear nuevo .env
cat > .env << EOF
HOST=0.0.0.0
PORT=8001
ENV=development
DEBUG=True

SOCRATA_DOMAIN=www.datos.gov.co
SOCRATA_API_KEY=YOUR_API_KEY_HERE
SOCRATA_USERNAME=YOUR_USERNAME
SOCRATA_PASSWORD=YOUR_PASSWORD

SOCRATA_BASE_URL=https://www.datos.gov.co
SOCRATA_API_ENDPOINT=/api/views
SOCRATA_RESOURCE_ENDPOINT=/resource

DEFAULT_RECORDS_LIMIT=50000
TIMEOUT_REQUEST=30

CORS_ORIGINS=*
CORS_CREDENTIALS=true
CORS_METHODS=*
CORS_HEADERS=*

LOG_LEVEL=INFO
LOG_FILE=./logs/api.log
EOF
```

### Paso 3: Crear directorio de logs
```bash
mkdir -p logs
```

### Paso 4: Iniciar servidor
```bash
python main.py

# Debe mostrar:
# 🌐 Iniciando servidor Data Quality API en 0.0.0.0:8001...
# 🔧 Ambiente: development
# 🐛 Debug: True
# INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Paso 5: Verificar que funciona
```bash
# En otra terminal
curl http://localhost:8001/

# Respuesta esperada:
# {"message":"Data Quality Assessment API","status":"running","version":"1.0",...}
```

---

## 🐳 Deployment en Docker

### Paso 1: Crear Dockerfile
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Descargar modelo Spacy
RUN python -m spacy download es_core_news_sm

# Copiar código
COPY . .

# Crear directorio de logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/')"

# Iniciar servidor
CMD ["python", "main.py"]
```

### Paso 2: Crear .dockerignore
```
.git
.gitignore
.env
.venv
__pycache__
*.pyc
.pytest_cache
.coverage
tests/
DOCUMENTOS/
README.md
```

### Paso 3: Build de imagen
```bash
docker build -t data-quality-backend:1.0 .
```

### Paso 4: Ejecutar container
```bash
docker run \
  --name quality-api \
  --env-file .env \
  -p 8001:8001 \
  -v $(pwd)/logs:/app/logs \
  data-quality-backend:1.0

# O en background
docker run -d \
  --name quality-api \
  --env-file .env \
  -p 8001:8001 \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  data-quality-backend:1.0
```

### Paso 5: Verificar
```bash
# Logs
docker logs quality-api

# Health check
docker ps | grep quality-api

# Probar
curl http://localhost:8001/
```

---

## 🏢 Deployment en Producción (Ubuntu/AWS)

### Paso 1: Provisionar servidor
```bash
# Ubuntu 22.04 LTS
# Requisitos mínimos: 2 vCPU, 4GB RAM, 10GB disk

# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  git \
  nginx \
  supervisor \
  curl \
  wget
```

### Paso 2: Clonar aplicación
```bash
# Como usuario deploy
sudo su - deploy
cd /opt

# Clonar repo
git clone https://github.com/valentinagn13/Mini_backend_metricas.git
cd Mini_backend_metricas

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
python -m spacy download es_core_news_sm
```

### Paso 3: Configurar .env (producción)
```bash
cat > .env << 'EOF'
HOST=127.0.0.1
PORT=8001
ENV=production
DEBUG=False

SOCRATA_DOMAIN=www.datos.gov.co
SOCRATA_API_KEY=YOUR_PROD_API_KEY
SOCRATA_USERNAME=YOUR_PROD_USERNAME
SOCRATA_PASSWORD=YOUR_PROD_PASSWORD

SOCRATA_BASE_URL=https://www.datos.gov.co
SOCRATA_API_ENDPOINT=/api/views
SOCRATA_RESOURCE_ENDPOINT=/resource

DEFAULT_RECORDS_LIMIT=50000
TIMEOUT_REQUEST=30

CORS_ORIGINS=https://midominio.com,https://www.midominio.com
CORS_CREDENTIALS=true
CORS_METHODS=GET,POST,OPTIONS
CORS_HEADERS=*

LOG_LEVEL=INFO
LOG_FILE=/var/log/quality-api/api.log
EOF

chmod 600 .env
```

### Paso 4: Configurar Supervisor
```bash
# Crear archivo de configuración
sudo tee /etc/supervisor/conf.d/quality-api.conf > /dev/null << EOF
[program:quality-api]
directory=/opt/Mini_backend_metricas
command=/opt/Mini_backend_metricas/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8001 \
  --access-logfile /var/log/quality-api/access.log \
  --error-logfile /var/log/quality-api/error.log \
  --log-level info
user=deploy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/quality-api/supervisor.log

[group:quality]
programs=quality-api
EOF

# Crear directorio de logs
sudo mkdir -p /var/log/quality-api
sudo chown deploy:deploy /var/log/quality-api
```

### Paso 5: Configurar Nginx (reverse proxy)
```bash
# Crear configuración
sudo tee /etc/nginx/sites-available/quality-api > /dev/null << 'EOF'
upstream quality_backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name api.midominio.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.midominio.com;

    # SSL certificates (usar Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.midominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.midominio.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/quality-api-access.log;
    error_log /var/log/nginx/quality-api-error.log;

    # Client limits
    client_max_body_size 100M;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://quality_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://quality_backend/;
        access_log off;
    }
}
EOF

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/quality-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Paso 6: SSL con Let's Encrypt
```bash
# Instalar certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot certonly --nginx -d api.midominio.com

# Renovación automática
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Paso 7: Iniciar servicios
```bash
# Recargar Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start quality-api

# Verificar estado
sudo supervisorctl status quality-api

# Ver logs
sudo tail -f /var/log/quality-api/api.log
```

### Paso 8: Verificar
```bash
# Desde local
curl https://api.midominio.com/

# Debe retornar:
# {"message":"Data Quality Assessment API","status":"running",...}
```

---

## 📊 Monitoreo en Producción

### Logs de Aplicación
```bash
# En tiempo real
sudo tail -f /var/log/quality-api/api.log

# Últimos 100 líneas
sudo tail -n 100 /var/log/quality-api/api.log

# Buscar errores
sudo grep -i error /var/log/quality-api/api.log
```

### Monitoreo de Procesos
```bash
# Ver estado del proceso
sudo supervisorctl status quality-api

# Reiniciar si es necesario
sudo supervisorctl restart quality-api

# Ver logs de Supervisor
sudo tail -f /var/log/quality-api/supervisor.log
```

### Monitoreo de Nginx
```bash
# Ver logs de acceso
sudo tail -f /var/log/nginx/quality-api-access.log

# Ver logs de error
sudo tail -f /var/log/nginx/quality-api-error.log

# Test de configuración
sudo nginx -t
```

### Métricas Útiles
```bash
# Usar herramienta simple
watch -n 1 'ps aux | grep gunicorn'

# O con herramienta más avanzada (opcional)
pip install prometheus-client

# Luego agregar en main.py:
# from prometheus_client import start_http_server
# start_http_server(8010)  # Metrics en puerto 8010
```

---

## 🔄 Actualizaciones y Rollback

### Actualizar código
```bash
cd /opt/Mini_backend_metricas
git fetch origin
git pull origin main

# Activar entorno
source venv/bin/activate

# Instalar nuevas dependencias
pip install -r requirements.txt

# Reiniciar servicio
sudo supervisorctl restart quality-api
```

### Rollback
```bash
# Ir a versión anterior
git reset --hard HEAD~1

# Reiniciar
sudo supervisorctl restart quality-api

# Verificar
curl https://api.midominio.com/
```

---

## 🆘 Troubleshooting

### API no responde
```bash
# Verificar si el proceso está corriendo
sudo supervisorctl status quality-api

# Si no está corriendo:
sudo supervisorctl start quality-api

# Ver logs
sudo tail -f /var/log/quality-api/api.log
```

### Error de conexión a Socrata
```bash
# Verificar credenciales en .env
cat /opt/Mini_backend_metricas/.env | grep SOCRATA

# Verificar conectividad
curl https://www.datos.gov.co/api/views

# Si falla: conectividad de red
ping 8.8.8.8  # Test DNS
```

### Error de memoria insuficiente
```bash
# Ver memoria disponible
free -h

# Ver consumo del proceso
ps aux | grep gunicorn

# Soluciones:
# 1. Reducir DEFAULT_RECORDS_LIMIT en .env
# 2. Aumentar workers en gunicorn (cuidado: usa más memoria)
# 3. Aumentar RAM del servidor
```

### Performance lento
```bash
# Ver logs de acceso
sudo grep "duration" /var/log/quality-api/api.log

# Optimizaciones:
# 1. Aumentar timeout TIMEOUT_REQUEST
# 2. Aumentar workers Gunicorn
# 3. Optimizar queries a Socrata
# 4. Agregar caché (Redis)
```

---

## 📈 Escalabilidad Futura

### Caché con Redis
```python
# Instalar redis
pip install redis

# Agregar a main.py
import redis
cache = redis.Redis(host='localhost', port=6379)

# Usar en endpoints
@app.get("/actualidad")
async def get_actualidad(dataset_id: str):
    cache_key = f"actualidad:{dataset_id}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    # ... calcular
```

### Load Balancing
```bash
# Nginx upstream con múltiples instancias
upstream quality_backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

# Configurar múltiples instancias en Supervisor
# [program:quality-api-1]
# [program:quality-api-2]
# [program:quality-api-3]
```

### Containerización completa (Kubernetes)
```yaml
# Futuro: agregar deployment.yaml, service.yaml, ingress.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quality-api
spec:
  replicas: 3
  # ... resto de configuración
```

---

**Versión**: 1.0  
**Última actualización**: 30 de noviembre de 2025
