# Análisis del Backend - Flujo de Datos

## Problema Identificado

El backend tiene una **variable global `calculator`** que es compartida por todos los endpoints.
Esto significa que si un usuario:

1. Hace `POST /initialize` con dataset A
2. Luego hace `GET /actualidad`
   - Se usa el `calculator` del dataset A ✅ (Correcto)

Pero si otro usuario hace:
3. `POST /initialize` con dataset B  
4. El anterior usuario hace `GET /actualidad` nuevamente
   - Se usa el `calculator` del dataset B ❌ (INCORRECTO - debería ser A)

## Solución Recomendada

**Opción 1: Sessionless (Recomendado para estateless APIs)**
- Cada endpoint recibe el `dataset_id` en la petición
- Se calcula sobre la marcha sin mantener estado global
- Mejor para REST APIs

**Opción 2: Session-based con ID**
- Enviar el `dataset_id` en cada endpoint GET
- Validar que coincida con el `calculator` actual
- Mantiene el contexto consistente

## Flujo Actual (main.py)

```
POST /initialize?dataset_id=XYZ
  ↓
Obtiene metadatos de dataset XYZ
  ↓
Crea: calculator = DataQualityCalculator(XYZ, metadata)
  ↓
Almacena en variable global `calculator`

GET /actualidad
  ↓
Usa el `calculator` global
  ↓
Devuelve score basado en el dataset del último /initialize
```

## Recomendación

Para que sea consistente y seguro en un entorno multi-usuario:

**Cambio necesario:**
Pasar `dataset_id` en los GET endpoints para validar consistencia:

```
GET /actualidad?dataset_id=XYZ
```

Si no coincide con el `calculator` global actual, devolver error.
