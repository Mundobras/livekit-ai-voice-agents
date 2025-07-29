#!/usr/bin/env python3
"""
Integração SIP Real com LiveKit
Sistema para fazer ligações reais usando configuração SIP do LiveKit
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions
from livekit.agents import sip
from livekit.agents.llm import (
    llm,
    ChatContext,
    ChatMessage,
    StopResponse,
)
from livekit.api import LiveKitAPI
import assemblyai
import groq

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("real_sip_integration")

class RealSipAgent(Agent):
    """Agente para ligações SIP reais via LiveKit"""
    
    def __init__(self):
        super().__init__(
            instructions="""Você é um assistente de IA para ligações telefônicas reais.
            
            PROTOCOLO PARA LIGAÇÕES REAIS:
            - Identifique-se claramente como assistente de IA
            - Seja educado e profissional
            - Mantenha respostas claras e concisas (10-30 palavras)
            - Confirme informações importantes
            - Pergunte se pode ajudar em algo mais
            
            EXEMPLO DE CONVERSA:
            "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo hoje?"
            
            REGRAS IMPORTANTES:
            - Sempre seja transparente sobre ser IA
            - Use linguagem natural e amigável
            - Evite jargões técnicos
            - Seja paciente com o usuário""",
            stt=assemblyai.STT(),
        )
        
        self.groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.call_start_time = datetime.now()
        self.sip_metadata = {}
        
        logger.info("Agente SIP Real inicializado")

    def set_real_sip_metadata(self, **kwargs):
        """Define metadados para ligação SIP real"""
        self.sip_metadata = {
            "call_id": f"real_sip_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "start_time": self.call_start_time.isoformat(),
            "call_type": "real_sip",
            **kwargs
        }
        logger.info(f"Metadados SIP Real: {self.sip_metadata}")

    async def generate_real_sip_response(self, user_message: str) -> str:
        """Gera resposta otimizada para ligações SIP reais"""
        try:
            call_duration = (datetime.now() - self.call_start_time).total_seconds()
            
            messages = [
                {
                    "role": "system",
                    "content": f"""Você está em uma ligação telefônica REAL.
                    
                    CONTEXTO:
                    - Call ID: {self.sip_metadata.get('call_id', 'unknown')}
                    - Duração: {call_duration:.0f} segundos
                    - Tipo: Ligação SIP real
                    
                    INSTRUÇÕES CRÍTICAS:
                    1. Respostas de 8-25 palavras (telefone real)
                    2. Seja claro e direto
                    3. Use linguagem natural
                    4. Confirme entendimento
                    5. Seja educado e profissional
                    
                    EXEMPLOS:
                    - "Entendi perfeitamente. Posso ajudá-lo com isso."
                    - "Claro! Vou processar essa informação agora."
                    - "Perfeito. Mais alguma coisa?"
                    """
                }
            ]
            
            # Histórico recente
            for msg in self.conversation_history[-4:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Groq otimizado para ligações reais
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                max_tokens=60,  # Resposta muito curta para telefone
                temperature=0.3,  # Mais consistente
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Atualizar histórico
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Manter histórico pequeno
            if len(self.conversation_history) > 8:
                self.conversation_history = self.conversation_history[-8:]
            
            logger.info(f"[REAL-SIP] User: {user_message}")
            logger.info(f"[REAL-SIP] AI: {ai_response}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Erro na resposta SIP real: {e}")
            return "Desculpe, tive um problema. Pode repetir, por favor?"

    async def on_user_turn_completed(self, chat_ctx: ChatContext, new_message: ChatMessage):
        """Processa fala do usuário em ligação SIP real"""
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "caller"
        
        call_duration = (datetime.now() - self.call_start_time).total_seconds()
        
        logger.info(f"[REAL-SIP-CALL] {participant_id}: {user_transcript} [{call_duration:.1f}s]")
        
        # Limite de duração para ligações reais
        if call_duration > 1800:  # 30 minutos
            await chat_ctx.respond("Obrigado pela ligação. Nosso tempo se esgotou. Tenha um ótimo dia!")
            logger.info(f"[REAL-SIP] Chamada encerrada por tempo: {call_duration:.1f}s")
            raise StopResponse()
        
        # Gerar resposta para ligação real
        ai_response = await self.generate_real_sip_response(user_transcript)
        
        # Log estruturado para ligação real
        real_sip_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "real_sip_conversation",
            "call_metadata": self.sip_metadata,
            "caller_id": participant_id,
            "user_message": user_transcript,
            "ai_response": ai_response,
            "call_duration": call_duration,
            "conversation_turns": len(self.conversation_history) // 2,
            "call_type": "real_sip_call"
        }
        
        logger.info(f"[REAL-SIP-LOG] {json.dumps(real_sip_log, ensure_ascii=False)}")
        
        # Responder na ligação real
        await chat_ctx.respond(ai_response)
        
        raise StopResponse()

async def real_sip_entrypoint(ctx: JobContext):
    """Ponto de entrada para ligações SIP reais"""
    logger.info(f"Iniciando agente SIP REAL para sala: {ctx.room.name}")
    
    # Conectar com configurações otimizadas para SIP real
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    
    # Criar agente SIP real
    agent = RealSipAgent()
    
    # Configurar metadados para ligação real
    agent.set_real_sip_metadata(
        room_name=ctx.room.name,
        livekit_sip_enabled=True,
        real_phone_call=True
    )
    
    # Iniciar sessão para ligação real
    session = AgentSession()
    await session.start(
        agent=agent,
        room=ctx.room,
        room_output_options=agents.RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=True,
            # Configurações otimizadas para telefonia real
            audio_codec="opus",
            audio_bitrate=64000,  # Qualidade telefônica
            audio_channels=1,     # Mono para SIP
            audio_sample_rate=16000,  # Padrão telefônico
        ),
    )

async def create_real_sip_call(destination_number: str, caller_id: str = None, sip_trunk_id: str = None) -> Dict[str, Any]:
    """
    Cria uma ligação SIP REAL usando LiveKit CreateSIPParticipant API
    Esta função fará o telefone de destino TOCAR de verdade!
    """
    try:
        # Configurar LiveKit API
        lk_api = LiveKitAPI(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
        )
        
        call_id = f"real_call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        room_name = f"sip_real_{call_id}"
        
        # 1. Criar sala para ligação real
        from livekit.api import CreateRoomRequest
        room_request = CreateRoomRequest(
            name=room_name,
            empty_timeout=60,
            max_participants=3,  # Caller + AI Agent + SIP Participant
            metadata=json.dumps({
                "type": "real_sip_call",
                "call_id": call_id,
                "destination": destination_number,
                "caller_id": caller_id or "AI_Assistant",
                "created_at": datetime.now().isoformat(),
                "sip_enabled": True
            })
        )
        
        room = await lk_api.room.create_room(room_request)
        logger.info(f"✅ Sala criada para ligação real: {room_name}")
        
        # 2. CRIAR SIP PARTICIPANT - ISSO FAZ O TELEFONE TOCAR!
        from livekit.api import CreateSIPParticipantRequest
        
        # Configuração do SIP Participant para ligação real
        sip_participant_request = CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id or os.getenv("LIVEKIT_SIP_TRUNK_ID", "default"),
            sip_call_to=destination_number,  # NÚMERO QUE VAI TOCAR!
            room_name=room_name,
            participant_identity=f"sip_caller_{call_id}",
            participant_name=caller_id or "AI Assistant",
            krisp_enabled=True,  # Cancelamento de ruído
            wait_until_answered=False,  # Não esperar atender para retornar
            play_dialtone=True,  # Tocar dial tone enquanto chama
            participant_metadata=json.dumps({
                "call_id": call_id,
                "call_type": "outbound_real",
                "destination": destination_number,
                "timestamp": datetime.now().isoformat()
            })
        )
        
        # 3. EXECUTAR A LIGAÇÃO REAL!
        logger.info(f"🔥 FAZENDO LIGAÇÃO REAL para {destination_number}...")
        sip_participant = await lk_api.sip.create_sip_participant(sip_participant_request)
        
        logger.info(f"🎉 LIGAÇÃO REAL INICIADA!")
        logger.info(f"📞 SIP Participant ID: {sip_participant.participant_id}")
        logger.info(f"📞 Destino: {destination_number}")
        logger.info(f"📞 Status: {sip_participant.sip_call_status}")
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "destination": destination_number,
            "status": "calling",  # Telefone está tocando!
            "message": f"🔥 LIGAÇÃO REAL iniciada para {destination_number}! Telefone deve estar tocando!",
            "livekit_room": room.name,
            "sip_participant_id": sip_participant.participant_id,
            "sip_call_status": sip_participant.sip_call_status,
            "real_phone_call": True
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar ligação SIP real: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Falha ao iniciar ligação real: {str(e)}"
        }

if __name__ == "__main__":
    # Worker para ligações SIP reais
    worker_options = WorkerOptions(
        entrypoint_fnc=real_sip_entrypoint,
        max_concurrent_jobs=10,  # Ligações simultâneas
        job_timeout=1800,        # 30 minutos por ligação
        worker_type="real_sip_agent",
    )
    
    logger.info("Iniciando worker para ligações SIP REAIS...")
    agents.cli.run_app(worker_options)
