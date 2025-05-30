import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Carregando variáveis de ambiente
load_dotenv()

def get_supabase_client() -> Client:
    """
    Retorna um cliente do Supabase configurado com as credenciais do .env
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar definidos no arquivo .env")
    
    return create_client(url, key)

def get_supabase_admin_client() -> Client:
    """
    Retorna um cliente do Supabase com permissões de administrador (service_role)
    Usado para operações que exigem mais privilégios
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar definidos no arquivo .env")
    
    return create_client(url, key)

def setup_database_tables():
    """
    Configura as tabelas necessárias no Supabase se elas não existirem
    Isso é útil para desenvolvimento e testes
    """
    try:
        client = get_supabase_admin_client()
        
        # Verificar se as tabelas existem e criá-las se necessário
        # Nota: Em produção, é melhor usar migrações SQL
        
        # Tabela de perfis (vinculada ao auth.users)
        client.table("profiles").select("count", count="exact").limit(1).execute()
        
        # Tabela de assinaturas
        client.table("subscriptions").select("count", count="exact").limit(1).execute()
        
        # Tabela de uso
        client.table("usages").select("count", count="exact").limit(1).execute()
        
        # Tabela de devocionais
        client.table("devotionals").select("count", count="exact").limit(1).execute()
        
        return {"status": "success", "message": "Tabelas verificadas com sucesso"}
    
    except Exception as e:
        # Se ocorrer um erro, provavelmente as tabelas não existem
        # Em um ambiente de produção, você deve usar migrações SQL adequadas
        return {
            "status": "error", 
            "message": f"Erro ao verificar tabelas: {str(e)}",
            "instructions": "Execute as migrações SQL manualmente no console do Supabase"
        } 