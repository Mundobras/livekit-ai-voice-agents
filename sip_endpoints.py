#!/usr/bin/env python3
"""
Endpoints específicos para SIP/LiveKit
Integração nativa com sistema SIP do LiveKit
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
logger = logging.getLogger("sip_endpoints")

# Router para endpoints SIP
sip_router = APIRouter(prefix="/sip", tags=["SIP"])

# Armazenamento em memória para chamadas SIP ativas
active_sip_calls: Dict[str, Dict[str, Any]] = {}
sip_call_history: List[Dict[str, Any]] = []

# Modelos Pydantic para SIP
class SipInboundConfig(BaseModel):
    caller_id: str
    destination: str
    trunk: str = "default"
    greeting: str = "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo?"
    max_duration: int = 1800  # 30 minutos
    personality: str = "professional"
    language: str = "pt-BR"

class SipOutboundConfig(BaseModel):
    destination: str
    caller_id: str = "AI_Assistant"
    trunk: str = "default"
    initial_message: str = "Olá! Esta é uma ligação do seu assistente de IA."
    max_duration: int = 1800
    personality: str = "professional"
    language: str = "pt-BR"
    scheduled_time: Optional[str] = None

class SipCallStatus(BaseModel):
    call_id: str
    status: str  # "active", "ringing", "completed", "failed"
    caller_id: str
    destination: str
    start_time: str
    duration: int
    trunk: str
    room_name: str
    agent_pid: Optional[int] = None

class SipMetrics(BaseModel):
    total_calls: int
    active_calls: int
    completed_calls: int
    failed_calls: int
    average_duration: float
    total_duration: int
    calls_by_trunk: Dict[str, int]
    calls_by_hour: Dict[str, int]

def generate_sip_call_id() -> str:
    """Gera ID único para chamada SIP"""
    return f"sip_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

def create_sip_room_name(call_id: str) -> str:
    """Cria nome da sala para chamada SIP"""
    return f"sip_call_{call_id}"

async def start_sip_agent(call_id: str, room_name: str, sip_config: Dict[str, Any]) -> Optional[int]:
    """Inicia agente SIP para uma chamada específica"""
    try:
        # Comando para iniciar agente SIP
        command = [
            "python", 
            "sip_voice_agent.py",
            "--room", room_name,
            "--call-id", call_id
        ]
        
        # Adicionar configurações SIP como variáveis de ambiente
        env = os.environ.copy()
        env.update({
            "SIP_CALL_ID": call_id,
            "SIP_ROOM_NAME": room_name,
            "SIP_CALLER_ID": sip_config.get("caller_id", "unknown"),
            "SIP_DESTINATION": sip_config.get("destination", "unknown"),
            "SIP_TRUNK": sip_config.get("trunk", "default"),
            "SIP_GREETING": sip_config.get("greeting", "Olá!"),
            "SIP_MAX_DURATION": str(sip_config.get("max_duration", 1800)),
            "SIP_PERSONALITY": sip_config.get("personality", "professional"),
            "SIP_LANGUAGE": sip_config.get("language", "pt-BR")
        })
        
        # Iniciar processo do agente SIP
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        logger.info(f"Agente SIP iniciado para call_id {call_id}, PID: {process.pid}")
        return process.pid
        
    except Exception as e:
        logger.error(f"Erro ao iniciar agente SIP: {e}")
        return None

@sip_router.post("/inbound", response_model=Dict[str, Any])
async def handle_sip_inbound(
    config: SipInboundConfig,
    background_tasks: BackgroundTasks
):
    """
    Processa chamada SIP entrante
    Integração nativa com SIP do LiveKit
    """
    try:
        call_id = generate_sip_call_id()
        room_name = create_sip_room_name(call_id)
        
        logger.info(f"Processando chamada SIP entrante: {call_id}")
        logger.info(f"Caller: {config.caller_id} -> Destination: {config.destination}")
        
        # Criar sala no LiveKit para a chamada SIP
        try:
            lk_api = LiveKitAPI(
                url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            
            # Configurações específicas para SIP
            room_request = CreateRoomRequest(
                name=room_name,
                empty_timeout=60,  # Timeout rápido para SIP
                max_participants=2,  # Caller + AI Agent
                metadata=json.dumps({
                    "type": "sip_inbound",
                    "call_id": call_id,
                    "caller_id": config.caller_id,
                    "destination": config.destination,
                    "trunk": config.trunk,
                    "created_at": datetime.now().isoformat()
                })
            )
            
            room = await lk_api.room.create_room(room_request)
            logger.info(f"Sala SIP criada: {room_name}")
            
        except Exception as e:
            logger.warning(f"Erro ao criar sala LiveKit: {e}")
            # Continuar mesmo sem sala (para desenvolvimento)
        
        # Iniciar agente SIP
        sip_config_dict = {
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "greeting": config.greeting,
            "max_duration": config.max_duration,
            "personality": config.personality,
            "language": config.language
        }
        
        agent_pid = await start_sip_agent(call_id, room_name, sip_config_dict)
        
        # Registrar chamada ativa
        call_info = {
            "call_id": call_id,
            "status": "active",
            "type": "inbound",
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "room_name": room_name,
            "start_time": datetime.now().isoformat(),
            "agent_pid": agent_pid,
            "config": sip_config_dict
        }
        
        active_sip_calls[call_id] = call_info
        
        # Log estruturado para SIP
        sip_log = {
            "event": "sip_inbound_started",
            "call_id": call_id,
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "room_name": room_name,
            "agent_pid": agent_pid,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[SIP-INBOUND] {json.dumps(sip_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "status": "active",
            "message": f"Chamada SIP entrante processada: {config.caller_id}",
            "agent_pid": agent_pid,
            "sip_config": sip_config_dict
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar chamada SIP entrante: {e}")
        raise HTTPException(status_code=500, detail=f"Erro SIP: {str(e)}")

@sip_router.post("/outbound", response_model=Dict[str, Any])
async def handle_sip_outbound(
    config: SipOutboundConfig,
    background_tasks: BackgroundTasks
):
    """
    Inicia chamada SIP sainte
    Integração nativa com SIP do LiveKit
    """
    try:
        call_id = generate_sip_call_id()
        room_name = create_sip_room_name(call_id)
        
        logger.info(f"Iniciando chamada SIP sainte: {call_id}")
        logger.info(f"Destination: {config.destination} from {config.caller_id}")
        
        # Criar sala no LiveKit para chamada sainte
        try:
            lk_api = LiveKitAPI(
                url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            
            room_request = CreateRoomRequest(
                name=room_name,
                empty_timeout=60,
                max_participants=2,
                metadata=json.dumps({
                    "type": "sip_outbound",
                    "call_id": call_id,
                    "caller_id": config.caller_id,
                    "destination": config.destination,
                    "trunk": config.trunk,
                    "scheduled_time": config.scheduled_time,
                    "created_at": datetime.now().isoformat()
                })
            )
            
            room = await lk_api.room.create_room(room_request)
            logger.info(f"Sala SIP sainte criada: {room_name}")
            
        except Exception as e:
            logger.warning(f"Erro ao criar sala LiveKit: {e}")
        
        # Configuração para chamada sainte
        sip_config_dict = {
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "greeting": config.initial_message,
            "max_duration": config.max_duration,
            "personality": config.personality,
            "language": config.language,
            "call_type": "outbound"
        }
        
        # Iniciar agente SIP
        agent_pid = await start_sip_agent(call_id, room_name, sip_config_dict)
        
        # Registrar chamada ativa
        call_info = {
            "call_id": call_id,
            "status": "ringing",  # Sainte começa como "ringing"
            "type": "outbound",
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "room_name": room_name,
            "start_time": datetime.now().isoformat(),
            "agent_pid": agent_pid,
            "config": sip_config_dict
        }
        
        active_sip_calls[call_id] = call_info
        
        # Log estruturado
        sip_log = {
            "event": "sip_outbound_started",
            "call_id": call_id,
            "caller_id": config.caller_id,
            "destination": config.destination,
            "trunk": config.trunk,
            "room_name": room_name,
            "agent_pid": agent_pid,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[SIP-OUTBOUND] {json.dumps(sip_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "status": "ringing",
            "message": f"Chamada SIP sainte iniciada para: {config.destination}",
            "agent_pid": agent_pid,
            "sip_config": sip_config_dict
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar chamada SIP sainte: {e}")
        raise HTTPException(status_code=500, detail=f"Erro SIP: {str(e)}")

@sip_router.get("/calls", response_model=List[SipCallStatus])
async def get_active_sip_calls():
    """Lista todas as chamadas SIP ativas"""
    try:
        calls = []
        current_time = datetime.now()
        
        for call_id, call_info in active_sip_calls.items():
            start_time = datetime.fromisoformat(call_info["start_time"])
            duration = int((current_time - start_time).total_seconds())
            
            call_status = SipCallStatus(
                call_id=call_id,
                status=call_info["status"],
                caller_id=call_info["caller_id"],
                destination=call_info["destination"],
                start_time=call_info["start_time"],
                duration=duration,
                trunk=call_info["trunk"],
                room_name=call_info["room_name"],
                agent_pid=call_info.get("agent_pid")
            )
            calls.append(call_status)
        
        logger.info(f"Retornando {len(calls)} chamadas SIP ativas")
        return calls
        
    except Exception as e:
        logger.error(f"Erro ao listar chamadas SIP: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@sip_router.post("/hangup/{call_id}")
async def hangup_sip_call(call_id: str):
    """Encerra uma chamada SIP específica"""
    try:
        if call_id not in active_sip_calls:
            raise HTTPException(status_code=404, detail="Chamada SIP não encontrada")
        
        call_info = active_sip_calls[call_id]
        
        # Encerrar processo do agente se existir
        if call_info.get("agent_pid"):
            try:
                import psutil
                process = psutil.Process(call_info["agent_pid"])
                process.terminate()
                logger.info(f"Processo do agente SIP encerrado: PID {call_info['agent_pid']}")
            except Exception as e:
                logger.warning(f"Erro ao encerrar processo: {e}")
        
        # Mover para histórico
        call_info["status"] = "completed"
        call_info["end_time"] = datetime.now().isoformat()
        
        start_time = datetime.fromisoformat(call_info["start_time"])
        end_time = datetime.now()
        call_info["total_duration"] = int((end_time - start_time).total_seconds())
        
        sip_call_history.append(call_info)
        del active_sip_calls[call_id]
        
        # Log de encerramento
        sip_log = {
            "event": "sip_call_hangup",
            "call_id": call_id,
            "duration": call_info["total_duration"],
            "caller_id": call_info["caller_id"],
            "destination": call_info["destination"],
            "trunk": call_info["trunk"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[SIP-HANGUP] {json.dumps(sip_log, ensure_ascii=False)}")
        
        return {
            "success": True,
            "call_id": call_id,
            "message": "Chamada SIP encerrada com sucesso",
            "duration": call_info["total_duration"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao encerrar chamada SIP: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@sip_router.get("/metrics", response_model=SipMetrics)
async def get_sip_metrics():
    """Retorna métricas das chamadas SIP"""
    try:
        total_calls = len(active_sip_calls) + len(sip_call_history)
        active_calls = len(active_sip_calls)
        completed_calls = len([c for c in sip_call_history if c["status"] == "completed"])
        failed_calls = len([c for c in sip_call_history if c["status"] == "failed"])
        
        # Calcular duração média
        durations = []
        total_duration = 0
        
        for call in sip_call_history:
            if "total_duration" in call:
                durations.append(call["total_duration"])
                total_duration += call["total_duration"]
        
        # Adicionar duração das chamadas ativas
        current_time = datetime.now()
        for call in active_sip_calls.values():
            start_time = datetime.fromisoformat(call["start_time"])
            duration = int((current_time - start_time).total_seconds())
            durations.append(duration)
            total_duration += duration
        
        average_duration = sum(durations) / len(durations) if durations else 0
        
        # Chamadas por trunk
        calls_by_trunk = {}
        all_calls = list(active_sip_calls.values()) + sip_call_history
        for call in all_calls:
            trunk = call.get("trunk", "default")
            calls_by_trunk[trunk] = calls_by_trunk.get(trunk, 0) + 1
        
        # Chamadas por hora (últimas 24h)
        calls_by_hour = {}
        for call in all_calls:
            start_time = datetime.fromisoformat(call["start_time"])
            hour_key = start_time.strftime("%H:00")
            calls_by_hour[hour_key] = calls_by_hour.get(hour_key, 0) + 1
        
        metrics = SipMetrics(
            total_calls=total_calls,
            active_calls=active_calls,
            completed_calls=completed_calls,
            failed_calls=failed_calls,
            average_duration=average_duration,
            total_duration=total_duration,
            calls_by_trunk=calls_by_trunk,
            calls_by_hour=calls_by_hour
        )
        
        logger.info(f"Métricas SIP: {total_calls} total, {active_calls} ativas")
        return metrics
        
    except Exception as e:
        logger.error(f"Erro ao calcular métricas SIP: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@sip_router.get("/history")
async def get_sip_call_history():
    """Retorna histórico de chamadas SIP"""
    try:
        # Ordenar por data mais recente
        sorted_history = sorted(
            sip_call_history,
            key=lambda x: x.get("start_time", ""),
            reverse=True
        )
        
        logger.info(f"Retornando histórico de {len(sorted_history)} chamadas SIP")
        return {
            "success": True,
            "total_calls": len(sorted_history),
            "history": sorted_history[:50]  # Últimas 50 chamadas
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico SIP: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@sip_router.get("/status")
async def get_sip_status():
    """Status geral do sistema SIP"""
    try:
        return {
            "success": True,
            "sip_enabled": True,
            "livekit_connected": bool(os.getenv("LIVEKIT_URL")),
            "active_calls": len(active_sip_calls),
            "total_history": len(sip_call_history),
            "supported_codecs": ["opus", "pcmu", "pcma"],
            "max_concurrent_calls": 50,
            "system_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status SIP: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
