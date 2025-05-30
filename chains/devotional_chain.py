import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
from typing import Dict, Any, List
import threading
import queue

# Carregando variáveis de ambiente
load_dotenv()

# Configurar API do Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class DevotionalChain:
    def __init__(self):
        """Initialize the DevotionalChain with Gemini model"""
        # Configure the model
        self.model_name = "gemini-2.0-flash"
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 1024,
            }
        )
        
        # Create the prompt template
        self.template = """
Você é um pastor evangélico experiente, com sólida base bíblica fundamentada nos ensinamentos do Ministério Verbo da Vida(não precisa informar isso no output). Sua missão é gerar um devocional personalizado e inspirado, com base no sentimento descrito abaixo por um cristão:

Sentimento: "{sentimento}"

Siga rigorosamente o seguinte formato:
obs: não precisa informar que é do ministério verbo da vida e sempre que for se direcionar se direcione como primeira pessoa do plural (nós).

Se o sentimento foi bom inicie com: "Que bom que você esta se sentindo assim! (ou variações que digam a mesma coisa)"

Se o sentimento foi ruim inicie com: "Uma pena que você se sente assim, mas tenho certeza que Deus irá mudar isso! (ou variações que digam a mesma coisa)"

1. **Versículo(s) chave:** Escolha 1 ou 2 versículos principais diretamente relacionados ao sentimento informado. Esses versículos devem servir de alicerce para todo o conteúdo devocional a seguir.

2. **Devocional:** Desenvolva uma reflexão profunda, espiritual e bíblica, conectando o(s) versículo(s) chave ao sentimento da pessoa. cite tambem, citações de escritores reconhecidos no ministério verbo da vida, baseados no sentimento. Se necessário, cite outros versículos de apoio, desde que se conectem diretamente ao versículo chave e reforcem a mensagem. Mantenha uma linha lógica e coerente com a Palavra.

3. **Aplicação prática:** Apresente uma breve sugestão de como o leitor pode aplicar a mensagem do devocional em sua vida diária, de forma objetiva, realista e alinhada à fé cristã.

4. **Oração final:** Elabore uma oração conclusiva que resuma os aprendizados do devocional, reafirme as promessas da Palavra e fortaleça a fé do leitor e use de uma linguagem mais simples e humana, inclua uma declaração de fé com base no sentimento.

5. **Aprofundamento:** Dê sugestões de versiculos para que o leitor possa aprofundar o conhecimento no tema abordado pelo devocional.

Estilo e tom:
- Use uma linguagem acolhedora, compassiva, fiel à Palavra de Deus e inspiradora e simples.
- Evite termos técnicos ou complexos. Seja claro, direto e pastoral.
- Toda a estrutura deve manter um tom de encorajamento e edificação pessoal.

Importante:
- Todo o conteúdo deve girar em torno do versículo chave selecionado.

Formate sua resposta para que eu possa facilmente extrair as seguintes informações em um formato JSON:
- texto: o texto completo do devocional
- versiculos: lista de versículos citados (com referência)
- reflexao: a reflexão principal do devocional
- oracao: a oração final
"""
    
    async def generate_devotional_async(self, sentimento: str) -> dict:
        """Generate a devotional based on the user's feeling with retry mechanism"""
        # Format the prompt with the user's feeling
        prompt = self.template.format(sentimento=sentimento)
        
        # Configurações de retry
        max_retries = 5
        retry_delay = 2  # segundos
        timeout = 60  # segundos por tentativa
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Tentativa {attempt} de gerar devocional...")
                
                # Gerar o conteúdo de forma assíncrona
                response = await self.model.generate_content_async(prompt)
                result = response.text
                
                print(f"Devocional gerado com sucesso na tentativa {attempt}")
                
                # Extract structured data from the result
                parsed_result = self.extract_structured_data(result, sentimento)
                
                return parsed_result
            except asyncio.TimeoutError:
                print(f"Timeout na tentativa {attempt} de {max_retries}")
                if attempt < max_retries:
                    # Esperar antes de tentar novamente
                    await asyncio.sleep(retry_delay)
                    # Aumentar o delay para a próxima tentativa
                    retry_delay *= 1.5
                else:
                    raise Exception(f"Tempo esgotado após {max_retries} tentativas de gerar o devocional")
            except Exception as e:
                print(f"Erro na tentativa {attempt}: {e}")
                # Se for o último retry, propagar o erro
                if attempt == max_retries:
                    raise Exception(f"Erro ao gerar devocional após {max_retries} tentativas: {str(e)}")
                # Esperar antes de tentar novamente
                await asyncio.sleep(retry_delay)
                # Aumentar o delay para a próxima tentativa
                retry_delay *= 1.5
    
    # Função síncrona que gera o devocional usando abordagem de thread separada com queue para retornar resultado
    def generate_devotional_sync(self, sentimento: str) -> Dict[str, Any]:
        """Generate devotional in a synchronous way using a separate thread"""
        result_queue = queue.Queue()
        error_queue = queue.Queue()
        
        # Função para executar em uma thread separada
        def run_in_thread():
            try:
                # Criar um novo event loop para a thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Executar a coroutine e colocar o resultado na fila
                    result = loop.run_until_complete(self.generate_devotional_async(sentimento))
                    result_queue.put(result)
                finally:
                    # Finalizar tarefas pendentes e fechar o loop
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    if pending:
                        # Executar até que todas as tarefas sejam canceladas
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    
                    loop.close()
            except Exception as e:
                # Colocar o erro na fila de erros
                error_queue.put(e)
        
        # Criar e iniciar a thread
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()  # Esperar a thread terminar
        
        # Verificar se houve erro
        if not error_queue.empty():
            raise error_queue.get()
        
        # Obter o resultado da fila
        if not result_queue.empty():
            return result_queue.get()
        
        # Se não tiver resultado nem erro, usar método síncrono como fallback
        print("Usando fallback síncrono para gerar devocional")
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 1024,
            }
        )
        prompt = self.template.format(sentimento=sentimento)
        response = model.generate_content(prompt)
        result = response.text
        return self.extract_structured_data(result, sentimento)
    
    def extract_structured_data(self, text: str, sentimento: str) -> Dict[str, Any]:
        """Extract structured data from the devotional text"""
        try:
            # Try to extract JSON if present
            json_str = self.extract_json_from_text(text)
            try:
                devotional_data = json.loads(json_str)
                
                # Ensure all required fields are present
                required_fields = ["texto", "versiculos", "reflexao", "oracao"]
                for field in required_fields:
                    if field not in devotional_data:
                        devotional_data[field] = ""
                
                # Ensure versiculos is a list
                if not isinstance(devotional_data["versiculos"], list):
                    devotional_data["versiculos"] = [devotional_data["versiculos"]]
                
                return devotional_data
            except json.JSONDecodeError:
                # If JSON parsing fails, use heuristic parsing
                pass
        except Exception:
            # Continue with heuristic parsing if any error occurs
            pass
        
        # Extract structured data using heuristics
        return self.extract_devotional_from_text(text)
    
    def extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text that may contain other information"""
        # Look for JSON patterns
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            json_text = text[json_start:json_end+1]
            return json_text
        
        # If no JSON format found, return the original text
        return text
    
    def extract_devotional_from_text(self, text: str) -> Dict[str, Any]:
        """Extract devotional information from unstructured text"""
        lines = text.split("\n")
        texto = text
        versiculos = self.extract_verses_from_text(text)
        reflexao = ""
        oracao = ""
        
        # Extract reflection and prayer using simple heuristics
        in_oracao = False
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Identify prayer section
            if "oração final" in line_lower or "oremos" in line_lower or "vamos orar" in line_lower:
                in_oracao = True
                oracao = "\n".join(lines[i:])
                break
        
        # If no prayer section identified, use the last few lines
        if not oracao:
            for i, line in enumerate(lines):
                if "oração" in line.lower():
                    oracao = "\n".join(lines[i:])
                    break
            
            # If still no prayer found, use last lines
            if not oracao and len(lines) > 3:
                oracao = "\n".join(lines[-3:])
        
        # Extract reflection (look for "Devocional" or "Reflexão" headers)
        for i, line in enumerate(lines):
            if "devocional:" in line.lower() or "reflexão:" in line.lower() or "**devocional:**" in line.lower():
                # Find end of reflection (next section)
                end_idx = len(lines)
                for j in range(i+1, len(lines)):
                    if "**aplicação" in lines[j].lower() or "**oração" in lines[j].lower():
                        end_idx = j
                        break
                
                reflexao = "\n".join(lines[i+1:end_idx])
                break
        
        # If no reflection found, use a middle section of text
        if not reflexao:
            if len(lines) > 10:
                # Try to find a reasonable section in the middle
                for i, line in enumerate(lines):
                    if i > len(lines) // 3 and i < (2 * len(lines) // 3):
                        if len(line) > 50:  # Long line likely part of main content
                            reflexao = line
                            break
            
            # If still no reflection, use a chunk from the middle
            if not reflexao:
                third = len(lines) // 3
                reflexao = "\n".join(lines[third:2*third])
        
        return {
            "texto": texto,
            "versiculos": versiculos,
            "reflexao": reflexao,
            "oracao": oracao
        }
    
    def extract_verses_from_text(self, text: str) -> List[str]:
        """Extract biblical references from text"""
        # Pattern for common Bible references
        pattern = r'([1-3]?\s*[A-ZÀ-Úa-zà-ú]+)\s+(\d+)[:]\s*(\d+)(?:\s*[-]\s*(\d+))?'
        
        matches = re.findall(pattern, text)
        verses = []
        
        for match in matches:
            book, chapter, verse_start, verse_end = match
            
            if verse_end:
                verses.append(f"{book} {chapter}:{verse_start}-{verse_end}")
            else:
                verses.append(f"{book} {chapter}:{verse_start}")
        
        return verses

# Create a singleton instance
devotional_chain_instance = DevotionalChain()

# Função assíncrona para ser usada em contextos assíncronos (como FastAPI)
async def generate_devotional_async(sentimento: str) -> Dict[str, Any]:
    """
    Async function for use in async contexts like FastAPI
    """
    return await devotional_chain_instance.generate_devotional_async(sentimento)

def generate_devotional(sentimento: str) -> Dict[str, Any]:
    """
    Synchronous function for backward compatibility
    """
    try:
        # Tentar o método síncrono com thread separada
        return devotional_chain_instance.generate_devotional_sync(sentimento)
    except Exception as e:
        # Format and re-raise the exception with a helpful message
        error_message = str(e)
        print(f"Erro ao gerar devocional: {error_message}")
        raise Exception(f"Erro ao gerar devocional: {error_message}") 