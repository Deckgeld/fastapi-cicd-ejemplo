from fastapi import APIRouter

router = APIRouter()

# Simulación de base de datos en memoria
fake_db = {
    1: {"id": 1, "name": "Laptop", "price": 999.99},
    2: {"id": 2, "name": "Mouse", "price": 29.99},
}

@router.get("/items", summary="Obtener todos los items")
def get_items():
    """Endpoint 1: Devuelve la lista completa de items."""
    return {"items": list(fake_db.values())}

@router.get("/items/{item_id}", summary="Obtener un item por ID")
def get_item(item_id: int):
    """Endpoint 2: Devuelve un item específico por su ID."""
    if item_id not in fake_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return fake_db[item_id]
