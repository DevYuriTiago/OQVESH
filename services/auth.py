import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv

from services.supabase_client import get_supabase_client

# Carregando variáveis de ambiente
load_dotenv()

class AuthService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.secret_key = os.getenv("SECRET_KEY")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    def create_access_token(self, data: dict) -> str:
        """
        Cria um token JWT para autenticação
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica a validade de um token JWT
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            
            if user_id is None:
                return None
            
            return {"user_id": user_id}
        
        except JWTError:
            return None
    
    async def register_user(self, email: str, password: str, nome: Optional[str] = None) -> Dict[str, Any]:
        """
        Registra um novo usuário no sistema
        """
        try:
            # Registrar usuário no Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            user_id = auth_response.user.id
            
            # Criar perfil do usuário
            profile_data = {
                "id": user_id,
                "email": email,
                "nome": nome or "",
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("profiles").insert(profile_data).execute()
            
            # Criar registro de uso
            self.supabase.table("usages").insert({
                "user_id": user_id,
                "devotional_count": 0,
                "last_used": datetime.utcnow().isoformat()
            }).execute()
            
            # Gerar token JWT
            access_token = self.create_access_token({"sub": user_id})
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": profile_data
            }
        
        except Exception as e:
            raise Exception(f"Erro ao registrar usuário: {str(e)}")
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Autentica um usuário e retorna um token JWT
        """
        try:
            # Autenticar usuário no Supabase
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            user_id = auth_response.user.id
            
            # Buscar dados do perfil
            profile = self.supabase.table("profiles").select("*").eq("id", user_id).execute()
            
            if not profile.data or len(profile.data) == 0:
                raise Exception("Perfil de usuário não encontrado")
            
            # Atualizar último acesso
            self.supabase.table("usages").update({
                "last_used": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            # Gerar token JWT
            access_token = self.create_access_token({"sub": user_id})
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": profile.data[0]
            }
        
        except Exception as e:
            raise Exception(f"Erro de autenticação: {str(e)}")
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca o perfil de um usuário pelo ID
        """
        try:
            profile = self.supabase.table("profiles").select("*").eq("id", user_id).execute()
            
            if not profile.data or len(profile.data) == 0:
                return None
            
            return profile.data[0]
        
        except Exception:
            return None 