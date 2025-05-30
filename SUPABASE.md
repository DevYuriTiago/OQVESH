# Configuração do Supabase

Este guia detalha como configurar o Supabase para a aplicação Devocionais Personalizados, incluindo autenticação, banco de dados e segurança.

## Índice

1. [Criar Projeto](#1-criar-projeto)
2. [Configurar Autenticação](#2-configurar-autenticação)
3. [Executar Scripts SQL](#3-executar-scripts-sql)
4. [Configurar OAuth (Google)](#4-configurar-oauth-google)
5. [Obter Credenciais](#5-obter-credenciais)
6. [Verificar RLS](#6-verificar-row-level-security-rls)
7. [Solução de Problemas](#7-solução-de-problemas)

## 1. Criar Projeto

1. Acesse [supabase.com](https://supabase.com/) e faça login ou crie uma conta
2. Clique em "New Project"
3. Preencha as informações:
   - **Nome do projeto**: Devocionais-Personalizados (ou o nome que preferir)
   - **Senha do banco de dados**: Crie uma senha forte
   - **Região**: Escolha a região mais próxima à sua localização
4. Clique em "Create new project"
5. Aguarde a criação do projeto (pode levar alguns minutos)

## 2. Configurar Autenticação

1. No menu lateral, vá para **Authentication**
2. Em **Settings**, configure:
   - **Site URL**: URL do seu site em produção (para desenvolvimento, pode usar `http://localhost:8000`)
   - **Redirect URLs**: Adicione `http://localhost:8000/callback` para desenvolvimento
   - **Enable Email Confirmations**: Você pode desativar para desenvolvimento, mas em produção é recomendado ativar
   - **Enable Email Signup**: Mantenha ativado
   - **Customize email templates**: Personalize os templates de email conforme necessário

## 3. Executar Scripts SQL

1. No menu lateral, vá para **SQL Editor**
2. Clique em "New Query"
3. Copie e cole o conteúdo do arquivo `supabase_setup.sql` do projeto
4. Clique em "Run" para executar o script
5. Verifique se não houve erros na execução

## 4. Configurar OAuth (Google)

Para habilitar login com Google:

1. No menu lateral, vá para **Authentication**
2. Em **Providers**, encontre **Google**
3. Ative o toggle para habilitar
4. Você precisará de **Client ID** e **Client Secret** do Google:
   
   ### Obter credenciais do Google:
   1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
   2. Crie um novo projeto ou use um existente
   3. Vá para **APIs & Services > Credentials**
   4. Clique em **Create Credentials > OAuth client ID**
   5. Selecione **Web application**
   6. Adicione URLs de redirecionamento autorizados:
      - `https://[SEU-PROJETO].supabase.co/auth/v1/callback`
   7. Copie o **Client ID** e **Client Secret** gerados
   
5. Cole o Client ID e Client Secret no Supabase
6. Salve as alterações

## 5. Obter Credenciais

Você precisará das seguintes credenciais para configurar sua aplicação:

1. No menu lateral, vá para **Project Settings**
2. Em **API**, encontre:
   - **URL**: Valor para `SUPABASE_URL` no arquivo `.env`
   - **anon/public key**: Valor para `SUPABASE_KEY` no arquivo `.env`
   - **service_role key**: Valor para `SUPABASE_SERVICE_KEY` no arquivo `.env` (mantenha esta chave segura!)

## 6. Verificar Row Level Security (RLS)

Para verificar se as políticas RLS foram aplicadas corretamente:

1. No menu lateral, vá para **Table Editor**
2. Selecione uma tabela (ex: profiles)
3. Vá para a aba **Policies**
4. Verifique se as políticas criadas estão listadas corretamente
5. Repita para todas as tabelas

## 7. Solução de Problemas

### Erro ao criar tabelas ou políticas

Se você encontrar erros ao executar o script SQL:

1. Verifique se não há tabelas ou políticas conflitantes
2. Execute o script em partes, começando pelas tabelas, depois RLS, e depois políticas
3. Verifique os logs de erro no SQL Editor

### Problemas de autenticação

Se os usuários não conseguirem se autenticar:

1. Verifique se as configurações de email estão corretas
2. Certifique-se de que as URLs de redirecionamento estão configuradas corretamente
3. Verifique se as chaves da API estão corretas no arquivo `.env`

### Problemas de permissão de acesso aos dados

Se os usuários não conseguirem acessar seus dados:

1. Verifique se as políticas RLS estão ativadas e configuradas corretamente
2. Verifique se os usuários estão autenticados corretamente
3. Use o SQL Editor para verificar diretamente os dados das tabelas e confirmar que existem 