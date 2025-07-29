#!/usr/bin/env python3
"""
Agente de IA otimizado para SIP/LiveKit
Integração nativa com sistema SIP do LiveKit
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
logger = logging.getLogger("sip_voice_agent")

class SipVoiceAgent(Agent):
    """Agente otimizado para chamadas SIP via LiveKit"""
    
    def __init__(self):
        super().__init__(
            instructions="""Você é um assistente de voz inteligente para chamadas telefônicas via SIP.
            
            CARACTERÍSTICAS PARA TELEFONIA:
            - Responda de forma clara e profissional
            - Use linguagem natural e conversacional
            - Mantenha respostas entre 10-40 palavras
            - Seja direto e útil
            - Confirme informações importantes
            
            PROTOCOLO DE CHAMADA:
            1. Cumprimente educadamente
            2. Identifique-se como assistente de IA
            3. Pergunte como pode ajudar
            4. Mantenha conversa natural
            5. Encerre educadamente quando apropriado
            
            REGRAS IMPORTANTES:
            - Evite respostas muito longas
            - Use pausas naturais
            - Confirme entendimento
            - Seja paciente e prestativo""",
            stt=assemblyai.STT(),
        )
        
        # Cliente Groq para IA
        self.groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.max_history = 6  # Histórico otimizado para SIP
        
        # Metadados da chamada SIP
        self.call_start_time = datetime.now()
        self.sip_metadata = {}
        
        # Configurações SIP
        self.sip_config = {
            "greeting": "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo?",
            "max_call_duration": 1800,  # 30 minutos
            "silence_timeout": 15,  # 15 segundos
            "audio_quality": "high",
            "echo_cancellation": True
        }
        
        logger.info("Agente SIP/LiveKit inicializado")

    def set_sip_metadata(self, sip_context: Optional[Any] = None, **kwargs):
        """Define metadados da chamada SIP"""
        self.sip_metadata = {
            "call_id": f"sip_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "start_time": self.call_start_time.isoformat(),
            "sip_context": sip_context,
            **kwargs
        }
        
        if sip_context:
            # Extrair informações do contexto SIP se disponível
            if hasattr(sip_context, 'caller_id'):
                self.sip_metadata["caller_id"] = sip_context.caller_id
            if hasattr(sip_context, 'destination'):
                self.sip_metadata["destination"] = sip_context.destination
            if hasattr(sip_context, 'trunk'):
                self.sip_metadata["trunk"] = sip_context.trunk
        
        logger.info(f"Metadados SIP definidos: {self.sip_metadata}")

    def update_conversation_history(self, message: str, is_user: bool = True):
        """Atualiza histórico otimizado para SIP"""
        self.conversation_history.append({
            "role": "user" if is_user else "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "call_duration": (datetime.now() - self.call_start_time).total_seconds()
        })
        
        # Manter histórico menor para SIP (melhor performance)
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    async def generate_sip_response(self, user_message: str) -> str:
        """Gera resposta otimizada para SIP/telefonia"""
        try:
            call_duration = (datetime.now() - self.call_start_time).total_seconds()
            
            # Contexto otimizado para SIP
            messages = [
                {
                    "role": "system",
                    "content": f"""Você é um assistente de voz para chamadas telefônicas SIP.
                    
                    CONTEXTO DA CHAMADA:
                    - Call ID: {self.sip_metadata.get('call_id', 'unknown')}
                    - Duração: {call_duration:.0f} segundos
                    - Caller: {self.sip_metadata.get('caller_id', 'unknown')}
                    - Trunk: {self.sip_metadata.get('trunk', 'default')}
                    
                    INSTRUÇÕES ESPECÍFICAS PARA SIP:
                    1. Respostas entre 8-35 palavras (otimizado para telefonia)
                    2. Use linguagem clara e natural
                    3. Evite termos técnicos
                    4. Seja direto e útil
                    5. Confirme informações importantes
                    6. Use pausas naturais na fala
                    
                    EXEMPLOS DE BOAS RESPOSTAS:
                    - "Entendi perfeitamente. Posso ajudá-lo com isso agora mesmo."
                    - "Claro! Vou processar essa informação para você."
                    - "Perfeito. Mais alguma coisa que posso esclarecer?"
                    """
                }
            ]
            
            # Adicionar histórico recente (otimizado para SIP)
            for msg in self.conversation_history[-4:]:  # Últimas 2 trocas
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Mensagem atual
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Chamar Groq com configurações otimizadas para SIP
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",  # Modelo rápido
                messages=messages,
                max_tokens=80,  # Resposta curta para SIP
                temperature=0.5,  # Consistente e natural
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Atualizar histórico
            self.update_conversation_history(user_message, is_user=True)
            self.update_conversation_history(ai_response, is_user=False)
            
            # Log específico para SIP
            logger.info(f"[SIP] User: {user_message}")
            logger.info(f"[SIP] AI: {ai_response}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta SIP: {e}")
            return "Desculpe, tive um problema técnico. Pode repetir, por favor?"

    async def on_user_turn_completed(self, chat_ctx: ChatContext, new_message: ChatMessage):
        """Processa fala do usuário em chamada SIP"""
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "caller"
        
        call_duration = (datetime.now() - self.call_start_time).total_seconds()
        
        # Log específico para SIP
        logger.info(f"[SIP-CALL] Caller ({participant_id}): {user_transcript} [Duration: {call_duration:.1f}s]")
        
        # Verificar duração máxima
        if call_duration > self.sip_config["max_call_duration"]:
            await chat_ctx.respond("Obrigado pela ligação. Nossa conversa atingiu o tempo limite. Tenha um ótimo dia!")
            logger.info(f"[SIP] Chamada encerrada por tempo limite: {call_duration:.1f}s")
            raise StopResponse()
        
        # Gerar resposta otimizada para SIP
        ai_response = await self.generate_sip_response(user_transcript)
        
        # Log estruturado para SIP
        sip_log = {
            "timestamp": datetime.now().isoformat(),
            "call_metadata": self.sip_metadata,
            "caller_id": participant_id,
            "user_message": user_transcript,
            "ai_response": ai_response,
            "call_duration": call_duration,
            "conversation_turns": len(self.conversation_history) // 2,
            "sip_trunk": self.sip_metadata.get('trunk', 'default')
        }
        
        logger.info(f"[SIP-LOG] {json.dumps(sip_log, ensure_ascii=False)}")
        
        # Enviar resposta
        await chat_ctx.respond(ai_response)
        
        raise StopResponse()

    async def on_sip_call_started(self, ctx: ChatContext):
        """Executado quando chamada SIP inicia"""
        logger.info(f"[SIP] Chamada SIP iniciada: {self.sip_metadata}")
        
        # Mensagem de boas-vindas otimizada para SIP
        greeting = self.sip_config["greeting"]
        await ctx.respond(greeting)
        
        # Registrar início
        self.update_conversation_history(greeting, is_user=False)

    async def on_sip_call_ended(self, ctx: ChatContext):
        """Executado quando chamada SIP termina"""
        call_duration = (datetime.now() - self.call_start_time).total_seconds()
        
        # Log final da chamada SIP
        final_log = {
            "event": "sip_call_ended",
            "call_metadata": self.sip_metadata,
            "total_duration": call_duration,
            "total_turns": len(self.conversation_history) // 2,
            "conversation_history": self.conversation_history,
            "sip_quality": "completed"
        }
        
        logger.info(f"[SIP-END] {json.dumps(final_log, ensure_ascii=False)}")

async def sip_entrypoint(ctx: JobContext):
    """Ponto de entrada otimizado para SIP"""
    logger.info(f"Iniciando agente SIP para sala: {ctx.room.name}")
    
    # Conectar com configurações otimizadas para SIP
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Criar agente SIP
    agent = SipVoiceAgent()
    
    # Configurar metadados SIP se disponível
    sip_context = getattr(ctx, 'sip_context', None)
    if sip_context:
        agent.set_sip_metadata(
            sip_context=sip_context,
            call_type="sip_inbound",
            room_name=ctx.room.name
        )
    else:
        agent.set_sip_metadata(
            call_type="sip_room",
            room_name=ctx.room.name
        )
    
    # Iniciar sessão com configurações SIP
    session = AgentSession()
    await session.start(
        agent=agent,
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=True,
            # Configurações otimizadas para SIP
            audio_codec="opus",
            audio_bitrate=48000,  # Qualidade otimizada para telefonia
            audio_channels=1,     # Mono para SIP
        ),
    )

if __name__ == "__main__":
    # Configurações específicas para SIP
    worker_options = WorkerOptions(
        entrypoint_fnc=sip_entrypoint,
        # Otimizações para SIP
        max_concurrent_jobs=20,  # Múltiplas chamadas SIP
        job_timeout=1800,        # 30 minutos por chamada
        worker_type="sip_agent", # Identificação específica
    )
    
    logger.info("Iniciando worker SIP/LiveKit...")
    agents.cli.run_app(worker_options)
