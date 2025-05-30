from fastapi import APIRouter, Request, HTTPException, status, Depends
from typing import Dict, Any
import os
import mercadopago
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel

from services.supabase_client import get_supabase_client

# Carregando variáveis de ambiente
load_dotenv()

router = APIRouter()

# Configurando cliente do Mercado Pago
mp_client = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# Modelo para a requisição de assinatura
class SubscriptionRequest(BaseModel):
    user_id: str

@router.post("/webhook")
async def process_webhook(request: Request):
    """
    Processa webhooks do Mercado Pago para atualizar assinaturas
    """
    try:
        payload = await request.json()
        
        # Verificar se é uma notificação de pagamento
        if payload.get("action") == "payment.created" or payload.get("action") == "payment.updated":
            payment_id = payload.get("data", {}).get("id")
            
            if not payment_id:
                return {"status": "ignored", "reason": "not_payment_notification"}
            
            # Obter detalhes do pagamento
            payment_info = mp_client.payment().get(payment_id)
            
            if payment_info["status"] != 200:
                return {"status": "error", "reason": "payment_not_found"}
            
            payment_data = payment_info["response"]
            
            # Verificar se o pagamento foi aprovado
            if payment_data["status"] == "approved":
                # Extrair dados do pagamento
                external_reference = payment_data.get("external_reference")
                
                if not external_reference:
                    return {"status": "error", "reason": "no_external_reference"}
                
                # O external_reference deve conter o ID do usuário
                user_id = external_reference
                
                # Atualizar assinatura no Supabase
                supabase = get_supabase_client()
                
                # Calcular data de validade (30 dias a partir de agora)
                valid_until = (datetime.utcnow() + timedelta(days=30)).isoformat()
                
                # Verificar se já existe assinatura
                subscription = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
                
                if subscription.data and len(subscription.data) > 0:
                    # Atualizar assinatura existente
                    supabase.table("subscriptions").update({
                        "is_active": True,
                        "valid_until": valid_until,
                        "last_payment_id": payment_id,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("user_id", user_id).execute()
                else:
                    # Criar nova assinatura
                    supabase.table("subscriptions").insert({
                        "user_id": user_id,
                        "is_active": True,
                        "valid_until": valid_until,
                        "last_payment_id": payment_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }).execute()
                
                return {"status": "success", "message": "subscription_updated"}
            
            return {"status": "ignored", "reason": "payment_not_approved"}
        
        return {"status": "ignored", "reason": "not_relevant_action"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar webhook: {str(e)}"
        )

@router.post("/subscribe")
async def create_subscription(subscription_data: SubscriptionRequest):
    """
    Cria uma preferência de pagamento no Mercado Pago
    """
    try:
        user_id = subscription_data.user_id
        
        # Configurar preferência de pagamento
        preference_data = {
            "items": [
                {
                    "title": "Assinatura Mensal - Devocionais Personalizados",
                    "quantity": 1,
                    "unit_price": 29.90,
                    "currency_id": "BRL"
                }
            ],
            "back_urls": {
                "success": f"{os.getenv('APP_URL', 'http://localhost:8000')}/payment/success",
                "failure": f"{os.getenv('APP_URL', 'http://localhost:8000')}/payment/failure",
                "pending": f"{os.getenv('APP_URL', 'http://localhost:8000')}/payment/pending"
            },
            "auto_return": "approved",
            "external_reference": user_id,
            "notification_url": os.getenv("MP_WEBHOOK_URL")
        }
        
        preference_response = mp_client.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar preferência de pagamento"
            )
        
        preference = preference_response["response"]
        
        return {
            "preference_id": preference["id"],
            "init_point": preference["init_point"],
            "sandbox_init_point": preference["sandbox_init_point"],
            "public_key": os.getenv("MP_PUBLIC_KEY")
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar preferência de pagamento: {str(e)}"
        ) 