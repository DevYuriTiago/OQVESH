import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from main import app
from services.supabase_client import get_supabase_client
from api.auth import create_access_token

# Cliente de teste
client = TestClient(app)

# Mock para o cliente Supabase
@pytest.fixture
def mock_supabase():
    with patch("services.supabase_client.get_supabase_client") as mock:
        # Criar um mock do cliente Supabase
        supabase_mock = MagicMock()
        
        # Configurar comportamentos padrão
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        supabase_mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        supabase_mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Retornar o mock
        mock.return_value = supabase_mock
        yield supabase_mock

# Mock para o LLM
@pytest.fixture
def mock_llm():
    with patch("chains.devotional_chain.get_llm") as mock:
        llm_mock = MagicMock()
        llm_mock.return_value = MagicMock()
        mock.return_value = llm_mock
        yield llm_mock

# Mock para o chain de devocionais
@pytest.fixture
def mock_devotional_chain():
    with patch("chains.devotional_chain.generate_devotional") as mock:
        mock.return_value = {
            "texto": "Este é um devocional de teste.",
            "versiculos": ["João 3:16", "Salmos 23:1"],
            "reflexao": "Uma reflexão para teste.",
            "oracao": "Uma oração para teste."
        }
        yield mock

# Fixture para criar um token de teste
@pytest.fixture
def test_token():
    # Criar um token JWT para testes
    user_id = "test-user-id"
    return create_access_token({"sub": user_id})

# Testes de autenticação
def test_signup(mock_supabase):
    # Configurar mock para o registro
    auth_response = MagicMock()
    auth_response.user.id = "test-user-id"
    mock_supabase.auth.sign_up.return_value = auth_response
    
    # Fazer requisição de registro
    response = client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password123", "nome": "Test User"}
    )
    
    # Verificar resposta
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["user"]["email"] == "test@example.com"
    
    # Verificar se o Supabase foi chamado corretamente
    mock_supabase.auth.sign_up.assert_called_once()
    mock_supabase.table.return_value.insert.assert_called()

def test_login(mock_supabase):
    # Configurar mock para o login
    auth_response = MagicMock()
    auth_response.user.id = "test-user-id"
    mock_supabase.auth.sign_in_with_password.return_value = auth_response
    
    # Configurar mock para buscar o perfil
    profile_data = {
        "id": "test-user-id",
        "email": "test@example.com",
        "nome": "Test User",
        "created_at": datetime.utcnow().isoformat()
    }
    profile_response = MagicMock(data=[profile_data])
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = profile_response
    
    # Fazer requisição de login
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    
    # Verificar resposta
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["user"]["email"] == "test@example.com"
    
    # Verificar se o Supabase foi chamado corretamente
    mock_supabase.auth.sign_in_with_password.assert_called_once()

# Testes de geração de devocionais
def test_generate_devotional(mock_supabase, mock_devotional_chain, test_token):
    # Configurar mock para verificar assinatura
    subscription_data = {
        "id": "test-subscription-id",
        "user_id": "test-user-id",
        "is_active": True,
        "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(data=[subscription_data]),  # Para verificação de assinatura
        MagicMock(data=[{"devotional_count": 0}])  # Para verificação de uso
    ]
    
    # Fazer requisição para gerar devocional
    response = client.post(
        "/api/feelings",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"sentimento": "Estou me sentindo triste hoje"}
    )
    
    # Verificar resposta
    assert response.status_code == 200
    assert "texto" in response.json()
    assert "versiculos" in response.json()
    assert "reflexao" in response.json()
    assert "oracao" in response.json()
    
    # Verificar se o chain de devocionais foi chamado
    mock_devotional_chain.assert_called_once_with("Estou me sentindo triste hoje")

def test_generate_devotional_limit_reached(mock_supabase, mock_devotional_chain, test_token):
    # Configurar mock para verificar assinatura (inativa)
    subscription_data = {
        "id": "test-subscription-id",
        "user_id": "test-user-id",
        "is_active": False
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(data=[subscription_data]),  # Para verificação de assinatura
        MagicMock(data=[{"devotional_count": 5}])  # Para verificação de uso (limite atingido)
    ]
    
    # Fazer requisição para gerar devocional
    response = client.post(
        "/api/feelings",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"sentimento": "Estou me sentindo triste hoje"}
    )
    
    # Verificar resposta (deve ser 402 Payment Required)
    assert response.status_code == 402
    assert "subscription_required" in response.json()
    
    # Verificar que o chain de devocionais não foi chamado
    mock_devotional_chain.assert_not_called()

# Testes de status do usuário
def test_get_user_status(mock_supabase, test_token):
    # Configurar mocks para verificar assinatura e uso
    subscription_data = {
        "id": "test-subscription-id",
        "user_id": "test-user-id",
        "is_active": True,
        "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }
    usage_data = {
        "id": "test-usage-id",
        "user_id": "test-user-id",
        "devotional_count": 3
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(data=[subscription_data]),  # Para verificação de assinatura
        MagicMock(data=[usage_data])  # Para verificação de uso
    ]
    
    # Fazer requisição para obter status do usuário
    response = client.get(
        "/api/status",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    # Verificar resposta
    assert response.status_code == 200
    assert response.json()["assinatura_ativa"] is True
    assert response.json()["usos_restantes"] == "ilimitado"
    assert response.json()["validade"] is not None 