import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API configuration
API_HOST = os.getenv("HOST", "localhost")
API_PORT = os.getenv("PORT", "8001")
base_url = f"http://{API_HOST}:{API_PORT}"

dataset_request = {
    "dataset_url": "https://api.example.com/data.json",
    "metadata": {
        "titulo": "Dataset de Prueba",
        "descripcion": "Este es un dataset de prueba para validar los criterios de calidad de datos",
        "fecha_actualizacion": "2025-11-01",
        "frecuencia_actualizacion_dias": 30,
        "fuente": "Entidad de Prueba",
        "publicador": "Departamento de Datos",
        "licencia": "CC BY 4.0",
        "tags": ["prueba", "calidad", "datos"],
        "attribution_links": ["https://example.com"],
        "etiqueta_fila": "Registro de datos de ejemplo",
        "columnas": {
            "id": {"descripcion": "Identificador unico del registro"},
            "nombre": {"descripcion": "Nombre completo"},
            "edad": {"descripcion": "Edad en anos"}
        }
    }
}

print("Testing Data Quality Assessment API")
print("=" * 50)

print("\n1. Initializing dataset...")
response = requests.post(f"{base_url}/initialize", json=dataset_request)
if response.status_code == 200:
    print(f"   Success: {response.json()}")
else:
    print(f"   Error: {response.text}")
    exit(1)

endpoints = [
    "confidencialidad",
    "relevancia",
    "actualidad",
    "trazabilidad",
    "conformidad",
    "exactitudSintactica",
    "exactitudSemantica",
    "completitud",
    "consistencia",
    "precision",
    "portabilidad",
    "credibilidad",
    "comprensibilidad",
    "accesibilidad",
    "unicidad",
    "eficiencia",
    "recuperabilidad",
    "disponibilidad"
]

print("\n2. Testing individual endpoints:")
results = {}
for endpoint in endpoints:
    response = requests.get(f"{base_url}/{endpoint}")
    if response.status_code == 200:
        score = response.json()['score']
        results[endpoint] = score
        print(f"   {endpoint}: {score}/10")
    else:
        print(f"   {endpoint}: Error - {response.text}")

print("\n3. Testing all_scores endpoint:")
response = requests.get(f"{base_url}/all_scores")
if response.status_code == 200:
    all_scores = response.json()
    print(f"   All scores retrieved successfully")
    print(f"   Total criteria: {len(all_scores)}")
else:
    print(f"   Error: {response.text}")

print("\n" + "=" * 50)
print("Testing completed!")
