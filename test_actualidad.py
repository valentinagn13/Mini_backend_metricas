from data_quality_calculator import DataQualityCalculator
from datetime import datetime, timedelta

# Test casos de "Más de tres años" con diferentes variaciones
test_cases = [
    {
        'nombre': 'Más de tres años (normal)',
        'metadata': {
            'frecuencia_actualizacion': 'Más de tres años',
            'fecha_actualizacion': (datetime.now() - timedelta(days=100)).isoformat()
        }
    },
    {
        'nombre': 'más de tres años (minúsculas)',
        'metadata': {
            'frecuencia_actualizacion': 'más de tres años',
            'fecha_actualizacion': (datetime.now() - timedelta(days=100)).isoformat()
        }
    },
    {
        'nombre': 'MAS DE TRES ANOS (mayúsculas sin acentos)',
        'metadata': {
            'frecuencia_actualizacion': 'MAS DE TRES ANOS',
            'fecha_actualizacion': (datetime.now() - timedelta(days=100)).isoformat()
        }
    },
    {
        'nombre': 'MÁS DE TRES AÑOS (mayúsculas con acentos)',
        'metadata': {
            'frecuencia_actualizacion': 'MÁS DE TRES AÑOS',
            'fecha_actualizacion': (datetime.now() - timedelta(days=100)).isoformat()
        }
    },
    {
        'nombre': 'Mensual (para comparación)',
        'metadata': {
            'frecuencia_actualizacion': 'Mensual',
            'fecha_actualizacion': (datetime.now() - timedelta(days=100)).isoformat()
        }
    }
]

dq = DataQualityCalculator('test_url', {})

print("=" * 70)
print("TEST: Lógica de 'Más de tres años'")
print("=" * 70)

for test in test_cases:
    print(f"\n📌 Test: {test['nombre']}")
    score = dq.calculate_actualidad(test['metadata'])
    print(f"   Resultado: {score}/10")
