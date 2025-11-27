"""
Script de prueba para la métrica de accesibilidad (metadata-only)
"""
from data_quality_calculator import DataQualityCalculator

# Metadata de ejemplo
metadata_example = {
    'tags': ['número de afiliados por departamento', 'afiliados'],
    'attributionLink': 'https://www.colpensiones.gov.co',
    'metadata': {
        'custom_fields': {
            'Información de Datos': {
                'URL Documentación': 'https://www.colpensiones.gov.co/documentacion',
                'URL Normativa': 'https://www.colpensiones.gov.co/Publicaciones/nuestra_entidad_colpensiones/Normativas'
            }
        }
    }
}

calc = DataQualityCalculator('test')
calc.metadata = metadata_example

score = calc.calculate_accesibilidad_from_metadata(metadata_example, verbose=True)
print('\nResultado accesibilidad:', score)
