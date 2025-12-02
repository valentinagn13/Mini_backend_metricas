from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
import uvicorn
import requests
from sodapy import Socrata
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

from data_quality_calculator import DataQualityCalculator

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ═══════════════════════════════════════════════════════════════════════════
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8001))
ENV = os.getenv("ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Socrata Configuration
SOCRATA_DOMAIN = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
SOCRATA_API_KEY = os.getenv("SOCRATA_API_KEY", "")
SOCRATA_USERNAME = os.getenv("SOCRATA_USERNAME", "")
SOCRATA_PASSWORD = os.getenv("SOCRATA_PASSWORD", "")

# URLs
SOCRATA_BASE_URL = os.getenv("SOCRATA_BASE_URL", "https://www.datos.gov.co")
SOCRATA_API_ENDPOINT = os.getenv("SOCRATA_API_ENDPOINT", "/api/views")
SOCRATA_RESOURCE_ENDPOINT = os.getenv("SOCRATA_RESOURCE_ENDPOINT", "/resource")

# Data Configuration
DEFAULT_RECORDS_LIMIT = int(os.getenv("DEFAULT_RECORDS_LIMIT", 50000))
TIMEOUT_REQUEST = int(os.getenv("TIMEOUT_REQUEST", 30))

# CORS Configuration
# Por seguridad configurable vía variables de entorno. Por defecto permitir sólo el dominio
# de producción `https://datacensus.site` en lugar de `*`.
_raw_origins = os.getenv("CORS_ORIGINS", "https://datacensus.site")
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"

# Métodos y headers aceptan wildcard `*` o lista separada por comas
_raw_methods = os.getenv("CORS_METHODS", "*")
CORS_METHODS = [m.strip() for m in _raw_methods.split(",") if m.strip()] if _raw_methods != "*" else ["*"]
_raw_headers = os.getenv("CORS_HEADERS", "*")
CORS_HEADERS = [h.strip() for h in _raw_headers.split(",") if h.strip()] if _raw_headers != "*" else ["*"]

app = FastAPI(title="Data Quality Assessment API")

# Normalize CORS settings for CORSMiddleware
# Si el origen contiene '*' y se requieren credenciales, usamos una regex
# para permitir cualquier origin (incluye preflight OPTIONS) sin usar el wildcard
# literal en allow_origins (que impide allow_credentials=True).
_allow_origin_regex = None
if len(CORS_ORIGINS) == 1 and CORS_ORIGINS[0] == "*":
    if CORS_CREDENTIALS:
        _allow_origins = []
        _allow_origin_regex = r".*"
    else:
        _allow_origins = ["*"]
else:
    _allow_origins = CORS_ORIGINS

# Métodos y headers finales (aceptan '*' como wildcard)
_allow_methods = CORS_METHODS if not (len(CORS_METHODS) == 1 and CORS_METHODS[0] == "*") else ["*"]
_allow_headers = CORS_HEADERS if not (len(CORS_HEADERS) == 1 and CORS_HEADERS[0] == "*") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=_allow_methods,
    allow_headers=_allow_headers,
)


# Fallback global handler for CORS preflight OPTIONS requests.
# Devuelve 200 para cualquier ruta OPTIONS para que proxys/routers
# que bloqueen OPTIONS no impidan que el navegador reciba una respuesta
# válida de preflight. `CORSMiddleware` seguirá añadiendo las cabeceras CORS.
@app.options("/{full_path:path}")
async def _preflight_handler(full_path: str):
    """Fallback handler for CORS preflight requests.

    This returns 200 for any OPTIONS request so that browsers receive a
    successful preflight response even if the router or a proxy blocks
    OPTIONS. CORSMiddleware will still add the appropriate CORS headers.
    """
    return Response(status_code=200)

calculator = None

class DatasetRequest(BaseModel):
    dataset_id: str
    # Si es True, se cargan todos los datos en la inicialización (por defecto False)
    load_full: Optional[bool] = False

class ScoreResponse(BaseModel):
    score: float
    details: Optional[Dict] = None

class DatasetInfoResponse(BaseModel):
    message: str
    dataset_id: str
    dataset_name: str
    rows: int
    columns: int
    data_url: str
    metadata_obtained: bool
    records_count: int
    total_records_available: int
    limit_reached: bool

def obtener_metadatos_socrata(dataset_id: str) -> Dict:
    """Obtiene metadatos desde la API de Socrata"""
    metadata_url = f"{SOCRATA_BASE_URL}{SOCRATA_API_ENDPOINT}/{dataset_id}"
    print(f"🔍 Obteniendo metadatos desde: {metadata_url}")
    
    try:
        response = requests.get(metadata_url, timeout=TIMEOUT_REQUEST)
        if response.status_code == 200:
            metadata = response.json()
            print("✅ Metadatos obtenidos exitosamente")
            return metadata
        else:
            print(f"❌ Error obteniendo metadatos: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Excepción al obtener metadatos: {e}")
        return {}

def obtener_todos_los_datos_socrata(dataset_id: str, limit: int = None) -> pd.DataFrame:
    """Obtiene todos los datos del dataset usando paginación"""
    if limit is None:
        limit = DEFAULT_RECORDS_LIMIT
    
    # Use sodapy Socrata client for faster and robust retrieval
    print(f"🔗 Obteniendo datos (sodapy) para dataset: {dataset_id}")
    print(f"📦 Límite configurado: {limit} registros")
    try:
        # Credentials from environment variables
        client = Socrata(
            SOCRATA_DOMAIN,
            SOCRATA_API_KEY,
            username=SOCRATA_USERNAME,
            password=SOCRATA_PASSWORD,
        )

        results = client.get(dataset_id, limit=limit)
        print(f"🎯 Registros obtenidos (sodapy): {len(results)}")
        if results:
            df = pd.DataFrame.from_records(results)
            print(f"📊 DataFrame creado: {len(df)} filas, {len(df.columns)} columnas")
            return df
        else:
            print("⚠️ No se obtuvieron datos")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error obteniendo datos con sodapy: {e}")
        return pd.DataFrame()



# La clase DataQualityCalculator se importa desde data_quality_calculator.py (línea 12)

@app.post("/initialize")
async def initialize_dataset(request: DatasetRequest) -> DatasetInfoResponse:
    """Inicializa el dataset obteniendo metadatos.

    Por defecto NO descarga todos los datos (evita llamar a `obtener_todos_los_datos_socrata`).
    Si `load_full` en la petición es True, entonces se cargan los datos completos.
    """
    global calculator
    try:
        dataset_id = request.dataset_id
        print(f"🚀 Inicializando dataset con ID: {dataset_id}")

        # Obtener metadatos desde Socrata
        metadata = obtener_metadatos_socrata(dataset_id)
        print("🗂️ Metadatos obtenidos:")
        try:
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(metadata)
        # Inicializar el calculador con metadata (sin cargar datos por defecto)
        calculator = DataQualityCalculator(dataset_id, metadata)

        rows = 0
        columns = 0
        records_count = 0
        limit_reached = False

        # Si el cliente solicitó carga completa, la ejecutamos
        if request.load_full:
            await calculator.load_data()
            rows = len(calculator.df)
            columns = len(calculator.df.columns)
            records_count = rows
            limit_reached = rows >= 50000
            print(f"📊 Dataset cargado completamente:")
            print(f"   - Filas: {rows}")
            print(f"   - Columnas: {columns}")
        else:
            # Intentar inferir columnas desde metadatos sin descargar datos
            meta_columns = metadata.get('columns') or metadata.get('column_names') or []
            if isinstance(meta_columns, list):
                columns = len(meta_columns)
            else:
                columns = 0

            print("ℹ️ Inicialización con metadatos completada (sin cargar datos). Call /load_data to fetch full rows.")

        return DatasetInfoResponse(
            message="Dataset initialized successfully",
            dataset_id=dataset_id,
            dataset_name=metadata.get('name', 'Desconocido'),
            rows=rows,
            columns=columns,
            data_url=f"{SOCRATA_BASE_URL}{SOCRATA_RESOURCE_ENDPOINT}/{dataset_id}.json",
            metadata_obtained=bool(metadata),
            records_count=records_count,
            total_records_available=records_count,
            limit_reached=limit_reached
        )
    except Exception as e:
        print(f"❌ Error inicializando dataset: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/load_data")
async def load_full_data() -> DatasetInfoResponse:
    """Carga los datos completos del dataset para el `calculator` ya inicializado."""
    global calculator
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")
    try:
        await calculator.load_data()
        rows = len(calculator.df)
        columns = len(calculator.df.columns)
        limit_reached = rows >= DEFAULT_RECORDS_LIMIT
        return DatasetInfoResponse(
            message="Full data loaded successfully",
            dataset_id=calculator.dataset_id,
            dataset_name=calculator.metadata.get('name', 'Desconocido'),
            rows=rows,
            columns=columns,
            data_url=f"{SOCRATA_BASE_URL}{SOCRATA_RESOURCE_ENDPOINT}/{calculator.dataset_id}.json",
            metadata_obtained=bool(calculator.metadata),
            records_count=rows,
            total_records_available=rows,
            limit_reached=limit_reached
        )
    except Exception as e:
        print(f"❌ Error cargando datos completos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/actualidad")
async def get_actualidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de actualidad para un dataset específico.
    
    Parámetros:
        dataset_id: ID del dataset (debe coincidir con el inicializado)
    
    Validación:
        - Dataset debe estar inicializado
        - dataset_id debe coincidir con el dataset actual
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")

    # Backwards-compatible behavior: if dataset_id not provided in query,
    # use the already-initialized calculator.dataset_id. This avoids 422 errors
    # for clients that previously called GET /actualidad without query params.
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )
    
    try:
        print(f"📊 Calculando actualidad para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)
        score = calculator.calculate_actualidad(calculator.metadata, verbose=False)
        print(f"📈 Métrica de Actualidad calculada: {score}")
        return ScoreResponse(score=round(score, 2))
    except Exception as e:
        print(f"❌ Error calculando actualidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confidencialidad")
async def get_confidencialidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de confidencialidad usando sólo metadatos (columns[]).

    Query params:
        dataset_id (string, recomendado): debe coincidir con el dataset inicializado.
        Si se omite, se usa el dataset inicializado (fallback por compatibilidad).
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")

    # Compatibilidad: si no se pasa dataset_id, usar el inicializado
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )

    try:
        print(f"📊 Calculando confidencialidad (metadata-only) para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)
        
        # Llamar a la función que usa metadata (verbose=False para evitar duplicar impresión de metadata)
        score = calculator.calculate_confidencialidad_from_metadata(calculator.metadata, verbose=False)

        # Para retornar detalles, reconstruimos la lista de columnas sensibles (misma lógica que la función)
        columns_meta = calculator.metadata.get('columns') or []
        sensitive_columns = []
        total_columns = len(columns_meta)

        # mismos patrones que en el calculador (niveles y pesos)
        high_kw = [
            'documento', 'documento de identidad', 'pasaporte', 'cuenta bancaria', 'cuenta', 'banco',
            'tarjeta', 'historial', 'historial medico', 'historial médico', 'diagnostico', 'diagnóstico',
            'password', 'contraseña', 'cedula', 'cédula', 'dni'
        ]
        medium_kw = ['direccion', 'dirección', 'telefono', 'teléfono', 'celular', 'correo', 'email', 'mail']
        low_kw = ['fecha de nacimiento', 'nacimiento', 'sexo', 'edad', 'nombre', 'apellido']

        for col in columns_meta:
            if isinstance(col, dict):
                name = str(col.get('name') or col.get('fieldName') or '')
                desc = str(col.get('description') or col.get('comment') or '')
            else:
                name = str(col)
                desc = ''

            combined = f"{name} {desc}".lower()
            found = False
            for kw in high_kw:
                if kw in combined:
                    sensitive_columns.append({'name': name, 'level': 'alto', 'weight': 3, 'keyword': kw})
                    found = True
                    break
            if found:
                continue
            for kw in medium_kw:
                if kw in combined:
                    sensitive_columns.append({'name': name, 'level': 'medio', 'weight': 2, 'keyword': kw})
                    found = True
                    break
            if found:
                continue
            for kw in low_kw:
                if kw in combined:
                    sensitive_columns.append({'name': name, 'level': 'bajo', 'weight': 1, 'keyword': kw})
                    found = True
                    break

        N_conf = len(sensitive_columns)
        riesgo_total = sum(c['weight'] for c in sensitive_columns)
        propConf = (N_conf / total_columns) if total_columns > 0 else 0.0

        # print(f"\n📋 DETALLE DE COLUMNAS SENSIBLES DETECTADAS:")
        if N_conf > 0:
            for sc in sensitive_columns:
                print(f"  ✓ '{sc['name']}': nivel={sc['level']}, peso={sc['weight']}, keyword='{sc['keyword']}'")
        else:
            print("  - Ninguna columna sensible detectada")
        
        # print(f"\n📊 PARÁMETROS CALCULADOS:")
        # print(f"  Total columnas: {total_columns}")
        # print(f"  Columnas sensibles (N_conf): {N_conf}")
        # print(f"  Proporción sensible (propConf): {propConf:.4f}")
        # print(f"  Riesgo total: {riesgo_total}")
        # print(f"  Score final: {round(float(score), 2)}")

        details = {
            'total_columns': total_columns,
            'sensitive_columns': sensitive_columns,
            'N_conf': N_conf,
            'propConf': propConf,
            'riesgo_total': riesgo_total
        }

        return ScoreResponse(score=round(float(score), 2), details=details)
    except Exception as e:
        print(f"❌ Error calculando confidencialidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/accesibilidad")
async def get_accesibilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Accesibilidad usando SOLO metadata.

    Parámetros:
        dataset_id: ID del dataset (debe coincidir con el inicializado)

    Retorna:
        ScoreResponse(score=float, details=dict)
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")

    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )

    try:
        print(f"📊 Calculando accesibilidad (metadata-only) para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)

        score = calculator.calculate_accesibilidad_from_metadata(calculator.metadata, verbose=False)

        # Reconstruir detalles basados en la misma lógica
        tags = calculator.metadata.get('tags') or []
        links = [
            calculator.metadata.get('attributionLink'),
            calculator.metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Documentación'),
            calculator.metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Normativa')
        ]
        links_found = [l for l in links if l]

        details = {
            'accesibilidad': float(score),
            'puntaje_tags': 5.0 if len(tags) > 0 else 0.0,
            'puntaje_link': 5.0 if len(links_found) > 0 else 0.0,
            'tags_count': len(tags),
            'links_found': links_found
        }

        if len(tags) > 0:
            print(f"  ✓ tags_count: {len(tags)}")
        else:
            print("  - No se encontraron tags")
        if links_found:
            print(f"  ✓ links encontrados: {links_found}")
        else:
            print("  - No se encontraron links relevantes")

        return ScoreResponse(score=round(float(score), 2), details=details)
    except Exception as e:
        print(f"❌ Error calculando accesibilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/completitud")
async def get_completitud(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Completitud del dataset.
    
    REQUIERE que los datos estén cargados via POST /load_data.
    
    Parámetros:
        dataset_id: ID del dataset (debe coincidir con el inicializado)
    
    Validación:
        - Dataset debe estar inicializado
        - Datos deben estar cargados (call /load_data primero)
        - dataset_id debe coincidir con el dataset actual
    
    Retorna:
        score: float entre 0-10 (10 = dataset completamente completo)
        details: objeto con detalles del cálculo (filas, columnas, nulos, etc.)
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")
    
    # Backwards-compatible behavior: if dataset_id not provided, use initialized dataset_id
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )
    
    # Validar que los datos estén cargados
    if calculator.df is None or len(calculator.df) == 0:
        raise HTTPException(
            status_code=400,
            detail="Full data not loaded. Call POST /load_data first to fetch dataset records."
        )
    
    try:
        print(f"📊 Calculando completitud para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)
        
        # Llamar a la función con verbose=False (metadata ya impresa en endpoint)
        score = calculator.calculate_completitud(calculator.metadata, verbose=False)
        
        # Imprimir detalles solo en la consola (no en la respuesta)
        total_filas = len(calculator.df)
        total_columnas_actuales = len(calculator.df.columns)
        total_celdas = total_filas * total_columnas_actuales
        total_nulos = int(calculator.df.isna().sum().sum())
        proporcion_nulos = total_nulos / total_celdas if total_celdas > 0 else 0
        
        columnas_metadata = calculator.metadata.get('columns') or []
        total_columnas_metadata = len(columnas_metadata)
        
        # Identificar columnas con alto % de nulos (umbral 50%)
        umbral_nulos = 0.50
        num_col_porciento_nulos = 0
        for col in calculator.df.columns:
            nulos_col = calculator.df[col].isna().sum()
            porciento_nulos = (nulos_col / total_filas) if total_filas > 0 else 0
            if porciento_nulos > umbral_nulos:
                num_col_porciento_nulos += 1
        
        # Imprimir detalles SOLO en consola
        print(f"\n📋 DETALLES DE COMPLETITUD:")
        print(f"  ✓ Total de registros analizados: {total_filas}")
        print(f"  Columnas cargadas: {total_columnas_actuales}")
        print(f"  Columnas en metadata: {total_columnas_metadata}")
        print(f"  Celdas totales: {total_celdas}")
        print(f"  Celdas nulas: {total_nulos} ({proporcion_nulos*100:.2f}%)")
        print(f"  Columnas con >50% nulos: {num_col_porciento_nulos}")
        print(f"  Score final: {round(float(score), 2)}")
        
        # Retornar solo score (sin details, como /actualidad)
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando completitud: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conformidad")
async def get_conformidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Conformidad mejorada usando metadata y datos.

    Reglas:
    - Si NO se detectan columnas relevantes (departamento, municipio, año, latitud, longitud, correo): Score = 10.0
    - Si se detectan columnas pero no hay datos cargados: Intenta cargar una muestra (5000 registros)
    - Si hay columnas y datos: Valida valores según reglas y retorna score basado en proporción de errores
    
    Score:
    - 10.0: Sin columnas para validar (máximo) o datos completamente válidos
    - 0.0: Todos los datos son inválidos (mínimo)
    """
    metadata_to_use = None

    # Determine metadata source
    if dataset_id is None:
        if calculator is None:
            raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first or provide dataset_id")
        dataset_id = calculator.dataset_id
        metadata_to_use = calculator.metadata
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator is not None and calculator.dataset_id == dataset_id:
            metadata_to_use = calculator.metadata
        else:
            print(f"ℹ️ Obteniendo metadatos en línea para dataset_id={dataset_id}")
            fetched = obtener_metadatos_socrata(dataset_id)
            if not fetched:
                raise HTTPException(status_code=404, detail=f"Metadata not found for dataset_id={dataset_id}")
            metadata_to_use = fetched

    try:
        print(f"📊 Calculando conformidad para dataset: {dataset_id}")

        # Use existing calculator if matches and has data, otherwise create temporary
        use_calc = None
        if calculator is not None and calculator.dataset_id == dataset_id:
            use_calc = calculator
        else:
            use_calc = DataQualityCalculator(dataset_id, metadata_to_use)

        # Detect relevant columns; if there are and no data loaded, try to load a sample
        detected = use_calc._detect_relevant_columns(metadata_to_use)
        any_found = any(len(v) > 0 for v in detected.values())

        if any_found and (getattr(use_calc, 'df', None) is None or len(use_calc.df) == 0):
            print("ℹ️ Columnas relevantes detectadas y no hay datos cargados -> intentando cargar muestra (5000)")
            try:
                await use_calc.load_data(limit=5000)
            except Exception as e:
                print(f"⚠️ No se pudieron cargar datos para validación: {e}")

        score = use_calc.calculate_conformidad_from_metadata_and_data(metadata_to_use, verbose=True)

        # Build details from cache if available
        cached = getattr(use_calc, 'cached_scores', {}).get('conformidad_advanced')
        details = cached['details'] if cached else None

        return ScoreResponse(score=round(float(score), 2), details=details)
    except Exception as e:
        print(f"❌ Error calculando conformidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portabilidad")
async def get_portabilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Portabilidad del dataset.
    
    Portabilidad mide si el recurso se puede descargar y usar sin depender de 
    software propietario, sin macros, contraseñas ni bloqueos.
    
    Análisis realizado:
    - Clasifica formatos disponibles (muy portable, mediano, no portable)
    - Evalúa la reutilizabilidad de los datos
    - Considera metadatos sobre medios de conservación
    - Aplica pesos según portabilidad de cada formato
    
    REQUIERE que los datos estén cargados via POST /load_data.
    
    Parámetros:
        dataset_id: ID del dataset (debe coincidir con el inicializado)
    
    Validación:
        - Dataset debe estar inicializado
        - Datos deben estar cargados (call /load_data primero)
        - dataset_id debe coincidir con el dataset actual
    
    Retorna:
        score: float entre 0-10 (10 = dataset completamente portable)
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")
    
    # Backwards-compatible behavior: if dataset_id not provided, use initialized dataset_id
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )
    
    # Validar que los datos estén cargados
    if calculator.df is None or len(calculator.df) == 0:
        raise HTTPException(
            status_code=400,
            detail="Full data not loaded. Call POST /load_data first to fetch dataset records."
        )
    
    try:
        print(f"📊 Calculando portabilidad para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)
        
        # Llamar a la función
        score = calculator.calculate_portabilidad()
        
        print(f"📈 Métrica de Portabilidad calculada: {score}")
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando portabilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/disponibilidad")
async def get_disponibilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Disponibilidad del dataset.
    
    Disponibilidad mide la capacidad del dataset de estar **siempre listo y accesible**
    para su uso. Se calcula como el promedio simple de Accesibilidad y Actualidad.
    
    Fórmula:
    disponibilidad = (accesibilidad + actualidad) / 2
    
    Escala de interpretación:
    - 10: Datos siempre listos y accesibles (máximo)
    - 7-9: Dataset generalmente disponible (bueno)
    - 5-6: Disponibilidad parcial (aceptable)
    - 3-4: Disponibilidad limitada (deficiente)
    - 0-2: Datos prácticamente no disponibles (crítico)
    
    Componentes:
    - **Accesibilidad**: ¿Qué tan fácil es acceder al dataset? (basada en tags y links)
    - **Actualidad**: ¿Qué tan reciente es la información? (basada en fecha de actualización)
    
    Parámetros:
        dataset_id: ID del dataset (opcional, usa inicializado si se omite)
    
    Retorna:
        score: float entre 0-10 (10 = dataset siempre disponible)
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")
    
    # Backwards-compatible behavior: if dataset_id not provided, use initialized dataset_id
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )
    
    try:
        print(f"📊 Calculando disponibilidad para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)
        
        # Llamar a la función
        score = calculator.calculate_disponibilidad()
        
        print(f"📈 Métrica de Disponibilidad calculada: {score}")
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trazabilidad")
async def get_trazabilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Trazabilidad del dataset (usa metadatos).

    REQUIERE metadatos. Si el `calculator` inicializado coincide con el
    `dataset_id`, se usa; si no, se obtienen metadatos on-demand.
    """
    metadata_to_use = None

    if dataset_id is None:
        if calculator is None:
            raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first or provide dataset_id")
        dataset_id = calculator.dataset_id
        metadata_to_use = calculator.metadata
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator is not None and calculator.dataset_id == dataset_id:
            metadata_to_use = calculator.metadata
        else:
            print(f"ℹ️ Obteniendo metadatos en línea para dataset_id={dataset_id}")
            fetched = obtener_metadatos_socrata(dataset_id)
            if not fetched:
                raise HTTPException(status_code=404, detail=f"Metadata not found for dataset_id={dataset_id}")
            metadata_to_use = fetched

    try:
        print(f"📊 Calculando trazabilidad para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(metadata_to_use, indent=2, ensure_ascii=False))
        except Exception:
            print(metadata_to_use)

        # Usar calculator existente si coincide, sino crear temporal
        if calculator is not None and calculator.dataset_id == dataset_id:
            score = calculator.calculate_trazabilidad(metadata_to_use)
        else:
            temp_calc = DataQualityCalculator(dataset_id, metadata_to_use)
            score = temp_calc.calculate_trazabilidad(metadata_to_use)

        print(f"📈 Métrica de Trazabilidad calculada: {score}")
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando trazabilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recuperabilidad")
async def get_recuperabilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Recuperabilidad del dataset según la Guía de Calidad v7/v8.
    
    Fórmula: recuperabilidad = (accesibilidad + medidaMetadatosCompletos + metadatosAuditados) / 3
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")

    # Backwards-compatible behavior
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )

    # Validar que los datos estén cargados
    if calculator.df is None or len(calculator.df) == 0:
        raise HTTPException(
            status_code=400,
            detail="Full data not loaded. Call POST /load_data first to fetch dataset records."
        )

    try:
        print(f"📊 Calculando recuperabilidad para dataset: {dataset_id}")
        
        # 1. Obtener accesibilidad usando el método existente
        accesibilidad_score = calculator.calculate_accesibilidad_from_metadata(verbose=False)
        # Normalizar a escala 0-1 (tu método retorna 0-10)
        accesibilidad_normalized = accesibilidad_score / 10.0
        print(f"  - Accesibilidad: {accesibilidad_score}/10 → {accesibilidad_normalized:.2f}")
        
        # 2. Calcular medidaMetadatosCompletos
        metadatos_completos_score = calculator.calculate_metadatos_completos()
        print(f"  - Metadatos Completos: {metadatos_completos_score:.2f}")
        
        # 3. Calcular metadatosAuditados
        metadatos_auditados_score = calculator.calculate_metadatos_auditados()
        print(f"  - Metadatos Auditados: {metadatos_auditados_score:.2f}")
        
        # 4. Calcular recuperabilidad según fórmula (todas en escala 0-1)
        recuperabilidad_score = (
            accesibilidad_normalized + 
            metadatos_completos_score + 
            metadatos_auditados_score
        ) / 3.0
        
        # Convertir a escala 0-10 para consistencia con otras métricas
        recuperabilidad_final = recuperabilidad_score * 10.0
        
        print(f"📈 Métrica de Recuperabilidad calculada: {recuperabilidad_final:.2f}/10")
        
        return ScoreResponse(
            score=round(float(recuperabilidad_final), 2),
            details={
                "componentes": {
                    "accesibilidad": round(float(accesibilidad_score), 2),
                    "accesibilidad_normalized": round(float(accesibilidad_normalized), 2),
                    "metadatos_completos": round(float(metadatos_completos_score), 2),
                    "metadatos_auditados": round(float(metadatos_auditados_score), 2)
                },
                "formula": "recuperabilidad = (accesibilidad + metadatos_completos + metadatos_auditados) / 3",
                "escala": "0-10"
            }
        )
    except Exception as e:
        print(f"❌ Error calculando recuperabilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credibilidad")
async def get_credibilidad(dataset_id: Optional[str] = None) -> ScoreResponse:
    """Calcula la métrica de Credibilidad del dataset.

    REQUIERE que los datos estén cargados via POST /load_data.
    """
    if calculator is None:
        raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first.")

    # Backwards-compatible behavior: if dataset_id not provided, use initialized dataset_id
    if dataset_id is None:
        dataset_id = calculator.dataset_id
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        if calculator.dataset_id != dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset mismatch. Initialized: {calculator.dataset_id}, Requested: {dataset_id}"
            )

    # Validar que los datos estén cargados
    if calculator.df is None or len(calculator.df) == 0:
        raise HTTPException(
            status_code=400,
            detail="Full data not loaded. Call POST /load_data first to fetch dataset records."
        )

    try:
        print(f"📊 Calculando credibilidad para dataset: {dataset_id}")
        print("🛈 Metadata usada:")
        try:
            print(json.dumps(calculator.metadata, indent=2, ensure_ascii=False))
        except Exception:
            print(calculator.metadata)

        # Llamar a la función
        score = calculator.calculate_credibilidad()

        print(f"📈 Métrica de Credibilidad calculada: {score}")
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando credibilidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/unicidad")
async def get_unicidad(dataset_id: Optional[str] = None, nivel_riesgo: Optional[float] = 1.5) -> ScoreResponse:
    """Calcula la métrica de Unicidad del dataset (duplicados).
    
    Detecta:
    - Filas duplicadas: Filas con exactamente los mismos valores en todas las columnas
    - Columnas duplicadas: Columnas con exactamente los mismos valores en todas las filas
    
    REQUIERE que los datos estén cargados via POST /load_data.
    
    Parámetros:
        dataset_id: ID del dataset (debe coincidir con el inicializado)
        nivel_riesgo: Parámetro para ajustar penalización (default=1.5)
            - 1.0: Penalización suave
            - 1.5: Penalización media (RECOMENDADO)
            - 2.0: Penalización estricta (para datos críticos)
    
    Validación:
        - Dataset debe estar inicializado
        - Datos deben estar cargados (call /load_data primero)
        - dataset_id debe coincidir con el dataset actual
    
    Retorna:
        score: float entre 0-10 (10 = sin duplicados, 0 = muchos duplicados)
    """
    metadata_to_use = None

    # Determine metadata source
    if dataset_id is None:
        # No dataset_id provided: require initialized calculator
        if calculator is None:
            raise HTTPException(status_code=400, detail="Dataset not initialized. Call /initialize first or provide dataset_id")
        dataset_id = calculator.dataset_id
        metadata_to_use = calculator.metadata
        print("⚠️ Warning: dataset_id not provided in request; using initialized dataset_id")
    else:
        # If calculator exists and matches, use its metadata
        if calculator is not None and calculator.dataset_id == dataset_id:
            metadata_to_use = calculator.metadata
        else:
            # Try to fetch metadata on-demand for the provided dataset_id
            print(f"ℹ️ Obteniendo metadatos en línea para dataset_id={dataset_id}")
            fetched = obtener_metadatos_socrata(dataset_id)
            if not fetched:
                raise HTTPException(status_code=404, detail=f"Metadata not found for dataset_id={dataset_id}")
            metadata_to_use = fetched

    try:
        print(f"📊 Calculando unicidad para dataset: {dataset_id}")
        print(f"   Nivel de riesgo: {nivel_riesgo}")

        # If we have an initialized calculator with data for this dataset, use it; otherwise
        # create a temporary calculator that only holds metadata (note: unicidad needs data,
        # so the temp calculator will return a neutral value if no data is present).
        if calculator is not None and calculator.dataset_id == dataset_id and getattr(calculator, 'df', None) is not None and len(calculator.df) > 0:
            score = calculator.calculate_unicidad(nivel_riesgo=nivel_riesgo)
        else:
            temp_calc = DataQualityCalculator(dataset_id, metadata_to_use)
            score = temp_calc.calculate_unicidad(nivel_riesgo=nivel_riesgo)

        print(f"📈 Métrica de Unicidad calculada: {score}")
        return ScoreResponse(score=round(float(score), 2))
    except Exception as e:
        print(f"❌ Error calculando unicidad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Data Quality Assessment API", 
        "status": "running",
        "version": "1.0",
        "features": ["pagination", "full_dataset_loading"]
    }

if __name__ == "__main__":
    print(f"🌐 Iniciando servidor Data Quality API en {HOST}:{PORT}...")
    print(f"🔧 Ambiente: {ENV}")
    print(f"🐛 Debug: {DEBUG}")
    print("📚 Características: Paginación habilitada para datasets grandes")
    uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)
  