from fastapi import FastAPI, HTTPException, Query
import aiohttp
import uuid
from pydantic import BaseModel, Field
from typing import Dict, Any, Union

app = FastAPI(
    title="CarighasBot API",
    description="API para gestionar las keys de Carighas",
    version="1.0.0"
)

# URL remota donde se almacenan las keys
KEYS_URL = "https://lesuchiha.github.io/Carighas/keys.json"

# Almacén en memoria para las keys
keys_store: Dict[str, Any] = {}

class Key(BaseModel):
    key: str = Field(..., description="Identificador único de la key")
    valid: bool = Field(True, description="Indica si la key es válida")
    security_code: Union[str, None] = Field(None, description="Código de seguridad asociado")

async def load_remote_keys() -> None:
    """
    Carga las keys desde el archivo remoto JSON y las almacena en `keys_store`.
    Se asume que el JSON es un objeto dict o una lista de objetos con la propiedad "key".
    """
    global keys_store
    async with aiohttp.ClientSession() as session:
        async with session.get(KEYS_URL) as response:
            if response.status == 200:
                data = await response.json()
                # Si el JSON es un dict, lo usamos directamente.
                if isinstance(data, dict):
                    keys_store = data
                # Si es una lista, convertimos cada objeto en una entrada del dict usando su campo "key"
                elif isinstance(data, list):
                    keys_store = {item["key"]: item for item in data if "key" in item}
                else:
                    raise HTTPException(status_code=500, detail="Formato de JSON no soportado")
            else:
                raise HTTPException(status_code=500, detail="Error al obtener las keys remotas")

@app.on_event("startup")
async def startup_event():
    await load_remote_keys()

@app.get("/", summary="Inicio", tags=["Root"])
async def root():
    """
    Ruta raíz que muestra un mensaje de bienvenida.
    """
    return {"message": "Bienvenido a la API de CarighasBot"}

@app.get("/reload_keys", summary="Recargar Keys", tags=["Keys"])
async def reload_keys():
    """
    Recarga las keys desde la fuente remota.
    Útil si se actualizó el JSON manualmente.
    """
    await load_remote_keys()
    return {"message": "Keys recargadas correctamente"}

@app.post("/buy_key", summary="Comprar Key", tags=["Keys"])
async def buy_key():
    """
    Genera una nueva key única y la añade al almacén.
    Nota: esta nueva key solo se guarda en memoria y no se actualiza en el JSON remoto.
    """
    new_key = str(uuid.uuid4())
    new_key_data = {"key": new_key, "valid": True, "security_code": None}
    keys_store[new_key] = new_key_data
    return {"key": new_key}

@app.get("/verify_key", summary="Verificar Key", tags=["Keys"])
async def verify_key(key: str = Query(..., description="La key a verificar")):
    """
    Verifica si una key existe y es válida.
    Retorna la información de la key si se encuentra.
    """
    if key in keys_store:
        return {"valid": keys_store[key].get("valid", False), "key_data": keys_store[key]}
    else:
        raise HTTPException(status_code=404, detail="Key no encontrada")

@app.post("/set_security", summary="Establecer Código de Seguridad", tags=["Keys"])
async def set_security(
    key: str = Query(..., description="La key a actualizar"),
    code: str = Query(..., description="El código de seguridad a asignar")
):
    """
    Establece o actualiza el código de seguridad para una key dada.
    """
    if key in keys_store:
        keys_store[key]["security_code"] = code
        return {"message": "Código de seguridad actualizado correctamente", "key_data": keys_store[key]}
    else:
        raise HTTPException(status_code=404, detail="Key no encontrada")
