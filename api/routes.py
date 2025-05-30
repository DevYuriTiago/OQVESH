from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os

from api.auth import get_current_user
from services.supabase_client import get_supabase_client
from chains.devotional_chain import generate_devotional

router = APIRouter()

class FeelingRequest(BaseModel):
    sentimento: str

class DevotionalSaveRequest(BaseModel):
    sentimento: str
    greeting: str
    verse: Dict[str, str]
    content: str
    date: str

class DevotionalResponse(BaseModel):
    texto: str
    versiculos: list
    reflexao: str
    oracao: str

@router.post("/feelings", response_model=Dict[str, Any])
async def process_feeling(
    request: FeelingRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Processa o sentimento do usuário e gera um devocional personalizado.
    Verifica se o usuário tem usos gratuitos disponíveis ou assinatura ativa.
    """
    user_id = current_user["id"]
    supabase = get_supabase_client()
    
    # Verificar status da assinatura e contagem de uso
    subscription = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
    usage = supabase.table("usages").select("*").eq("user_id", user_id).execute()
    
    is_subscribed = False
    usage_count = 0
    
    # Verificar se o usuário tem assinatura ativa
    if subscription.data and len(subscription.data) > 0:
        is_subscribed = subscription.data[0].get("is_active", False)
    
    # Verificar contagem de uso
    if usage.data and len(usage.data) > 0:
        usage_count = usage.data[0].get("devotional_count", 0)
    else:
        # Criar registro de uso se não existir
        supabase.table("usages").insert({"user_id": user_id, "devotional_count": 0}).execute()
    
    # Verificar se o usuário pode gerar um devocional
    free_usage_limit = int(os.getenv("FREE_USAGE_LIMIT", "5"))
    if not is_subscribed and usage_count >= free_usage_limit:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "detail": "Limite de uso gratuito atingido. Por favor, assine o serviço para continuar.",
                "subscription_required": True
            }
        )
    
    # Gerar o devocional
    try:
        devotional = generate_devotional(request.sentimento)
        
        # Salvar o devocional no banco de dados
        supabase.table("devotionals").insert({
            "user_id": user_id,
            "sentimento": request.sentimento,
            "texto": devotional["texto"],
            "versiculos": devotional["versiculos"],
            "reflexao": devotional["reflexao"],
            "oracao": devotional["oracao"]
        }).execute()
        
        # Atualizar contagem de uso
        if usage.data and len(usage.data) > 0:
            supabase.table("usages").update({"devotional_count": usage_count + 1}).eq("user_id", user_id).execute()
        else:
            supabase.table("usages").insert({"user_id": user_id, "devotional_count": 1}).execute()
        
        return devotional
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar devocional: {str(e)}"
        )

@router.post("/devotional/save")
async def save_devotional(
    request: DevotionalSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Salva um devocional gerado pelo usuário
    """
    user_id = current_user["id"]
    supabase = get_supabase_client()
    
    try:
        devotional_data = {
            "user_id": user_id,
            "sentimento": request.sentimento,
            "greeting": request.greeting,
            "verse_text": request.verse.get("text", ""),
            "verse_reference": request.verse.get("reference", ""),
            "content": request.content,
            "created_at": request.date
        }
        
        result = supabase.table("saved_devotionals").insert(devotional_data).execute()
        
        if result.data:
            return {"success": True, "message": "Devocional salvo com sucesso"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao salvar devocional"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar devocional: {str(e)}"
        )

@router.get("/status")
async def get_user_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retorna o status do usuário: usos restantes, assinatura ativa, validade
    """
    user_id = current_user["id"]
    supabase = get_supabase_client()
    
    # Obter dados de assinatura e uso
    subscription = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
    usage = supabase.table("usages").select("*").eq("user_id", user_id).execute()
    
    is_subscribed = False
    valid_until = None
    usage_count = 0
    
    if subscription.data and len(subscription.data) > 0:
        is_subscribed = subscription.data[0].get("is_active", False)
        valid_until = subscription.data[0].get("valid_until")
    
    if usage.data and len(usage.data) > 0:
        usage_count = usage.data[0].get("devotional_count", 0)
    
    free_usage_limit = int(os.getenv("FREE_USAGE_LIMIT", "5"))
    usos_restantes = max(0, free_usage_limit - usage_count) if not is_subscribed else "ilimitado"
    
    return {
        "usos_restantes": usos_restantes,
        "assinatura_ativa": is_subscribed,
        "validade": valid_until
    }

@router.get("/devotionals")
async def get_user_devotionals(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retorna todos os devocionais gerados pelo usuário
    """
    user_id = current_user["id"]
    supabase = get_supabase_client()
    
    devotionals = supabase.table("devotionals").select("*").eq("user_id", user_id).execute()
    
    return devotionals.data

@router.get("/devotional/saved")
async def get_saved_devotionals(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retorna todos os devocionais salvos pelo usuário
    """
    user_id = current_user["id"]
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("saved_devotionals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"devotionals": result.data}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar devocionais salvos: {str(e)}"
        )