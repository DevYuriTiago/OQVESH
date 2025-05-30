-- Script de configuração do Supabase para a aplicação Devocionais Personalizados
-- Este script deve ser executado no Editor SQL do Supabase

-- ======== TABELAS ========

-- Tabela de perfis (vinculada ao auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL PRIMARY KEY,
  email TEXT NOT NULL,
  nome TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Tabela de assinaturas
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  is_active BOOLEAN DEFAULT FALSE NOT NULL,
  valid_until TIMESTAMP WITH TIME ZONE,
  last_payment_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Tabela de uso
CREATE TABLE IF NOT EXISTS public.usages (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  devotional_count INTEGER DEFAULT 0 NOT NULL,
  last_used TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Tabela de devocionais
CREATE TABLE IF NOT EXISTS public.devotionals (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  sentimento TEXT NOT NULL,
  texto TEXT NOT NULL,
  versiculos TEXT[] NOT NULL,
  reflexao TEXT,
  oracao TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- ======== SEGURANÇA (RLS) ========

-- Habilitar RLS em todas as tabelas
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devotionals ENABLE ROW LEVEL SECURITY;

-- ======== POLÍTICAS ========

-- Políticas para profiles
CREATE POLICY "Usuários podem ver seus próprios perfis"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Usuários podem atualizar seus próprios perfis"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

-- Políticas para subscriptions
CREATE POLICY "Usuários podem ver suas próprias assinaturas"
  ON public.subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "API pode criar e atualizar assinaturas"
  ON public.subscriptions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "API pode atualizar assinaturas"
  ON public.subscriptions FOR UPDATE
  USING (auth.uid() = user_id);

-- Políticas para usages
CREATE POLICY "Usuários podem ver seu próprio uso"
  ON public.usages FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "API pode criar registros de uso"
  ON public.usages FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "API pode atualizar registros de uso"
  ON public.usages FOR UPDATE
  USING (auth.uid() = user_id);

-- Políticas para devotionals
CREATE POLICY "Usuários podem ver seus próprios devocionais"
  ON public.devotionals FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Usuários podem criar seus próprios devocionais"
  ON public.devotionals FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ======== FUNÇÕES E TRIGGERS ========

-- Função para atualizar o timestamp 'updated_at'
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualização automática do campo 'updated_at' na tabela de assinaturas
CREATE TRIGGER update_subscriptions_updated_at
BEFORE UPDATE ON public.subscriptions
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- ======== CADASTRO AUTOMÁTICO DE PERFIL ========

-- Função para criar automaticamente um perfil quando um novo usuário se registra
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, nome, created_at)
  VALUES (NEW.id, NEW.email, '', NEW.created_at);
  
  INSERT INTO public.usages (user_id, devotional_count, last_used)
  VALUES (NEW.id, 0, NEW.created_at);
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger para criação automática de perfil
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.handle_new_user();

-- ======== ÍNDICES ========

-- Índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON public.subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_usages_user_id ON public.usages (user_id);
CREATE INDEX IF NOT EXISTS idx_devotionals_user_id ON public.devotionals (user_id);

-- ======== CONFIGURAÇÕES DE AUTENTICAÇÃO ========

-- Importante: Habilitar e-mail confirmação e redefinição de senha
-- Isso deve ser feito na interface do Supabase:
-- 1. Acesse Authentication > Settings
-- 2. Habilite "Enable Email Confirmations"
-- 3. Configure os templates de e-mail

-- ======== INSTRUÇÕES ADICIONAIS ========

-- Após executar este script, você deve:
-- 1. Configurar o provedor OAuth do Google se desejar autenticação com Google
-- 2. Verificar se as políticas de RLS estão funcionando corretamente
-- 3. Configurar variáveis de ambiente no seu aplicativo
-- 4. Testar se todos os endpoints estão funcionando corretamente 