import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions
from livekit.agents.llm import llm
from livekit.agents.llm.llm import StopResponse
from livekit.agents.llm.llm import ChatContext, ChatMessage
from livekit.agents.llm.llm import RoomOutputOptions
from livekit.agents.llm.llm import AutoSubscribe
import assemblyai
import groq

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("advanced_groq_agent")

class AdvancedGroqAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""Você é um assistente de voz avançado e versátil.
            Pode assumir diferentes personalidades e funcionalidades baseado no contexto.
            Sempre seja útil, preciso e natural em suas respostas.""",
            stt=assemblyai.STT(),
        )
        
        # Inicializar cliente Groq
        self.groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.max_history = 15
        
        # Personalidades disponíveis
        self.personalities = {
            "assistant": {
                "name": "Assistente IA",
                "tone": "profissional e amigável",
                "style": "útil e preciso",
                "system_prompt": "Você é um assistente inteligente e útil. Responda de forma clara e concisa."
            },
            "teacher": {
                "name": "Professor IA",
                "tone": "educativo e paciente",
                "style": "explicativo e didático",
                "system_prompt": "Você é um professor virtual. Explique conceitos de forma clara e didática."
            },
            "friend": {
                "name": "Amigo IA",
                "tone": "casual e descontraído",
                "style": "conversacional e empático",
                "system_prompt": "Você é um amigo virtual. Seja casual, empático e divertido nas conversas."
            },
            "coach": {
                "name": "Coach IA",
                "tone": "motivacional e energético",
                "style": "inspirador e focado",
                "system_prompt": "Você é um coach motivacional. Inspire e motive as pessoas com energia positiva."
            }
        }
        
        # Personalidade atual
        self.current_personality = "assistant"
        
        # Funcionalidades especiais
        self.special_functions = {
            "weather": self.get_weather_info,
            "time": self.get_time_info,
            "joke": self.get_joke,
            "quote": self.get_inspirational_quote,
            "calculator": self.simple_calculation,
            "translator": self.translate_text
        }
        
        # Métricas da sessão
        self.session_metrics = {
            "total_interactions": 0,
            "personality_changes": 0,
            "special_functions_used": 0,
            "session_start": datetime.now(),
            "participants": set()
        }
        
        logger.info("Agente avançado Groq inicializado com sucesso")

    def update_conversation_history(self, message: str, is_user: bool = True):
        """Atualiza o histórico de conversa"""
        self.conversation_history.append({
            "role": "user" if is_user else "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "personality": self.current_personality
        })
        
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    def detect_personality_change(self, text: str) -> Optional[str]:
        """Detecta se o usuário quer mudar a personalidade"""
        text_lower = text.lower()
        
        personality_triggers = {
            "teacher": ["professor", "ensinar", "explicar", "educativo", "aula"],
            "friend": ["amigo", "amigável", "casual", "descontraído", "conversa"],
            "coach": ["coach", "motivar", "inspirar", "energia", "motivação"],
            "assistant": ["assistente", "ajudar", "profissional", "formal"]
        }
        
        for personality, triggers in personality_triggers.items():
            if any(trigger in text_lower for trigger in triggers):
                return personality
        
        return None

    def detect_special_function(self, text: str) -> Optional[str]:
        """Detecta se o usuário quer usar uma funcionalidade especial"""
        text_lower = text.lower()
        
        function_triggers = {
            "weather": ["clima", "tempo", "temperatura", "chuva", "sol"],
            "time": ["horas", "que horas", "que dia", "data", "agora"],
            "joke": ["piada", "engraçado", "humor", "rir", "divertido"],
            "quote": ["frase", "inspiração", "motivação", "citação"],
            "calculator": ["calcular", "conta", "matemática", "soma", "multiplicar"],
            "translator": ["traduzir", "inglês", "espanhol", "idioma"]
        }
        
        for function, triggers in function_triggers.items():
            if any(trigger in text_lower for trigger in triggers):
                return function
        
        return None

    async def get_weather_info(self, location: str = "São Paulo") -> str:
        """Simula informações do clima"""
        return f"Hoje em {location} está ensolarado com temperatura de 25°C. Perfeito para um passeio!"

    async def get_time_info(self) -> str:
        """Retorna informações de data e hora"""
        now = datetime.now()
        return f"Agora são {now.strftime('%H:%M')} do dia {now.strftime('%d/%m/%Y')}."

    async def get_joke(self) -> str:
        """Retorna uma piada"""
        jokes = [
            "Por que o livro de matemática está triste? Porque tem muitos problemas!",
            "O que o zero disse para o oito? Bonito cinto!",
            "Por que o computador foi ao médico? Porque estava com vírus!"
        ]
        import random
        return random.choice(jokes)

    async def get_inspirational_quote(self) -> str:
        """Retorna uma frase inspiracional"""
        quotes = [
            "A persistência é o caminho do êxito. - Charles Chaplin",
            "O sucesso nasce do querer, da determinação e persistência. - Augusto Cury",
            "Acredite em você mesmo e tudo será possível!"
        ]
        import random
        return random.choice(quotes)

    async def simple_calculation(self, expression: str) -> str:
        """Realiza cálculos simples"""
        try:
            # Remover palavras e manter apenas números e operadores
            import re
            clean_expr = re.sub(r'[^\d\+\-\*\/\(\)\.]', '', expression)
            result = eval(clean_expr)
            return f"O resultado de {expression} é {result}"
        except:
            return "Desculpe, não consegui fazer esse cálculo. Pode ser mais específico?"

    async def translate_text(self, text: str, target_lang: str = "inglês") -> str:
        """Simula tradução de texto"""
        translations = {
            "inglês": {
                "olá": "hello",
                "obrigado": "thank you",
                "como vai": "how are you"
            },
            "espanhol": {
                "olá": "hola",
                "obrigado": "gracias",
                "como vai": "cómo estás"
            }
        }
        
        text_lower = text.lower()
        if target_lang in translations:
            for pt, translated in translations[target_lang].items():
                if pt in text_lower:
                    return f"'{text}' em {target_lang} é '{translated}'"
        
        return f"Tradução de '{text}' para {target_lang}: [Tradução simulada]"

    async def generate_response(self, user_message: str) -> str:
        """Gera resposta usando Groq com personalidade e funcionalidades especiais"""
        try:
            # Verificar mudança de personalidade
            new_personality = self.detect_personality_change(user_message)
            if new_personality and new_personality != self.current_personality:
                self.current_personality = new_personality
                self.session_metrics["personality_changes"] += 1
                logger.info(f"Personalidade alterada para: {new_personality}")

            # Verificar funcionalidade especial
            special_function = self.detect_special_function(user_message)
            if special_function and special_function in self.special_functions:
                self.session_metrics["special_functions_used"] += 1
                result = await self.special_functions[special_function](user_message)
                return result

            # Preparar contexto com personalidade atual
            personality = self.personalities[self.current_personality]
            messages = [
                {
                    "role": "system",
                    "content": f"""{personality['system_prompt']}
                    
                    Personalidade atual: {personality['name']}
                    Tom: {personality['tone']}
                    Estilo: {personality['style']}
                    
                    Regras:
                    1. Mantenha respostas curtas para conversas em tempo real
                    2. Seja natural e contextual
                    3. Use a personalidade definida consistentemente
                    4. Seja útil e preciso"""
                }
            ]
            
            # Adicionar histórico recente
            for msg in self.conversation_history[-8:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Adicionar mensagem atual
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Chamar Groq
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Atualizar histórico
            self.update_conversation_history(user_message, is_user=True)
            self.update_conversation_history(ai_response, is_user=False)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com Groq: {e}")
            return "Desculpe, tive um problema técnico. Pode repetir?"

    def get_session_summary(self) -> Dict[str, Any]:
        """Retorna resumo da sessão"""
        session_duration = datetime.now() - self.session_metrics["session_start"]
        return {
            "total_interactions": self.session_metrics["total_interactions"],
            "personality_changes": self.session_metrics["personality_changes"],
            "special_functions_used": self.session_metrics["special_functions_used"],
            "current_personality": self.current_personality,
            "session_duration_minutes": session_duration.total_seconds() / 60,
            "unique_participants": len(self.session_metrics["participants"])
        }

    async def on_user_turn_completed(self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """Processa quando o usuário termina de falar"""
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "unknown"
        
        # Atualizar métricas
        self.session_metrics["total_interactions"] += 1
        self.session_metrics["participants"].add(participant_id)
        
        # Log da transcrição
        logger.info(f"Usuário ({participant_id}): {user_transcript}")
        
        # Gerar resposta
        ai_response = await self.generate_response(user_transcript)
        
        # Log da resposta
        logger.info(f"IA ({self.current_personality}): {ai_response}")
        
        # Log estruturado
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "participant_id": participant_id,
            "user_message": user_transcript,
            "ai_response": ai_response,
            "current_personality": self.current_personality,
            "session_summary": self.get_session_summary()
        }
        
        logger.info(f"Interação avançada processada: {json.dumps(log_data, ensure_ascii=False)}")
        
        # Enviar resposta para o chat
        await chat_ctx.respond(ai_response)
        
        raise StopResponse()

async def entrypoint(ctx: JobContext):
    """Ponto de entrada do agente avançado"""
    logger.info(f"Iniciando agente avançado Groq para sala: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    session = AgentSession()
    await session.start(
        agent=AdvancedGroqAgent(),
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=True,
        ),
    )

if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 