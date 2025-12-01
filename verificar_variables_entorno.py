#!/usr/bin/env python3
"""
Script de diagnóstico para verificar variables de entorno
Valida que todas las variables estén configuradas correctamente
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("❌ ERROR: python-dotenv no está instalado")
    print("Instálalo con: pip install python-dotenv")
    sys.exit(1)

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def check_variable(name, sensitive=False, required=False):
    """Verifica si una variable de entorno está configurada"""
    value = os.getenv(name)
    
    if value is None:
        if required:
            print(f"  ❌ {name}: NO CONFIGURADA (⚠️  REQUERIDA)")
            return False
        else:
            print(f"  ⚠️  {name}: NO CONFIGURADA (usando default)")
            return True
    else:
        if sensitive:
            # Mostrar solo primeros y últimos caracteres
            if len(value) > 10:
                masked = value[:4] + "..." + value[-4:]
            else:
                masked = "***"
            print(f"  ✅ {name}: {masked} (configurada)")
        else:
            print(f"  ✅ {name}: {value}")
        return True

def main():
    print(f"\n{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════{Colors.END}")
    print(f"{Colors.BOLD}  🔐 VERIFICACIÓN DE VARIABLES DE ENTORNO{Colors.END}")
    print(f"{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════{Colors.END}\n")
    
    # Verificar .env
    env_path = Path(".env")
    if env_path.exists():
        print(f"✅ Archivo .env encontrado en: {env_path.absolute()}\n")
    else:
        print(f"⚠️  Archivo .env NO encontrado en: {env_path.absolute()}")
        print(f"   Copia .env.example como .env y edítalo con tus credenciales\n")
    
    # Verificar variables
    all_good = True
    
    print(f"{Colors.BOLD}🖥️  CONFIGURACIÓN DEL SERVIDOR:{Colors.END}")
    check_variable("HOST")
    check_variable("PORT")
    check_variable("ENV")
    check_variable("DEBUG")
    
    print(f"\n{Colors.BOLD}🔐 CREDENCIALES SOCRATA (SENSIBLES):{Colors.END}")
    all_good &= check_variable("SOCRATA_DOMAIN", required=True)
    all_good &= check_variable("SOCRATA_API_KEY", sensitive=True, required=True)
    all_good &= check_variable("SOCRATA_USERNAME", sensitive=True, required=True)
    all_good &= check_variable("SOCRATA_PASSWORD", sensitive=True, required=True)
    
    print(f"\n{Colors.BOLD}🌐 URLs:{Colors.END}")
    check_variable("SOCRATA_BASE_URL")
    check_variable("SOCRATA_API_ENDPOINT")
    check_variable("SOCRATA_RESOURCE_ENDPOINT")
    
    print(f"\n{Colors.BOLD}📊 DATOS:{Colors.END}")
    check_variable("DEFAULT_RECORDS_LIMIT")
    check_variable("TIMEOUT_REQUEST")
    
    print(f"\n{Colors.BOLD}🔄 CORS:{Colors.END}")
    check_variable("CORS_ORIGINS")
    check_variable("CORS_CREDENTIALS")
    check_variable("CORS_METHODS")
    check_variable("CORS_HEADERS")
    
    print(f"\n{Colors.BOLD}📝 LOGGING:{Colors.END}")
    check_variable("LOG_LEVEL")
    check_variable("LOG_FILE")
    
    # Resultado final
    print(f"\n{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════{Colors.END}")
    
    if all_good:
        print(f"{Colors.OK}{Colors.BOLD}✅ TODAS LAS VARIABLES REQUERIDAS ESTÁN CONFIGURADAS{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}❌ FALTAN VARIABLES REQUERIDAS{Colors.END}")
        print(f"\nAcciones necesarias:")
        print(f"  1. Edita el archivo .env con tus credenciales reales")
        print(f"  2. Ejecuta este script nuevamente para verificar")
        print(f"  3. Si todo está bien, inicia el servidor: python main.py\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
