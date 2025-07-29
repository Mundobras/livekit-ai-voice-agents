#!/usr/bin/env python3
"""
Endpoints para ligações SIP REAIS usando LiveKit
Sistema integrado com configuração SIP real do LiveKit
"""
import os
import json
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, HTTPException
from dotenv import load_dotenv

from livekit.api import LiveKitAPI, CreateRoomRequest
from livekit.protocol import room as room_proto

load_dotenv()
logger = logging.getLogger("real_sip_endpoints")

# Router para endpoints SIP reais
real_sip_router = APIRouter(prefix="/real-sip", tags=["Real SIP"])

# Armazenamento para ligações reais ativas
active_real_calls: Dict[str, Dict[str, Any]] = {}
real_call_history: List[Dict[str, Any]] = []

# Modelos para ligações SIP reais
class RealSipOutboundConfig(BaseModel):
    destination_number: str  # Número real para ligar
    caller_id: str = "AI_Assistant"
    initial_message: str = "Olá! Esta é uma ligação do seu assistente de IA. Como posso ajudá-lo?"
    max_duration: int = 1800  # 30 minutos
    personality: str = "professional"
    language: str = "pt-BR"
    use_livekit_sip: bool = True  # Usar SIP real do LiveKit

class RealSipInboundConfig(BaseModel):
    caller_number: str  # Número que está ligando
    destination_number: str  # Seu número que recebeu
    greeting: str = "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo?"
    personality: str = "professional"
    language: str = "pt-BR"

class RealCallStatus(BaseModel):
    call_id: str
    status: str  # "calling", "connected", "completed", "failed"
    caller_number: str
    destination_number: str
    start_time: str
    duration: int
    call_type: str  # "inbound", "outbound"
    room_name: str
    agent_pid: Optional[int] = None

def generate_real_call_id() -> str:
    """Gera ID único para ligação real"""
    return f"real_call_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

async def start_real_sip_agent(call_id: str, room_name: str, config: Dict[str, Any]) -> Optional[int]:
    """Inicia agente para ligação SIP real"""
    try:
        command = [
            "python", 
            "real_sip_integration.py",
            "--room", room_name,
            "--call-id", call_id
        ]
        
        # Variáveis de ambiente para ligação real
        env = os.environ.copy()
        env.update({
            "REAL_SIP_CALL_ID": call_id,
            "REAL_SIP_ROOM_NAME": room_name,
            "REAL_SIP_DESTINATION": config.get("destination_number", ""),
            "REAL_SIP_CALLER_ID": config.get("caller_id", "AI_Assistant"),
            "REAL_SIP_GREETING": config.get("greeting", "Olá!"),
            "REAL_SIP_PERSONALITY": config.get("personality", "professional"),
            "REAL_SIP_LANGUAGE": config.get("language", "pt-BR"),
            "REAL_SIP_ENABLED": "true"
        })
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        logger.info(f"Agente SIP REAL iniciado para call_id {call_id}, PID: {process.pid}")
        return process.pid
        
    except Exception as e:
        logger.error(f"Erro ao iniciar agente SIP real: {e}")
        return None

@real_sip_router.post("/outbound", response_model=Dict[str, Any])
async def make_real_sip_call(
    config: RealSipOutboundConfig,
    background_tasks: BackgroundTasks
):
    """
    Faz uma ligação SIP REAL usando LiveKit
    O telefone de destino vai tocar de verdade!
    """
    try:
        call_id = generate_real_call_id()
        room_name = f"real_sip_{call_id}"
        
        logger.info(f"🔥 INICIANDO LIGAÇÃO REAL: {call_id}")
        logger.info(f"📞 Ligando para: {config.destination_number}")
        logger.info(f"🆔 Caller ID: {config.caller_id}")
        
        # Criar sala no LiveKit para ligação real
        try:
            lk_api = LiveKitAPI(
                url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            
            # Metadados para ligação real
            room_metadata = {
                "type": "real_sip_outbound",
                "call_id": call_id,
                "destination_number": config.destination_number,
                "caller_id": config.caller_id,
                "real_phone_call": True,
                "sip_enabled": True,
                "created_at": datetime.now().isoformat()
            }
            
            room_request = CreateRoomRequest(
                name=room_name,
                empty_timeout=60,
                max_participants=2,  # Caller + AI Agent
                metadata=json.dumps(room_metadata)
            )
            
            room = await lk_api.room.create_room(room_request)
            logger.info(f"✅ Sala LiveKit criada para ligação real: {room_name}")
            
            # 🔥 EXECUTAR LIGAÇÃO SIP REAL USANDO CreateSIPParticipant!
            logger.info(f"🚀 Executando ligação SIP REAL...")
            
            # Usar LiveKitAPI diretamente para CreateSIPParticipant
            from livekit.api import CreateSIPParticipantRequest
            
            sip_participant_request = CreateSIPParticipantRequest(
                sip_trunk_id=os.getenv("LIVEKIT_SIP_TRUNK_ID", "default"),
                sip_call_to=config.destination_number,  # NÚMERO QUE VAI TOCAR!
                room_name=room_name,
                participant_identity=f"sip_caller_{call_id}",
                participant_name=config.caller_id,
                krisp_enabled=True,
                wait_until_answered=False,
                play_dialtone=True,
                participant_metadata=json.dumps({
                    "call_id": call_id,
                    "call_type": "outbound_real",
                    "destination": config.destination_number,
                    "timestamp": datetime.now().isoformat()
                })
            )
            
            # EXECUTAR A LIGAÇÃO REAL!
            logger.info(f"📞 FAZENDO LIGAÇÃO REAL para {config.destination_number}...")
            sip_participant = await lk_api.sip.create_sip_participant(sip_participant_request)
            
            logger.info(f"🎉 LIGAÇÃO REAL INICIADA!")
            logger.info(f"📞 SIP Participant ID: {sip_participant.participant_id}")
            logger.info(f"📞 Status: {sip_participant.sip_call_status}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar sala LiveKit: {e}")
            raise HTTPException(status_code=500, detail=f"Erro LiveKit: {str(e)}")
        
        # Configuração para ligação real
        real_config = {
            "destination_number": config.destination_number,
            "caller_id": config.caller_id,
            "greeting": config.initial_message,
            "max_duration": config.max_duration,
            "personality": config.personality,
            "language": config.language,
            "call_type": "real_outbound",
            "use_livekit_sip": True
        }
        
        # Iniciar agente para ligação real
        agent_pid = await start_real_sip_agent(call_id, room_name, real_config)
        
        # Registrar ligação real ativa
        call_info = {
            "call_id": call_id,
            "status": "calling",  # Telefone está tocando
            "call_type": "outbound",
            "caller_number": config.caller_id,
            "destination_number": config.destination_number,
            "room_name": room_name,
            "start_time": datetime.now().isoformat(),
            "agent_pid": agent_pid,
            "config": real_config,
            "real_call": True,
            "livekit_sip": True
        }
        
        active_real_calls[call_id] = call_info
        
        # Log estruturado para ligação real
        real_call_log = {
            "event": "real_sip_outbound_started",
            "call_id": call_id,
            "destination_number": config.destination_number,
            "caller_id": config.caller_id,
            "room_name": room_name,
            "agent_pid": agent_pid,
            "real_phone_call": True,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🔥 [REAL-SIP-OUTBOUND] {json.dumps(real_call_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "status": "calling",
            "message": f"🔥 LIGAÇÃO REAL iniciada para {config.destination_number}! O telefone deve estar tocando!",
            "destination_number": config.destination_number,
            "caller_id": config.caller_id,
            "agent_pid": agent_pid,
            "real_call": True,
            "livekit_sip_enabled": True
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao fazer ligação real: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na ligação real: {str(e)}")

@real_sip_router.post("/inbound", response_model=Dict[str, Any])
async def handle_real_sip_inbound(
    config: RealSipInboundConfig,
    background_tasks: BackgroundTasks
):
    """
    Processa chamada SIP REAL entrante
    Para quando alguém liga para seu número real
    """
    try:
        call_id = generate_real_call_id()
        room_name = f"real_sip_inbound_{call_id}"
        
        logger.info(f"📞 CHAMADA REAL ENTRANTE: {call_id}")
        logger.info(f"👤 De: {config.caller_number} → Para: {config.destination_number}")
        
        # Criar sala para chamada entrante real
        try:
            lk_api = LiveKitAPI(
                url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            
            room_metadata = {
                "type": "real_sip_inbound",
                "call_id": call_id,
                "caller_number": config.caller_number,
                "destination_number": config.destination_number,
                "real_phone_call": True,
                "sip_enabled": True,
                "created_at": datetime.now().isoformat()
            }
            
            room_request = CreateRoomRequest(
                name=room_name,
                empty_timeout=60,
                max_participants=2,
                metadata=json.dumps(room_metadata)
            )
            
            room = await lk_api.room.create_room(room_request)
            logger.info(f"✅ Sala criada para chamada entrante real: {room_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar sala LiveKit: {e}")
        
        # Configuração para chamada entrante real
        real_config = {
            "caller_number": config.caller_number,
            "destination_number": config.destination_number,
            "greeting": config.greeting,
            "personality": config.personality,
            "language": config.language,
            "call_type": "real_inbound",
            "use_livekit_sip": True
        }
        
        # Iniciar agente para chamada entrante real
        agent_pid = await start_real_sip_agent(call_id, room_name, real_config)
        
        # Registrar chamada entrante real
        call_info = {
            "call_id": call_id,
            "status": "connected",  # Chamada entrante já conectada
            "call_type": "inbound",
            "caller_number": config.caller_number,
            "destination_number": config.destination_number,
            "room_name": room_name,
            "start_time": datetime.now().isoformat(),
            "agent_pid": agent_pid,
            "config": real_config,
            "real_call": True,
            "livekit_sip": True
        }
        
        active_real_calls[call_id] = call_info
        
        # Log para chamada entrante real
        real_inbound_log = {
            "event": "real_sip_inbound_connected",
            "call_id": call_id,
            "caller_number": config.caller_number,
            "destination_number": config.destination_number,
            "room_name": room_name,
            "agent_pid": agent_pid,
            "real_phone_call": True,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"📞 [REAL-SIP-INBOUND] {json.dumps(real_inbound_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "status": "connected",
            "message": f"📞 Chamada REAL entrante processada: {config.caller_number}",
            "caller_number": config.caller_number,
            "destination_number": config.destination_number,
            "agent_pid": agent_pid,
            "real_call": True,
            "livekit_sip_enabled": True
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar chamada entrante real: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na chamada entrante: {str(e)}")

@real_sip_router.get("/calls", response_model=List[RealCallStatus])
async def get_active_real_calls():
    """Lista todas as ligações SIP REAIS ativas"""
    try:
        calls = []
        current_time = datetime.now()
        
        for call_id, call_info in active_real_calls.items():
            start_time = datetime.fromisoformat(call_info["start_time"])
            duration = int((current_time - start_time).total_seconds())
            
            call_status = RealCallStatus(
                call_id=call_id,
                status=call_info["status"],
                caller_number=call_info["caller_number"],
                destination_number=call_info["destination_number"],
                start_time=call_info["start_time"],
                duration=duration,
                call_type=call_info["call_type"],
                room_name=call_info["room_name"],
                agent_pid=call_info.get("agent_pid")
            )
            calls.append(call_status)
        
        logger.info(f"📊 Retornando {len(calls)} ligações REAIS ativas")
        return calls
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar ligações reais: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@real_sip_router.post("/hangup/{call_id}")
async def hangup_real_call(call_id: str):
    """Encerra uma ligação SIP REAL"""
    try:
        if call_id not in active_real_calls:
            raise HTTPException(status_code=404, detail="Ligação real não encontrada")
        
        call_info = active_real_calls[call_id]
        
        logger.info(f"📞 Encerrando ligação REAL: {call_id}")
        
        # Encerrar processo do agente
        if call_info.get("agent_pid"):
            try:
                import psutil
                process = psutil.Process(call_info["agent_pid"])
                process.terminate()
                logger.info(f"✅ Processo do agente real encerrado: PID {call_info['agent_pid']}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao encerrar processo: {e}")
        
        # Mover para histórico
        call_info["status"] = "completed"
        call_info["end_time"] = datetime.now().isoformat()
        
        start_time = datetime.fromisoformat(call_info["start_time"])
        end_time = datetime.now()
        call_info["total_duration"] = int((end_time - start_time).total_seconds())
        
        real_call_history.append(call_info)
        del active_real_calls[call_id]
        
        # Log de encerramento da ligação real
        hangup_log = {
            "event": "real_sip_call_hangup",
            "call_id": call_id,
            "duration": call_info["total_duration"],
            "caller_number": call_info["caller_number"],
            "destination_number": call_info["destination_number"],
            "call_type": call_info["call_type"],
            "real_phone_call": True,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"📞 [REAL-SIP-HANGUP] {json.dumps(hangup_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "message": f"📞 Ligação REAL encerrada: {call_info['total_duration']}s",
            "duration": call_info["total_duration"],
            "real_call": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao encerrar ligação real: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@real_sip_router.get("/status")
async def get_real_sip_status():
    """Status do sistema SIP REAL"""
    try:
        return {
            "success": True,
            "real_sip_enabled": True,
            "livekit_sip_configured": bool(os.getenv("LIVEKIT_URL")),
            "active_real_calls": len(active_real_calls),
            "total_real_history": len(real_call_history),
            "can_make_real_calls": True,
            "sip_provider": "LiveKit Native SIP",
            "supported_features": [
                "outbound_calls",
                "inbound_calls", 
                "call_recording",
                "ai_conversation",
                "call_metrics"
            ],
            "system_time": datetime.now().isoformat(),
            "message": "🔥 Sistema SIP REAL pronto para ligações!"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status SIP real: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@real_sip_router.get("/history")
async def get_real_call_history():
    """Histórico de ligações SIP REAIS"""
    try:
        sorted_history = sorted(
            real_call_history,
            key=lambda x: x.get("start_time", ""),
            reverse=True
        )
        
        return {
            "success": True,
            "total_real_calls": len(sorted_history),
            "history": sorted_history[:50],  # Últimas 50 ligações reais
            "real_calls_only": True
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar histórico real: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
