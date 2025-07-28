import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
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
logger = logging.getLogger("groq_voice_agent")

class GroqVoiceAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""Você é um assistente de voz inteligente e útil. 
            Responda de forma natural, concisa e amigável. 
            Mantenha as respostas curtas para conversas em tempo real.
            Use linguagem natural e evite ser muito formal.""",
            stt=assemblyai.STT(),
        )
        
        # Inicializar cliente Groq
        self.groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.max_history = 10  # Manter apenas as últimas 10 mensagens
        
        # Configurações do agente
        self.agent_personality = {
            "name": "Assistente IA",
            "tone": "amigável e profissional",
            "language": "português brasileiro",
            "response_style": "conciso e natural"
        }
        
        logger.info("Agente de voz Groq inicializado com sucesso")

    def update_conversation_history(self, message: str, is_user: bool = True):
        """Atualiza o histórico de conversa"""
        self.conversation_history.append({
            "role": "user" if is_user else "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Manter apenas as últimas mensagens
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    async def generate_response(self, user_message: str) -> str:
        """Gera resposta usando Groq"""
        try:
            # Preparar contexto da conversa
            messages = [
                {
                    "role": "system",
                    "content": f"""Você é {self.agent_personality['name']}, um assistente de voz inteligente.
                    Características:
                    - Tom: {self.agent_personality['tone']}
                    - Idioma: {self.agent_personality['language']}
                    - Estilo: {self.agent_personality['response_style']}
                    
                    Regras importantes:
                    1. Mantenha respostas curtas e naturais para conversas em tempo real
                    2. Seja útil e preciso
                    3. Use linguagem coloquial quando apropriado
                    4. Evite respostas muito longas ou complexas"""
                }
            ]
            
            # Adicionar histórico recente
            for msg in self.conversation_history[-6:]:  # Últimas 3 trocas
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
                model="llama3-8b-8192",  # Modelo rápido do Groq
                messages=messages,
                max_tokens=150,  # Resposta curta para tempo real
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

    def analyze_user_intent(self, text: str) -> Dict[str, Any]:
        """Análise básica da intenção do usuário"""
        text_lower = text.lower()
        
        intents = {
            "greeting": ["oi", "olá", "bom dia", "boa tarde", "boa noite", "hello"],
            "farewell": ["tchau", "adeus", "até logo", "até mais", "bye"],
            "help": ["ajuda", "help", "como usar", "o que você faz"],
            "weather": ["clima", "tempo", "temperatura", "chuva", "sol"],
            "time": ["horas", "que horas", "que dia", "data"],
            "joke": ["piada", "engraçado", "humor", "rir"]
        }
        
        detected_intent = "general"
        for intent, keywords in intents.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_intent = intent
                break
        
        return {
            "intent": detected_intent,
            "confidence": 0.8,
            "keywords": [word for word in text_lower.split() if len(word) > 3]
        }

    async def on_user_turn_completed(self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """Processa quando o usuário termina de falar"""
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "unknown"
        
        # Log da transcrição
        logger.info(f"Usuário ({participant_id}): {user_transcript}")
        
        # Análise da intenção
        intent_analysis = self.analyze_user_intent(user_transcript)
        
        # Gerar resposta
        ai_response = await self.generate_response(user_transcript)
        
        # Log da resposta
        logger.info(f"IA: {ai_response}")
        
        # Log estruturado
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "participant_id": participant_id,
            "user_message": user_transcript,
            "ai_response": ai_response,
            "intent": intent_analysis,
            "conversation_length": len(self.conversation_history)
        }
        
        logger.info(f"Interação processada: {json.dumps(log_data, ensure_ascii=False)}")
        
        # Enviar resposta para o chat
        await chat_ctx.respond(ai_response)
        
        raise StopResponse()

async def entrypoint(ctx: JobContext):
    """Ponto de entrada do agente"""
    logger.info(f"Iniciando agente de voz Groq para sala: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    session = AgentSession()
    await session.start(
        agent=GroqVoiceAgent(),
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=True,  # Habilitar áudio para respostas
        ),
    )

if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 