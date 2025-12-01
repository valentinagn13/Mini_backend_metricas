"""
Script de Diagnóstico para Conformidad (MEJORADO)
Ayuda a identificar el estado de la métrica de conformidad
"""

import requests
import pandas as pd
import re
from typing import Dict, List

def diagnosticar_conformidad(dataset_id: str, api_base: str = "http://localhost:8001") -> Dict:
    """
    Diagnóstico completo de la métrica de conformidad
    
    Cambios en v2.0:
    - Score = 10.0 si NO hay columnas relevantes (antes: 0)
    - Listas locales de departamentos y municipios (antes: API externa)
    - Mejor manejo de errores
    """
    
    print(f"\n{'='*70}")
    print(f"🔍 DIAGNÓSTICO DE CONFORMIDAD v2.0 - Dataset: {dataset_id}")
    print(f"{'='*70}\n")
    
    resultado = {
        "dataset_id": dataset_id,
        "diagnosticos": [],
        "score_final": None,
        "razon_cero": None,
        "columnas_detectadas": {}
    }
    
    # ========== PASO 1: Inicializar dataset ==========
    print("📋 PASO 1: Inicializando dataset...")
    try:
        resp = requests.post(f"{api_base}/initialize", json={"dataset_id": dataset_id, "load_full": False})
        if resp.status_code != 200:
            resultado["razon_cero"] = "Error al inicializar dataset"
            print(f"❌ Error: {resp.status_code}")
            return resultado
        init_data = resp.json()
        print(f"✅ Dataset inicializado")
        print(f"   - Nombre: {init_data.get('dataset_name')}")
        print(f"   - Columnas detectadas: {init_data.get('columns')}")
    except Exception as e:
        resultado["razon_cero"] = f"Excepción al inicializar: {str(e)}"
        print(f"❌ Excepción: {e}")
        return resultado
    
    # ========== PASO 2: Cargar datos ==========
    print(f"\n📦 PASO 2: Cargando datos completos...")
    try:
        resp = requests.post(f"{api_base}/load_data")
        if resp.status_code != 200:
            resultado["razon_cero"] = "Error al cargar datos"
            print(f"❌ Error: {resp.status_code}")
            return resultado
        load_data = resp.json()
        rows_loaded = load_data.get('rows', 0)
        cols_loaded = load_data.get('columns', 0)
        print(f"✅ Datos cargados")
        print(f"   - Filas: {rows_loaded}")
        print(f"   - Columnas: {cols_loaded}")
        
        if rows_loaded == 0:
            resultado["razon_cero"] = "No hay filas en el dataset"
            print(f"⚠️ PROBLEMA: Dataset vacío (0 filas)")
            return resultado
            
    except Exception as e:
        resultado["razon_cero"] = f"Excepción al cargar datos: {str(e)}"
        print(f"❌ Excepción: {e}")
        return resultado
    
    # ========== PASO 3: Obtener metadatos para analizar columnas ==========
    print(f"\n🔎 PASO 3: Analizando columnas para detección...")
    
    try:
        url = f"https://www.datos.gov.co/api/views/{dataset_id}.json"
        resp = requests.get(url)
        if resp.status_code == 200:
            metadata = resp.json()
            cols_metadata = metadata.get('columns', [])
            col_names = [c.get('name', c.get('fieldName', '')) for c in cols_metadata]
        else:
            col_names = []
    except Exception as e:
        print(f"⚠️ No se pudieron obtener columnas desde metadata: {e}")
        col_names = []
    
    print(f"   Columnas encontradas: {len(col_names)}")
    if col_names:
        print(f"   - Ejemplos: {col_names[:10]}")
    
    # Detectar columnas relevantes
    patterns = {
        'departamento': ['departamento', 'depto', 'department'],
        'municipio': ['municipio', 'ciudad', 'city', 'municipality'],
        'año': ['año', 'year', 'anio', 'ano'],
        'latitud': ['latitud', 'latitude', 'lat'],
        'longitud': ['longitud', 'longitude', 'lon', 'long'],
        'correo': ['correo', 'email', 'mail']
    }
    
    detected = {k: [] for k in patterns.keys()}
    for col in col_names:
        col_lower = str(col).lower()
        for tipo, pats in patterns.items():
            for pat in pats:
                if pat in col_lower:
                    detected[tipo].append(col)
                    break
    
    resultado["columnas_detectadas"] = detected
    
    print(f"\n   📍 Columnas DETECTADAS para validación:")
    columnas_encontradas = False
    for tipo, cols in detected.items():
        if cols:
            print(f"      ✅ {tipo:15} → {cols}")
            columnas_encontradas = True
        else:
            print(f"      ❌ {tipo:15} → (no encontrado)")
    
    if not columnas_encontradas:
        print(f"\n⚠️ INFO: No se detectaron columnas relevantes")
        print(f"   → Score ESPERADO: 10.0 (conforme por defecto)")
    
    # ========== PASO 4: Calcular conformidad ==========
    print(f"\n📊 PASO 4: Calculando conformidad...")
    try:
        resp = requests.get(f"{api_base}/conformidad?dataset_id={dataset_id}")
        if resp.status_code == 200:
            conf_data = resp.json()
            score = conf_data.get('score', 0)
            resultado["score_final"] = score
            print(f"✅ Score de conformidad: {score}")
            
            # Análisis del score
            if not columnas_encontradas and score == 10.0:
                print(f"\n✅ CORRECTO: Sin columnas relevantes → Score = 10.0")
            elif columnas_encontradas and score < 5:
                resultado["razon_cero"] = f"Demasiados errores en validación (score bajo: {score})"
                print(f"\n⚠️ Score BAJO ({score}): Probablemente los datos tienen errores de validación")
            else:
                print(f"\n✅ La conformidad parece estar funcionando correctamente")
        else:
            resultado["razon_cero"] = f"Error HTTP {resp.status_code} al calcular conformidad"
            print(f"❌ Error: {resp.status_code}")
            print(f"   Respuesta: {resp.text}")
    except Exception as e:
        resultado["razon_cero"] = f"Excepción al calcular conformidad: {str(e)}"
        print(f"❌ Excepción: {e}")
    
    # ========== PASO 5: Recomendaciones ==========
    print(f"\n{'='*70}")
    print(f"💡 ANÁLISIS Y RECOMENDACIONES")
    print(f"{'='*70}\n")
    
    if resultado["score_final"] == 10.0:
        if columnas_encontradas:
            print("✅ EXCELENTE: Datos completamente válidos")
            print("   Todos los valores en las columnas validadas cumplen las reglas.")
        else:
            print("✅ CORRECTO: Sin columnas para validar")
            print("   El dataset no tiene columnas de tipos: departamento, municipio, año, latitud, longitud, correo")
            print("   → Por defecto, score = 10.0 (conforme)")
    
    elif resultado["score_final"] and resultado["score_final"] > 5:
        print(f"⚠️ ACEPTABLE: Score = {resultado['score_final']}")
        print("   Hay algunos errores de validación pero mayoritariamente válido.")
        print("   Considera revisar datos en las columnas detectadas.")
    
    elif resultado["score_final"] and resultado["score_final"] <= 5:
        print(f"❌ DEFICIENTE: Score = {resultado['score_final']}")
        print("   Muchos errores en las columnas validadas.")
        print("\n   ACCIONES:")
        print("   1. Revisa las columnas detectadas")
        print("   2. Valida los formatos de datos:")
        print("      • Departamentos: Deben ser nombres válidos de Colombia")
        print("      • Años: Números entre 1900 y 2025")
        print("      • Coordenadas: Latitud 0-13, Longitud -81 a -66")
        print("      • Correos: Formato usuario@dominio.ext")
        print("   3. Limpia los datos inválidos")
    
    return resultado


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python diagnostico_conformidad.py <dataset_id>")
        print("\nEjemplo:")
        print("  python diagnostico_conformidad.py pbhj-r8dg")
        sys.exit(1)
    
    dataset_id = sys.argv[1]
    resultado = diagnosticar_conformidad(dataset_id)
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*70}\n")
    print(f"Dataset: {resultado['dataset_id']}")
    print(f"Score: {resultado['score_final']}")
    print(f"Columnas detectadas: {sum(len(v) for v in resultado['columnas_detectadas'].values())}")

