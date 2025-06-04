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
async def root(request: Request):
    # Para a página principal, vamos sempre renderizar sem verificar autenticação no backend
    # A verificação será feita no frontend via JavaScript
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": None  # Sempre None, verificação será no frontend
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

# Rota para dashboard (verificação de autenticação via frontend)
@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": None  # Verificação será feita no frontend
    })

# Rota para verificação de status
@app.get("/health")
async def health_check():
    return {"status": "online", "version": "1.0.0"}

# Rota para verificar usuário logado via token
@app.get("/api/user/me")
async def get_current_user_info(current_user = Depends(get_current_user_optional)):
    if current_user:
        return {"user": current_user, "authenticated": True}
    return {"user": None, "authenticated": False}

# Rota para estatísticas do usuário
@app.get("/api/user/stats")
async def get_user_stats(current_user = Depends(get_current_user)):
    try:
        supabase = get_supabase_client()
        
        # Contar devocionais salvos
        devotionals = supabase.table("saved_devotionals").select("id").eq("user_id", current_user["id"]).execute()
        devotionals_count = len(devotionals.data) if devotionals.data else 0
        
        # Calcular streak (simplificado por enquanto)
        streak_count = 7  # Placeholder - implementar lógica real
        
        return {
            "devotionalsCount": devotionals_count,
            "streakCount": streak_count
        }
    except Exception as e:
        return {"devotionalsCount": 0, "streakCount": 0}

# Rota para configurações do usuário
@app.get("/api/user/settings")
async def get_user_settings(current_user = Depends(get_current_user)):
    try:
        supabase = get_supabase_client()
        
        # Buscar configurações do usuário
        settings = supabase.table("user_settings").select("*").eq("user_id", current_user["id"]).execute()
        
        if settings.data and len(settings.data) > 0:
            return settings.data[0]
        else:
            # Retornar configurações padrão
            return {
                "emailNotifications": True,
                "saveHistory": True
            }
    except Exception as e:
        return {
            "emailNotifications": True,
            "saveHistory": True
        }

# Rota para gerar devocional (compatibilidade com o dashboard)
@app.post("/generate_devotional")
async def generate_devotional_endpoint(request: Request, current_user = Depends(get_current_user)):
    try:
        data = await request.json()
        sentimento = data.get("sentimento", "")
        
        if not sentimento:
            raise HTTPException(status_code=400, detail="Sentimento é obrigatório")
        
        # Importar a cadeia de devocional
        from chains.devotional_chain import generate_devotional
        
        # Gerar o devocional
        devotional = generate_devotional(sentimento)
        
        # Atualizar contador de uso
        supabase = get_supabase_client()
        usage = supabase.table("usages").select("*").eq("user_id", current_user["id"]).execute()
        
        if usage.data and len(usage.data) > 0:
            current_count = usage.data[0].get("devotional_count", 0)
            supabase.table("usages").update({"devotional_count": current_count + 1}).eq("user_id", current_user["id"]).execute()
        else:
            supabase.table("usages").insert({"user_id": current_user["id"], "devotional_count": 1}).execute()
        
        return devotional
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar devocional: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)