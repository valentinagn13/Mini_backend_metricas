import asyncio
import traceback
import json
from data_quality_calculator import DataQualityCalculator

DATASET_ID = 'tngu-f6c7'

async def main():
    try:
        print(f"Iniciando prueba de unicidad para dataset: {DATASET_ID}")
        calc = DataQualityCalculator(DATASET_ID)

        # Cargar una muestra razonable para debug (5000 filas) para reducir tiempo
        print("-> Cargando datos (limit=1000). Esto puede tardar menos...")
        try:
            await calc.load_data(limit=1000)
        except Exception as e:
            print("Error al ejecutar load_data:")
            traceback.print_exc()
            return

        if getattr(calc, 'df', None) is None:
            print("No se cargó DataFrame (df es None). Abortando prueba.")
            return

        print(f"-> Data cargada: {len(calc.df)} filas x {len(calc.df.columns)} columnas")

        # Llamar al cálculo de unicidad (con nivel por defecto)
        try:
            score = calc.calculate_unicidad()
            print(f"\n==> Score de Unicidad: {score}\n")
        except Exception as e:
            print("Error durante calculate_unicidad():")
            traceback.print_exc()

    except Exception:
        print("Error inesperado en script de prueba:")
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
