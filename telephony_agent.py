#!/usr/bin/env python3
"""
Agente de IA para Ligações Telefônicas com LiveKit
Suporta chamadas entrantes e saintes via SIP/Twilio
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, RoomOutputOptions, AutoSubscribe
from livekit.agents import sip
from livekit.agents.llm import (
    llm,
    ChatContext,
    ChatMessage,
    StopResponse,
)
import assemblyai
import groq

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("telephony_agent")

class TelephonyVoiceAgent(Agent):
    """Agente especializado para ligações telefônicas"""
    
    def __init__(self):
        super().__init__(
            instructions="""Você é um assistente de voz inteligente para ligações telefônicas.
            
            CARACTERÍSTICAS IMPORTANTES:
            - Responda de forma natural e profissional
            - Mantenha respostas curtas e claras para telefonia
            - Use linguagem adequada para conversas telefônicas
            - Seja educado e prestativo
            - Identifique-se quando necessário
            
            REGRAS PARA TELEFONIA:
            1. Sempre cumprimente adequadamente no início da ligação
            2. Mantenha respostas entre 10-30 segundos
            3. Confirme informações importantes
            4. Ofereça ajuda de forma proativa
            5. Encerre a ligação educadamente quando apropriado""",
            stt=assemblyai.STT(),
        )
        
        # Inicializar cliente Groq
        self.groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.max_history = 8  # Histórico menor para telefonia
        self.call_start_time = datetime.now()
        self.call_metadata = {}
        
        # Configurações específicas para telefonia
        self.telephony_config = {
            "greeting_message": "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo hoje?",
            "max_call_duration": 1800,  # 30 minutos
            "silence_timeout": 10,  # 10 segundos de silêncio
            "auto_hangup": True,
            "call_recording": True
        }
        
        logger.info("Agente de telephony inicializado com sucesso")

    def set_call_metadata(self, caller_id: str, call_type: str = "inbound", **kwargs):
        """Define metadados da ligação"""
        self.call_metadata = {
            "caller_id": caller_id,
            "call_type": call_type,
            "start_time": self.call_start_time.isoformat(),
            "agent_id": f"telephony_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            **kwargs
        }
        logger.info(f"Metadados da ligação definidos: {self.call_metadata}")

    def update_conversation_history(self, message: str, is_user: bool = True):
        """Atualiza o histórico de conversa"""
        self.conversation_history.append({
            "role": "user" if is_user else "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "call_duration": (datetime.now() - self.call_start_time).total_seconds()
        })
        
        # Manter histórico menor para telefonia
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    async def generate_telephony_response(self, user_message: str) -> str:
        """Gera resposta otimizada para telefonia"""
        try:
            # Preparar contexto específico para telefonia
            messages = [
                {
                    "role": "system",
                    "content": f"""Você é um assistente de voz para ligações telefônicas.
                    
                    CONTEXTO DA LIGAÇÃO:
                    - Tipo: {self.call_metadata.get('call_type', 'unknown')}
                    - Duração: {(datetime.now() - self.call_start_time).total_seconds():.0f} segundos
                    - Caller ID: {self.call_metadata.get('caller_id', 'unknown')}
                    
                    INSTRUÇÕES ESPECÍFICAS:
                    1. Respostas entre 5-25 palavras (ideal para telefonia)
                    2. Use linguagem clara e natural
                    3. Evite jargões técnicos
                    4. Seja direto e útil
                    5. Confirme informações importantes"""
                }
            ]
            
            # Adicionar histórico recente
            for msg in self.conversation_history[-4:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Adicionar mensagem atual
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Chamar Groq com configurações otimizadas para telefonia
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                max_tokens=100,
                temperature=0.6,
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Atualizar histórico
            self.update_conversation_history(user_message, is_user=True)
            self.update_conversation_history(ai_response, is_user=False)
            
            logger.info(f"[CALL] User: {user_message}")
            logger.info(f"[CALL] AI: {ai_response}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta para telefonia: {e}")
            return "Desculpe, tive um problema técnico. Pode repetir?"

    async def on_user_turn_completed(self, chat_ctx: ChatContext, new_message: ChatMessage):
        """Processa quando o usuário termina de falar na ligação"""
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "caller"
        
        # Log específico para telefonia
        call_duration = (datetime.now() - self.call_start_time).total_seconds()
        logger.info(f"[TELEPHONY] Caller ({participant_id}): {user_transcript} [Duration: {call_duration:.1f}s]")
        
        # Verificar duração máxima da ligação
        if call_duration > self.telephony_config["max_call_duration"]:
            await chat_ctx.respond("Desculpe, nossa ligação atingiu o tempo máximo. Obrigado por entrar em contato!")
            logger.info(f"[TELEPHONY] Ligação encerrada por tempo limite: {call_duration:.1f}s")
            raise StopResponse()
        
        # Gerar resposta otimizada para telefonia
        ai_response = await self.generate_telephony_response(user_transcript)
        
        # Log estruturado para telefonia
        call_log = {
            "timestamp": datetime.now().isoformat(),
            "call_metadata": self.call_metadata,
            "caller_id": participant_id,
            "user_message": user_transcript,
            "ai_response": ai_response,
            "call_duration": call_duration,
            "conversation_turns": len(self.conversation_history) // 2
        }
        
        logger.info(f"[TELEPHONY_LOG] {json.dumps(call_log, ensure_ascii=False)}")
        
        # Enviar resposta
        await chat_ctx.respond(ai_response)
        
        raise StopResponse()

    async def on_call_started(self, ctx: ChatContext):
        """Executado quando a ligação inicia"""
        logger.info(f"[TELEPHONY] Ligação iniciada: {self.call_metadata}")
        
        # Enviar mensagem de boas-vindas
        greeting = self.telephony_config["greeting_message"]
        await ctx.respond(greeting)
        
        # Log do início da ligação
        self.update_conversation_history(greeting, is_user=False)

    async def on_call_ended(self, ctx: ChatContext):
        """Executado quando a ligação termina"""
        call_duration = (datetime.now() - self.call_start_time).total_seconds()
        
        # Log final da ligação
        final_log = {
            "event": "call_ended",
            "call_metadata": self.call_metadata,
            "total_duration": call_duration,
            "total_turns": len(self.conversation_history) // 2,
            "conversation_history": self.conversation_history
        }
        
        logger.info(f"[TELEPHONY_END] {json.dumps(final_log, ensure_ascii=False)}")

async def telephony_entrypoint(ctx: JobContext):
    """Ponto de entrada para agente de telephony"""
    logger.info(f"Iniciando agente de telephony para sala: {ctx.room.name}")
    
    # Conectar com configurações específicas para telephony
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Criar agente de telephony
    agent = TelephonyVoiceAgent()
    
    # Configurar metadados da ligação se disponível
    if hasattr(ctx, 'sip_context'):
        sip_ctx = ctx.sip_context
        agent.set_call_metadata(
            caller_id=sip_ctx.caller_id,
            call_type="inbound",
            sip_trunk=sip_ctx.trunk,
            destination=sip_ctx.destination
        )
    
    # Iniciar sessão
    session = AgentSession()
    await session.start(
        agent=agent,
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=True,
            # Configurações específicas para telefonia
            audio_codec="opus",
            audio_bitrate=64000,  # Bitrate otimizado para telefonia
        ),
    )

if __name__ == "__main__":
    # Configurações específicas para telephony
    worker_options = WorkerOptions(
        entrypoint_fnc=telephony_entrypoint,
        # Configurações de worker otimizadas para telefonia
        max_concurrent_jobs=10,  # Múltiplas ligações simultâneas
        job_timeout=1800,  # 30 minutos por ligação
    )
    
    agents.cli.run_app(worker_options)
