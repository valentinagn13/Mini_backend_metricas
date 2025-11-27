"""
Script de prueba para el endpoint /unicidad con datos locales
"""
import pandas as pd
import numpy as np
from data_quality_calculator import DataQualityCalculator

# Crear datos de prueba
def create_test_data():
    """Crea un dataset de prueba con algunos duplicados conocidos"""
    
    print("\nCreando dataset de prueba con duplicados...")
    
    # Crear un DataFrame con datos y algunos duplicados
    data = {
        'id': list(range(1, 101)),
        'nombre': ['Usuario_' + str(i) for i in range(1, 101)],
        'edad': np.random.randint(18, 65, 100),
        'ciudad': np.random.choice(['Madrid', 'Barcelona', 'Valencia', 'Sevilla'], 100),
        'email': ['user_' + str(i) + '@example.com' for i in range(1, 101)],
        'copy_edad': np.random.randint(18, 65, 100),
    }
    
    df = pd.DataFrame(data)
    
    # Agregar algunas filas duplicadas (últimas 5 filas son copia de las primeras 5)
    df = pd.concat([df, df.iloc[:5].copy()], ignore_index=True)
    
    print(f"OK - Dataset creado: {len(df)} filas, {len(df.columns)} columnas")
    print(f"     Filas duplicadas exactas esperadas: 5")
    
    return df

def test_unicidad_local():
    """Prueba la métrica de unicidad con datos locales"""
    
    print("\n" + "="*70)
    print("TEST DEL METODO calculate_unicidad() CON DATOS LOCALES")
    print("="*70)
    
    # Crear calculadora
    calculator = DataQualityCalculator("test_dataset")
    
    # Crear datos de prueba
    df_test = create_test_data()
    
    # Asignar datos al calculador
    calculator.df = df_test
    calculator.df_filas = len(df_test)
    calculator.df_columnas = len(df_test.columns)
    calculator.metadata = {'columns': [{'name': col} for col in df_test.columns]}
    
    print(f"\nDataset asignado al calculador:")
    print(f"  - Filas: {calculator.df_filas}")
    print(f"  - Columnas: {calculator.df_columnas}")
    
    # Probar con diferentes niveles de riesgo
    print(f"\nPRUEBAS CON DIFERENTES NIVELES DE RIESGO:")
    print("-" * 70)
    
    results = {}
    for nivel_riesgo in [1.0, 1.5, 2.0]:
        print(f"\n[TEST] Nivel de riesgo: {nivel_riesgo}")
        try:
            score = calculator.calculate_unicidad(nivel_riesgo=nivel_riesgo)
            results[nivel_riesgo] = score
            print(f"   RESULTADO: Score = {score:.2f}/10")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Validaciones
    print(f"\n" + "="*70)
    print("VALIDACIONES:")
    print("="*70)
    
    # Validación 1: El score debe estar entre 0 y 10
    print(f"\n1. Rango de scores (0-10):")
    for nivel, score in results.items():
        status = "OK" if 0 <= score <= 10 else "FALLO"
        print(f"   Nivel {nivel}: {score:.2f} [{status}]")
    
    # Validación 2: Mayor penalización con mayor nivel_riesgo
    print(f"\n2. Penalizacion aumenta con nivel_riesgo:")
    if results[1.0] >= results[1.5] >= results[2.0]:
        print(f"   {results[1.0]:.2f} >= {results[1.5]:.2f} >= {results[2.0]:.2f} [OK]")
    else:
        print(f"   {results[1.0]:.2f} >= {results[1.5]:.2f} >= {results[2.0]:.2f} [FALLO]")
    
    # Validación 3: Dataset con duplicados debe tener score < 10
    print(f"\n3. Dataset con duplicados tiene score < 10:")
    status = "OK" if results[1.5] < 10 else "FALLO"
    print(f"   Score (1.5): {results[1.5]:.2f} < 10 [{status}]")
    
    print("\n" + "="*70)
    print("TEST COMPLETADO")
    print("="*70)

if __name__ == "__main__":
    test_unicidad_local()
