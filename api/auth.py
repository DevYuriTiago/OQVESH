from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

from services.supabase_client import get_supabase_client

# Carregando variáveis de ambiente
load_dotenv()

router = APIRouter()

# Configuração do OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Modelos Pydantic
class UserCreate(BaseModel):
    email: str
    password: str
    nome: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

# Funções de autenticação
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM", "HS256"))
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM", "HS256")])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Verificar se o usuário existe no Supabase
    supabase = get_supabase_client()
    user = supabase.table("profiles").select("*").eq("id", user_id).execute()
    
    if not user.data or len(user.data) == 0:
        raise credentials_exception
    
    return user.data[0]

# Rotas de autenticação
@router.post("/signup", response_model=Token)
async def signup(user: UserCreate):
    """
    Registra um novo usuário no sistema
    """
    supabase = get_supabase_client()
    
    try:
        # Registrar usuário no Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        user_id = auth_response.user.id
        
        # O trigger do Supabase cria automaticamente o perfil do usuário e o registro de uso
        # Vamos esperar um pouco e então buscar o perfil criado
        import time
        time.sleep(1)  # Pequena pausa para garantir que o trigger tenha tempo de executar
        
        # Buscar perfil criado pelo trigger
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if profile.data and len(profile.data) > 0:
            # Se o nome foi fornecido, atualizar o perfil
            if user.nome:
                supabase.table("profiles").update({"nome": user.nome}).eq("id", user_id).execute()
                profile.data[0]["nome"] = user.nome
        
        # Gerar token JWT
        access_token = create_access_token({"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": profile.data[0] if profile.data else {
                "id": user_id,
                "email": user.email,
                "nome": user.nome or "",
                "created_at": datetime.utcnow().isoformat()
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Autentica um usuário e retorna um token JWT (usado pelo Swagger e OAuth2)
    """
    supabase = get_supabase_client()
    
    try:
        # Autenticar usuário no Supabase
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": form_data.username,
                "password": form_data.password
            })
            
            user_id = auth_response.user.id
        except Exception as auth_error:
            # Verificar se o erro é de email não confirmado
            error_message = str(auth_error)
            if "Email not confirmed" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email não confirmado. Por favor, verifique sua caixa de entrada."
                )
            
            # Se não for erro de confirmação, repassar o erro original
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buscar dados do perfil
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not profile.data or len(profile.data) == 0:
            # Se o perfil não existir, vamos criá-lo
            profile_data = {
                "id": user_id,
                "email": form_data.username,
                "nome": "",
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("profiles").insert(profile_data).execute()
            
            # Também criar o registro de uso
            supabase.table("usages").insert({
                "user_id": user_id,
                "devotional_count": 0,
                "last_used": datetime.utcnow().isoformat()
            }).execute()
            
            # Buscar novamente o perfil
            profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        # Atualizar último acesso
        try:
            supabase.table("usages").update({
                "last_used": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
        except Exception:
            # Se falhar a atualização de uso, não é crítico
            pass
        
        # Gerar token JWT
        access_token = create_access_token({"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": profile.data[0] if profile.data and len(profile.data) > 0 else {
                "id": user_id,
                "email": form_data.username,
                "nome": "",
                "created_at": datetime.utcnow().isoformat()
            }
        }
    
    except HTTPException:
        # Repassar exceções HTTP que já foram criadas
        raise
    except Exception as e:
        print(f"Erro ao fazer login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/login-json", response_model=Token)
async def login_json(user_data: UserLogin):
    """
    Autentica um usuário via JSON e retorna um token JWT (usado pelo frontend)
    """
    supabase = get_supabase_client()
    
    try:
        # Autenticar usuário no Supabase
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            
            user_id = auth_response.user.id
        except Exception as auth_error:
            # Verificar se o erro é de email não confirmado
            error_message = str(auth_error)
            if "Email not confirmed" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email não confirmado. Por favor, verifique sua caixa de entrada."
                )
            
            # Se não for erro de confirmação, verificar se as credenciais estão corretas
            # tentando buscar o usuário diretamente
            users_response = supabase.auth.admin.list_users()
            for user in users_response.users:
                if user.email == user_data.email:
                    # Usuário existe, então a senha deve estar incorreta
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Senha incorreta."
                    )
            
            # Se não encontrou o usuário, é porque ele não existe
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email não encontrado."
            )
        
        # Buscar dados do perfil
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not profile.data or len(profile.data) == 0:
            # Se o perfil não existir, vamos criá-lo
            profile_data = {
                "id": user_id,
                "email": user_data.email,
                "nome": "",
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("profiles").insert(profile_data).execute()
            
            # Também criar o registro de uso
            supabase.table("usages").insert({
                "user_id": user_id,
                "devotional_count": 0,
                "last_used": datetime.utcnow().isoformat()
            }).execute()
            
            # Buscar novamente o perfil
            profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        # Atualizar último acesso
        try:
            supabase.table("usages").update({
                "last_used": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
        except Exception:
            # Se falhar a atualização de uso, não é crítico
            pass
        
        # Gerar token JWT
        access_token = create_access_token({"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": profile.data[0] if profile.data and len(profile.data) > 0 else {
                "id": user_id,
                "email": user_data.email,
                "nome": "",
                "created_at": datetime.utcnow().isoformat()
            }
        }
    
    except HTTPException:
        # Repassar exceções HTTP que já foram criadas
        raise
    except Exception as e:
        print(f"Erro ao fazer login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me")
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retorna os dados do usuário autenticado
    """
    return current_user 