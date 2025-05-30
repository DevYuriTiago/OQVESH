# Devocionais Personalizados

Aplicação para geração de devocionais cristãos personalizados com base em sentimentos descritos pelo usuário, utilizando IA generativa (Google Gemini) e integração com Supabase e Mercado Pago.

## 🧩 Stack Técnica

- **Interface Web:** FastAPI + Jinja2 Templates
- **Back-end:** FastAPI
- **IA:** LangChain + Google Gemini API
- **Banco e Autenticação:** Supabase (PostgreSQL + Auth)
- **Pagamentos:** Integração Mercado Pago

## 🚀 Instalação e Configuração Local

### Pré-requisitos

- Python 3.9+
- Conta no Supabase (gratuita)
- Conta no Mercado Pago (modo sandbox)
- Chave de API do Google Gemini

### Passos para Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/devocionais-personalizados.git
   cd devocionais-personalizados
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Crie um arquivo `.env` baseado no arquivo `env.example`:
   ```bash
   cp env.example .env
   ```

5. Preencha as variáveis de ambiente no arquivo `.env`:
   ```
   # Supabase
   SUPABASE_URL=https://seu-projeto.supabase.co
   SUPABASE_KEY=sua-chave-publica-anon
   SUPABASE_SERVICE_KEY=sua-chave-secreta-service-role

   # Mercado Pago
   MP_CLIENT_ID=seu-client-id
   MP_CLIENT_SECRET=seu-client-secret
   MP_ACCESS_TOKEN=seu-access-token
   MP_WEBHOOK_URL=https://seu-dominio.com/api/mp/webhook

   # Google Gemini API
   GOOGLE_API_KEY=sua-chave-api-google

   # Segurança
   SECRET_KEY=chave-secreta-para-tokens-jwt
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60

   # Configurações da aplicação
   APP_NAME=Devocionais Personalizados
   FREE_USAGE_LIMIT=5
   ```

6. Execute a aplicação:
   ```bash
   uvicorn main:app --reload
   ```

7. Acesse a aplicação em `http://localhost:8000`

## 🗃️ Configuração do Supabase

### Criação das Tabelas

Execute os seguintes comandos SQL no editor SQL do Supabase:

```sql
-- Tabela de perfis (vinculada ao auth.users)
create table public.profiles (
  id uuid references auth.users on delete cascade not null primary key,
  email text not null,
  nome text,
  created_at timestamp with time zone default now() not null
);

-- Tabela de assinaturas
create table public.subscriptions (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  is_active boolean default false not null,
  valid_until timestamp with time zone,
  last_payment_id text,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

-- Tabela de uso
create table public.usages (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  devotional_count integer default 0 not null,
  last_used timestamp with time zone default now() not null
);

-- Tabela de devocionais
create table public.devotionals (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  sentimento text not null,
  texto text not null,
  versiculos text[] not null,
  reflexao text,
  oracao text,
  created_at timestamp with time zone default now() not null
);
```

### Configuração de RLS (Row Level Security)

Execute os seguintes comandos SQL para configurar as políticas de segurança:

```sql
-- Habilitar RLS em todas as tabelas
alter table public.profiles enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usages enable row level security;
alter table public.devotionals enable row level security;

-- Políticas para profiles
create policy "Usuários podem ver seus próprios perfis"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Usuários podem atualizar seus próprios perfis"
  on public.profiles for update
  using (auth.uid() = id);

-- Políticas para subscriptions
create policy "Usuários podem ver suas próprias assinaturas"
  on public.subscriptions for select
  using (auth.uid() = user_id);

-- Políticas para usages
create policy "Usuários podem ver seu próprio uso"
  on public.usages for select
  using (auth.uid() = user_id);

-- Políticas para devotionals
create policy "Usuários podem ver seus próprios devocionais"
  on public.devotionals for select
  using (auth.uid() = user_id);

create policy "Usuários podem criar seus próprios devocionais"
  on public.devotionals for insert
  with check (auth.uid() = user_id);
```

## 💳 Configuração do Mercado Pago

1. Crie uma conta no [Mercado Pago Developers](https://developers.mercadopago.com/)
2. Obtenha suas credenciais de teste (Access Token, Client ID e Client Secret)
3. Configure o webhook URL no painel do Mercado Pago para `https://seu-dominio.com/api/mp/webhook`

### Teste com ngrok

Para testar o webhook localmente:

1. Instale o ngrok:
   ```bash
   # Windows (com pipChocolatey)
   choco install ngrok
   
   # macOS (com Homebrew)
   brew install ngrok
   ```

2. Execute o ngrok:
   ```bash
   ngrok http 8000
   ```

3. Copie a URL gerada (ex: `https://12345abcde.ngrok.io`) e configure o webhook no Mercado Pago como:
   ```
   https://meuappteste1.loca.lt/api/mp/webhook
   ```

4. Atualize a variável `MP_WEBHOOK_URL` no seu arquivo `.env`

## 🧪 Executando Testes

```bash
pytest
```

Para executar testes com cobertura:

```bash
pytest --cov=.
```

## 🚀 Deploy

### Opção 1: Deploy no Heroku

1. Instale o CLI do Heroku
2. Faça login no Heroku: `heroku login`
3. Crie uma aplicação: `heroku create devocionais-personalizados`
4. Configure as variáveis de ambiente:
   ```bash
   heroku config:set SUPABASE_URL=https://seu-projeto.supabase.co
   heroku config:set SUPABASE_KEY=sua-chave-publica-anon
   # ... configure todas as variáveis de ambiente
   ```
5. Faça deploy: `git push heroku main`

### Opção 2: Deploy no Railway

1. Faça fork deste repositório no GitHub
2. Crie uma conta no [Railway](https://railway.app/)
3. Crie um novo projeto a partir do repositório GitHub
4. Configure as variáveis de ambiente no painel do Railway
5. O deploy será feito automaticamente

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

Seu Nome - [GitHub](https://github.com/seu-usuario) 