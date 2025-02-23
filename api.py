from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Union
import json
import os

app = FastAPI()

# Ruta para almacenar el archivo JSON con las keys
KEYS_FILE_PATH = "keys.json"

# Almacén de keys en memoria
keys_store: Dict[str, dict] = {}

class Key(BaseModel):
    key: str
    valid: bool = True
    security_code: Union[str, None] = None
    expiration: Union[str, None] = None  # Para keys FREE
    owner: Union[str, None] = None         # Se asigna cuando se reclama la key
    claimed: bool = False                  # Indica si la key ya fue reclamada

def load_keys_from_file():
    global keys_store
    if os.path.exists(KEYS_FILE_PATH):
        with open(KEYS_FILE_PATH, "r") as file:
            keys_store = json.load(file)
    else:
        keys_store = {}

def save_keys_to_file():
    with open(KEYS_FILE_PATH, "w") as file:
        json.dump(keys_store, file, indent=4)

@app.on_event("startup")
async def startup_event():
    load_keys_from_file()

@app.get("/keys", response_class=JSONResponse, summary="Obtener todas las keys", tags=["Keys"])
async def get_keys():
    return keys_store

@app.post("/keys", response_class=JSONResponse, summary="Agregar una nueva key", tags=["Keys"])
async def add_key(key: Key):
    if key.key in keys_store:
        raise HTTPException(status_code=400, detail="La key ya existe")
    keys_store[key.key] = key.dict()
    save_keys_to_file()
    # Retornamos solo el objeto asociado a la key para cumplir con el formato deseado
    return { key.key: keys_store[key.key] }

@app.get("/verify_key", summary="Verificar Key", tags=["Keys"])
async def verify_key(key: str = Query(..., description="La key a verificar")):
    if key in keys_store:
        return {"valid": keys_store[key]["valid"], "key_data": keys_store[key]}
    else:
        raise HTTPException(status_code=404, detail="Key no encontrada")

@app.post("/set_security", summary="Establecer código de seguridad", tags=["Keys"])
async def set_security(key: str = Query(..., description="La key a actualizar"),
                       code: str = Query(..., description="El código de seguridad a asignar")):
    if key in keys_store:
        keys_store[key]["security_code"] = code
        save_keys_to_file()
        return {"message": "Código de seguridad actualizado correctamente", "key_data": keys_store[key]}
    else:
        raise HTTPException(status_code=404, detail="Key no encontrada")

@app.post("/claim_key", response_class=JSONResponse, summary="Reclamar key pendiente", tags=["Keys"])
async def claim_key(code: str = Query(..., description="El código temporal de la key"),
                    owner: str = Query(..., description="ID del owner que reclama la key")):
    """
    Reclama la key pendiente a partir del código temporal.
    Asigna el owner y marca la key como reclamada.
    """
    if code not in keys_store:
        raise HTTPException(status_code=404, detail="Código de key no encontrado")
    
    key_data = keys_store[code]
    if key_data.get("claimed", False):
        raise HTTPException(status_code=400, detail="La key ya ha sido reclamada")
    
    key_data["owner"] = owner
    key_data["claimed"] = True
    save_keys_to_file()
    return { code: key_data }
