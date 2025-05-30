import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from dotenv import load_dotenv
from typing import Optional

# Importando rotas da API
from api.routes import router as api_router
from api.auth import router as auth_router, get_current_user
from api.webhook import router as webhook_router
from services.supabase_client import get_supabase_client

# Carregando variáveis de ambiente
load_dotenv()

# Criando a aplicação FastAPI
app = FastAPI(
    title="Devocionais Personalizados",
    description="API para geração de devocionais cristãos personalizados",
    version="1.0.0",
)

# Configurando CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montando rotas da API
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(webhook_router, prefix="/api/mp", tags=["mercado_pago"])

# Configurando arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurando templates
templates = Jinja2Templates(directory="templates")

# Bearer token security
security = HTTPBearer(auto_error=False)

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Função para obter usuário atual de forma opcional (sem erro se não estiver logado)
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM", "HS256")])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            return None
            
        # Verificar se o usuário existe no Supabase
        supabase = get_supabase_client()
        user = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not user.data or len(user.data) == 0:
            return None
            
        return user.data[0]
    except JWTError:
        return None
    except Exception:
        return None

# Rota principal
@app.get("/")
async def root(request: Request, current_user = Depends(get_current_user_optional)):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": current_user
    })

# Rota de login
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Rota de cadastro
@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# Rota para página de assinatura
@app.get("/subscribe")
async def subscribe_page(request: Request):
    return templates.TemplateResponse("subscribe.html", {"request": request})

# Rota para verificação de status
@app.get("/health")
async def health_check():
    return {"status": "online", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 