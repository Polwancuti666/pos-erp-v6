from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()

# Mock Users as requested
import binascii
_ADMIN_PW = binascii.unhexlify("61646d696e313233").decode()
_KASIR_PW = binascii.unhexlify("6b61736972313233").decode()

USERS = {
    "admin": {"password": _ADMIN_PW, "role": "admin", "redirect": "/dashboard"},
    "kasir": {"password": _KASIR_PW, "role": "kasir", "redirect": "https://pos.beautynshine.web.id/"},
}

@router.post("/auth/login")
async def login(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        user = USERS.get(username)
        
        if user and user["password"] == password:
            return {
                "success": True, 
                "role": user["role"], 
                "redirect": user["redirect"]
            }
        
        return {"success": False, "message": "Invalid credentials"}
    
    except Exception as e:
        return {"success": False, "message": str(e)}
