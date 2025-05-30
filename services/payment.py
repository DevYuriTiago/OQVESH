import os
import mercadopago
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

from services.supabase_client import get_supabase_client

# Carregando variáveis de ambiente
load_dotenv()

class PaymentService:
    def __init__(self):
        self.mp_client = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))
        self.supabase = get_supabase_client()
    
    def create_payment_preference(self, user_id: str) -> Dict[str, Any]:
        """
        Cria uma preferência de pagamento no Mercado Pago
        """
        # Configurar preferência de pagamento
        preference_data = {
            "items": [
                {
                    "title": "Assinatura Mensal - Devocionais Personalizados",
                    "quantity": 1,
                    "unit_price": 29.90,
                    "currency_id": "BRL",
                    "description": "Acesso ilimitado a devocionais personalizados por 30 dias"
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
        
        preference_response = self.mp_client.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            raise Exception("Erro ao criar preferência de pagamento")
        
        preference = preference_response["response"]
        
        return {
            "preference_id": preference["id"],
            "init_point": preference["init_point"],
            "sandbox_init_point": preference["sandbox_init_point"]
        }
    
    def process_payment_notification(self, payment_id: str) -> Dict[str, Any]:
        """
        Processa uma notificação de pagamento do Mercado Pago
        """
        # Obter detalhes do pagamento
        payment_info = self.mp_client.payment().get(payment_id)
        
        if payment_info["status"] != 200:
            return {"status": "error", "reason": "payment_not_found"}
        
        payment_data = payment_info["response"]
        
        # Verificar se o pagamento foi aprovado
        if payment_data["status"] != "approved":
            return {"status": "ignored", "reason": "payment_not_approved"}
        
        # Extrair dados do pagamento
        external_reference = payment_data.get("external_reference")
        
        if not external_reference:
            return {"status": "error", "reason": "no_external_reference"}
        
        # O external_reference deve conter o ID do usuário
        user_id = external_reference
        
        # Atualizar assinatura no Supabase
        return self.update_user_subscription(user_id, payment_id)
    
    def update_user_subscription(self, user_id: str, payment_id: str) -> Dict[str, Any]:
        """
        Atualiza a assinatura do usuário no banco de dados
        """
        # Calcular data de validade (30 dias a partir de agora)
        valid_until = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        # Verificar se já existe assinatura
        subscription = self.supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
        
        if subscription.data and len(subscription.data) > 0:
            # Atualizar assinatura existente
            self.supabase.table("subscriptions").update({
                "is_active": True,
                "valid_until": valid_until,
                "last_payment_id": payment_id,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
        else:
            # Criar nova assinatura
            self.supabase.table("subscriptions").insert({
                "user_id": user_id,
                "is_active": True,
                "valid_until": valid_until,
                "last_payment_id": payment_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
        
        return {"status": "success", "message": "subscription_updated"}
    
    def check_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """
        Verifica o status da assinatura de um usuário
        """
        subscription = self.supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
        
        if not subscription.data or len(subscription.data) == 0:
            return {
                "is_active": False,
                "valid_until": None,
                "days_remaining": 0
            }
        
        sub_data = subscription.data[0]
        is_active = sub_data.get("is_active", False)
        valid_until = sub_data.get("valid_until")
        
        # Verificar se a assinatura expirou
        if valid_until:
            valid_until_date = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            now = datetime.utcnow()
            
            if valid_until_date < now:
                # Assinatura expirada, atualizar status
                self.supabase.table("subscriptions").update({
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("user_id", user_id).execute()
                
                is_active = False
                days_remaining = 0
            else:
                # Calcular dias restantes
                days_remaining = (valid_until_date - now).days
        else:
            days_remaining = 0
        
        return {
            "is_active": is_active,
            "valid_until": valid_until,
            "days_remaining": days_remaining
        } 