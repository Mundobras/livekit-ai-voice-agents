# ==================== TELEPHONY ENDPOINTS ====================
# Adicione este código ao final do api_server.py antes de "if __name__ == "__main__":"

import asyncio

# Estado global para ligações
active_calls: Dict[str, Dict[str, Any]] = {}
call_logs: List[Dict[str, Any]] = []

@app.post("/telephony/inbound")
async def handle_inbound_call(call_config: TelephonyCallConfig, background_tasks: BackgroundTasks):
    """Manipula chamadas telefônicas entrantes"""
    try:
        call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Registrar ligação
        call_data = {
            "call_id": call_id,
            "type": "inbound",
            "caller_id": call_config.phone_number,
            "agent_type": call_config.agent_type,
            "status": "connecting",
            "start_time": datetime.now().isoformat(),
            "greeting_message": call_config.greeting_message,
            "max_duration": call_config.max_duration,
            "recording_enabled": call_config.recording_enabled,
            "personality": call_config.personality
        }
        
        active_calls[call_id] = call_data
        
        # Criar sala específica para a ligação
        room_name = f"call_{call_id}"
        
        # Configurar agente para telephony
        agent_config = AgentConfig(
            agent_type="telephony",
            room_name=room_name,
            personality=call_config.personality,
            features=["transcription", "telephony", "call_recording"]
        )
        
        # Iniciar agente em background
        background_tasks.add_task(start_telephony_agent, call_id, agent_config)
        
        logger.info(f"Ligação entrante iniciada: {call_id} de {call_config.phone_number}")
        
        return {
            "call_id": call_id,
            "status": "connecting",
            "room_name": room_name,
            "message": "Ligação sendo conectada"
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar ligação entrante: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

@app.post("/telephony/outbound")
async def make_outbound_call(call_request: OutboundCallRequest, background_tasks: BackgroundTasks):
    """Inicia uma ligação sainte"""
    try:
        call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Registrar ligação sainte
        call_data = {
            "call_id": call_id,
            "type": "outbound",
            "destination": call_request.destination_number,
            "agent_type": call_request.agent_type,
            "status": "initiating",
            "start_time": datetime.now().isoformat(),
            "message": call_request.message,
            "scheduled_time": call_request.scheduled_time
        }
        
        active_calls[call_id] = call_data
        
        # Criar sala para ligação sainte
        room_name = f"outbound_call_{call_id}"
        
        # Configurar agente
        agent_config = AgentConfig(
            agent_type=call_request.agent_type,
            room_name=room_name,
            personality="professional",
            features=["transcription", "telephony", "outbound_calling"]
        )
        
        # Iniciar processo de ligação em background
        background_tasks.add_task(initiate_outbound_call, call_id, call_request, agent_config)
        
        logger.info(f"Ligação sainte iniciada: {call_id} para {call_request.destination_number}")
        
        return {
            "call_id": call_id,
            "status": "initiating",
            "destination": call_request.destination_number,
            "message": "Ligação sendo iniciada"
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar ligação sainte: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

@app.get("/telephony/calls")
async def list_active_calls():
    """Lista todas as ligações ativas"""
    return {
        "active_calls": len(active_calls),
        "calls": list(active_calls.values())
    }

@app.get("/telephony/calls/{call_id}")
async def get_call_status(call_id: str):
    """Obtém status de uma ligação específica"""
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail="Ligação não encontrada")
    
    return active_calls[call_id]

@app.post("/telephony/calls/{call_id}/hangup")
async def hangup_call(call_id: str):
    """Encerra uma ligação específica"""
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail="Ligação não encontrada")
    
    try:
        call_data = active_calls[call_id]
        call_data["status"] = "ended"
        call_data["end_time"] = datetime.now().isoformat()
        
        # Calcular duração
        start_time = datetime.fromisoformat(call_data["start_time"])
        duration = (datetime.now() - start_time).total_seconds()
        call_data["duration"] = duration
        
        # Mover para logs
        call_logs.append(call_data)
        del active_calls[call_id]
        
        logger.info(f"Ligação encerrada: {call_id} (duração: {duration:.1f}s)")
        
        return {
            "message": "Ligação encerrada com sucesso",
            "call_id": call_id,
            "duration": duration
        }
        
    except Exception as e:
        logger.error(f"Erro ao encerrar ligação {call_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

@app.get("/telephony/logs")
async def get_call_logs(limit: int = 50):
    """Obtém histórico de ligações"""
    return {
        "total_calls": len(call_logs),
        "calls": call_logs[-limit:]
    }

@app.get("/telephony/metrics")
async def get_telephony_metrics():
    """Obtém métricas de telephony"""
    active_count = len(active_calls)
    total_calls = len(call_logs)
    
    # Calcular métricas
    inbound_calls = sum(1 for call in call_logs if call.get("type") == "inbound")
    outbound_calls = sum(1 for call in call_logs if call.get("type") == "outbound")
    
    avg_duration = 0
    if call_logs:
        durations = [call.get("duration", 0) for call in call_logs if call.get("duration")]
        avg_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        "active_calls": active_count,
        "total_calls": total_calls,
        "inbound_calls": inbound_calls,
        "outbound_calls": outbound_calls,
        "average_duration": round(avg_duration, 2),
        "timestamp": datetime.now().isoformat()
    }

# Funções auxiliares para telephony
async def start_telephony_agent(call_id: str, agent_config: AgentConfig):
    """Inicia agente específico para telephony"""
    try:
        active_calls[call_id]["status"] = "connected"
        
        # Usar telephony_agent.py em vez do agente padrão
        script_to_run = "telephony_agent.py"
        
        command = [
            sys.executable,
            script_to_run,
            "start",
            "--room",
            agent_config.room_name,
        ]
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        active_calls[call_id]["process"] = process
        active_calls[call_id]["agent_id"] = f"telephony_{call_id}"
        
        logger.info(f"Agente de telephony iniciado para ligação {call_id}")
        
    except Exception as e:
        logger.error(f"Erro ao iniciar agente de telephony para {call_id}: {e}")
        active_calls[call_id]["status"] = "failed"

async def initiate_outbound_call(call_id: str, call_request: OutboundCallRequest, agent_config: AgentConfig):
    """Inicia processo de ligação sainte"""
    try:
        # Aqui você integraria com Twilio ou outro provider
        # Por enquanto, simular o processo
        active_calls[call_id]["status"] = "ringing"
        
        # Simular delay de conexão
        await asyncio.sleep(2)
        
        # Iniciar agente
        await start_telephony_agent(call_id, agent_config)
        
        logger.info(f"Ligação sainte conectada: {call_id}")
        
    except Exception as e:
        logger.error(f"Erro na ligação sainte {call_id}: {e}")
        active_calls[call_id]["status"] = "failed"
