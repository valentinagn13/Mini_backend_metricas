"""
Test de integración: Valida que el backend use consistentemente el dataset_id del frontend
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API configuration
API_HOST = os.getenv("HOST", "localhost")
API_PORT = os.getenv("PORT", "8001")
BASE_URL = f"http://{API_HOST}:{API_PORT}"
DATASET_ID = "ijus-ubej"

print("=" * 80)
print("TEST: Validación de Consistencia Dataset ID")
print("=" * 80)

# Test 1: Inicializar con dataset correcto
print("\n✅ Test 1: POST /initialize")
print(f"   Enviando dataset_id: {DATASET_ID}")

response = requests.post(
    f"{BASE_URL}/initialize",
    json={"dataset_id": DATASET_ID, "load_full": False}
)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   ✅ Inicializado correctamente")
    print(f"   - Dataset Name: {data['dataset_name']}")
    print(f"   - Metadata Obtained: {data['metadata_obtained']}")
else:
    print(f"   ❌ Error: {response.text}")
    exit(1)

# Test 2: Calcular actualidad con dataset_id CORRECTO
print("\n✅ Test 2: GET /actualidad con dataset_id CORRECTO")
print(f"   Parámetro dataset_id: {DATASET_ID}")

response = requests.get(f"{BASE_URL}/actualidad?dataset_id={DATASET_ID}")

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   ✅ Actualidad calculada correctamente")
    print(f"   - Score: {data['score']}")
else:
    print(f"   ❌ Error: {response.text}")
    exit(1)

# Test 3: Intentar calcular actualidad con dataset_id INCORRECTO
print("\n✅ Test 3: GET /actualidad con dataset_id INCORRECTO (debe fallar)")
WRONG_DATASET = "8dbv-wsjq"
print(f"   Parámetro dataset_id: {WRONG_DATASET}")

response = requests.get(f"{BASE_URL}/actualidad?dataset_id={WRONG_DATASET}")

print(f"   Status: {response.status_code}")
if response.status_code == 400:
    data = response.json()
    print(f"   ✅ Correctamente rechazado con error 400")
    print(f"   - Error: {data['detail']}")
    # Validar que el mensaje sea de mismatch
    if "mismatch" in data['detail'].lower() or "initialized" in data['detail'].lower():
        print(f"   ✅ Mensaje de validación correcto")
    else:
        print(f"   ❌ Mensaje inesperado: {data['detail']}")
        exit(1)
else:
    print(f"   ❌ No devolvió 400. Devolvió: {response.status_code}")
    print(f"   Response: {response.text}")
    exit(1)

print("\n" + "=" * 80)
print("✅ TODOS LOS TESTS PASARON - Backend valida correctamente dataset_id")
print("=" * 80)
