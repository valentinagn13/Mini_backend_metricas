from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
import uvicorn
import requests
import json
import pandas as pd
from datetime import datetime

from data_quality_calculator import DataQualityCalculator

app = FastAPI(title="Data Quality Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    metadata_url = f"https://www.datos.gov.co/api/views/{dataset_id}"
    print(f"🔍 Obteniendo metadatos desde: {metadata_url}")
    
    try:
        response = requests.get(metadata_url)
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

def obtener_todos_los_datos_socrata(dataset_id: str, limit: int = 50000) -> pd.DataFrame:
    """Obtiene todos los datos del dataset usando paginación"""
    base_url = f"https://www.datos.gov.co/resource/{dataset_id}.json"
    
    print(f"🔗 Obteniendo datos desde: {base_url}")
    print(f"📦 Límite configurado: {limit} registros")
    
    all_data = []
    offset = 0
    page_size = 1000  # Máximo por página en Socrata
    total_obtained = 0
    
    try:
        while offset < limit:
            url = f"{base_url}?$limit={page_size}&$offset={offset}"
            print(f"📄 Solicitando página: offset={offset}, limit={page_size}")
            
            response = requests.get(url)
            if response.status_code == 200:
                page_data = response.json()
                records_in_page = len(page_data)
                all_data.extend(page_data)
                total_obtained += records_in_page
                
                print(f"✅ Página obtenida: {records_in_page} registros")
                
                # Si obtenemos menos registros que el page_size, es la última página
                if records_in_page < page_size:
                    print(f"🏁 Última página alcanzada. Total: {total_obtained} registros")
                    break
                
                offset += page_size
                
                # Pequeña pausa para no saturar la API
                import time
                time.sleep(0.1)
                
            else:
                print(f"❌ Error en página {offset}: {response.status_code}")
                break
                
        print(f"🎯 Total de registros obtenidos: {len(all_data)}")
        
        if all_data:
            df = pd.DataFrame(all_data)
            print(f"📊 DataFrame creado: {len(df)} filas, {len(df.columns)} columnas")
            return df
        else:
            print("⚠️ No se obtuvieron datos")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error obteniendo datos: {e}")
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
            data_url=f"https://www.datos.gov.co/resource/{dataset_id}.json",
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
        limit_reached = rows >= 50000
        return DatasetInfoResponse(
            message="Full data loaded successfully",
            dataset_id=calculator.dataset_id,
            dataset_name=calculator.metadata.get('name', 'Desconocido'),
            rows=rows,
            columns=columns,
            data_url=f"https://www.datos.gov.co/resource/{calculator.dataset_id}.json",
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
        print(f"📊 Calculando unicidad para dataset: {dataset_id}")
        print(f"   Nivel de riesgo: {nivel_riesgo}")
        score = calculator.calculate_unicidad(nivel_riesgo=nivel_riesgo)
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
    print("🌐 Iniciando servidor Data Quality API en puerto 8001...")
    print("📚 Características: Paginación habilitada para datasets grandes")
    uvicorn.run(app, host="0.0.0.0", port=8001)
  