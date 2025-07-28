import os
import json
import logging
import subprocess
import sys
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from livekit import api, rtc

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

app = FastAPI(
    title="LiveKit AI Voice Agents API",
    description="API para gerenciar agentes de voz por IA usando Groq + LiveKit",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", status_code=200)
async def health_check():
    """
    Health check endpoint for Railway.
    """
    return {"status": "ok", "message": "API is healthy"}

# Modelos Pydantic
class AgentConfig(BaseModel):
    agent_type: str  # "basic", "advanced", "groq", "advanced_groq"
    room_name: str
    personality: Optional[str] = "assistant"
    features: Optional[List[str]] = []

class AgentStatus(BaseModel):
    agent_id: str
    status: str
    room_name: str
    agent_type: str
    start_time: str
    metrics: Dict[str, Any]

class ConversationMessage(BaseModel):
    participant_id: str
    message: str
    timestamp: str
    agent_response: Optional[str] = None

# Estado global da aplicação
active_agents: Dict[str, Dict[str, Any]] = {}
conversation_logs: List[Dict[str, Any]] = []

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "LiveKit AI Voice Agents API",
        "version": "1.0.0",
        "status": "running",
        "active_agents": len(active_agents)
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_agents": len(active_agents),
        "total_conversations": len(conversation_logs)
    }

@app.post("/agents/start")
async def start_agent(agent_config: AgentConfig, background_tasks: BackgroundTasks):
    """Inicia um novo agente, criando a sala se não existir."""
    try:
        # Inicializa a API do LiveKit (usará variáveis de ambiente)
        lk_api = api.LiveKitAPI(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
        )

        # 1. Verifica se a sala já existe, usando o objeto de requisição correto
        list_request = api.ListRoomsRequest(names=[agent_config.room_name])
        room_list = await lk_api.room.list_rooms(list_request)

        if not room_list.rooms:
            # 2. Se não existir, cria a sala
            logger.info(f"Sala '{agent_config.room_name}' não encontrada. Criando...")
            await lk_api.room.create_room(api.CreateRoomRequest(name=agent_config.room_name))
            logger.info(f"Sala '{agent_config.room_name}' criada com sucesso.")

        # 3. Procede com a criação do agente
        agent_id = f"{agent_config.agent_type}_{agent_config.room_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Verificar se já existe um agente para esta sala
        for existing_agent in active_agents.values():
            if existing_agent["room_name"] == agent_config.room_name:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Já existe um agente ativo para a sala {agent_config.room_name}"
                )
        
        # Configurar o agente
        agent_info = {
            "agent_id": agent_id,
            "agent_type": agent_config.agent_type,
            "room_name": agent_config.room_name,
            "personality": agent_config.personality,
            "features": agent_config.features,
            "status": "starting",
            "start_time": datetime.now().isoformat(),
            "metrics": {
                "total_interactions": 0,
                "conversation_length": 0,
                "errors": 0
            }
        }
        
        active_agents[agent_id] = agent_info
        
        # Iniciar o agente em background
        background_tasks.add_task(start_agent_process, agent_id, agent_config)
        
        logger.info(f"Agente {agent_id} iniciado para sala {agent_config.room_name}")
        
        return {
            "message": "Agente iniciado com sucesso",
            "agent_id": agent_id,
            "status": "starting"
        }

    except HTTPException as http_exc:
        raise http_exc  # Re-lança a exceção HTTP para que o FastAPI a manipule
    except Exception as e:
        logger.error(f"Erro inesperado ao iniciar agente ou gerenciar sala: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

class StopAgentRequest(BaseModel):
    agent_id: Optional[str] = None
    room_name: Optional[str] = None

@app.post("/agents/stop", status_code=200)
async def stop_agent(request: StopAgentRequest):
    """Para um agente ativo pelo seu ID ou pelo nome da sala."""
    if not request.agent_id and not request.room_name:
        raise HTTPException(status_code=400, detail="É necessário fornecer agent_id ou room_name")

    agent_to_stop_id = None
    if request.room_name:
        for agent_id, agent_info in active_agents.items():
            if agent_info.get("room_name") == request.room_name:
                agent_to_stop_id = agent_id
                break
        if not agent_to_stop_id:
            raise HTTPException(status_code=404, detail=f"Nenhum agente ativo encontrado para a sala {request.room_name}")
    elif request.agent_id:
        if request.agent_id not in active_agents:
            raise HTTPException(status_code=404, detail=f"Agente com ID {request.agent_id} não encontrado.")
        agent_to_stop_id = request.agent_id

    agent_info = active_agents.get(agent_to_stop_id, {})
    process = agent_info.get("process")
    
    if process and process.poll() is None:  # Verifica se o processo está rodando
        logger.info(f"Tentando parar o processo do agente {agent_to_stop_id} (PID: {process.pid})")
        process.terminate()
        try:
            process.wait(timeout=5)
            logger.info(f"Processo do agente {agent_to_stop_id} parado com sucesso.")
        except subprocess.TimeoutExpired:
            logger.warning(f"Processo do agente {agent_to_stop_id} não parou a tempo, forçando a finalização.")
            process.kill()

    if agent_to_stop_id in active_agents:
        del active_agents[agent_to_stop_id]
        logger.info(f"Agente {agent_to_stop_id} removido da lista de agentes ativos.")
        return {"message": f"Agente {agent_to_stop_id} parado e removido com sucesso."}
    
    # Este caso não deve ser alcançado devido às verificações anteriores, mas é uma salvaguarda.
    raise HTTPException(status_code=404, detail="Agente não encontrado para remoção.")

async def start_agent_process(agent_id: str, agent_config: AgentConfig):
    """Inicia o processo do agente em segundo plano"""
    try:
        active_agents[agent_id]["status"] = "running"

        script_to_run = ""
        if agent_config.agent_type == "groq":
            script_to_run = "groq_voice_agent.py"
        elif agent_config.agent_type == "advanced_groq":
            script_to_run = "advanced_groq_agent.py"
        else:
            logger.warning(f"Tipo de agente desconhecido: {agent_config.agent_type}")
            active_agents[agent_id]["status"] = "error"
            return

        command = [
            sys.executable,  # Garante que estamos usando o python correto do ambiente
            # O comando correto, conforme a documentação do LiveKit, é executar o script diretamente
            # com o argumento 'start'. Não usamos '-m' aqui.
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

        # Iniciar a thread para registrar a saída do agente
        log_thread = threading.Thread(target=log_agent_output, args=(agent_id, process))
        log_thread.daemon = True  # Permite que a aplicação principal saia mesmo que a thread esteja rodando
        log_thread.start()
        active_agents[agent_id]["process"] = process
        logger.info(f"Agente {script_to_run} ({agent_id}) iniciado com PID {process.pid} para a sala {agent_config.room_name}")

    except Exception as e:
        logger.error(f"Erro no processo do agente {agent_id}: {e}")
        active_agents[agent_id]["status"] = "error"
        active_agents[agent_id]["metrics"]["errors"] += 1

def log_agent_output(agent_id: str, process: subprocess.Popen):
    """
    Lê a saída de um processo de agente em uma thread separada e a registra.
    Atualiza o status do agente quando o processo termina.
    """
    try:
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                logger.info(f"[AgentLog-{agent_id}]: {line.strip()}")
            process.stdout.close()

        return_code = process.wait()
        logger.info(f"Processo do agente {agent_id} finalizado com código: {return_code}")

        if agent_id in active_agents:
            if return_code == 0:
                active_agents[agent_id]["status"] = "finished"
            else:
                active_agents[agent_id]["status"] = "crashed"
                active_agents[agent_id]["metrics"]["errors"] += 1
            
            active_agents[agent_id]["process"] = None
            active_agents[agent_id]["ended_at"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Erro no logger do processo do agente {agent_id}: {e}")

@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Para um agente específico"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    try:
        agent_info = active_agents[agent_id]
        agent_info["status"] = "stopping"

        process = agent_info.get("process")
        if process:
            process.terminate()
            process.wait()
            logger.info(f"Processo do agente {agent_id} (PID: {process.pid}) terminado.")

        active_agents.pop(agent_id)

        logger.info(f"Agente {agent_id} parado com sucesso")

        return {
            "message": "Agente parado com sucesso",
            "agent_id": agent_id,
            "final_metrics": agent_info["metrics"]
        }

    except Exception as e:
        logger.error(f"Erro ao parar agente {agent_id}: {e}")
        if agent_id in active_agents:
            active_agents.pop(agent_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def list_agents():
    """Lista todos os agentes ativos"""
    return {
        "active_agents": len(active_agents),
        "agents": list(active_agents.values())
    }

@app.get("/agents/{agent_id}")
async def get_agent_status(agent_id: str):
    """Obtém o status de um agente específico"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    return active_agents[agent_id]

@app.get("/conversations")
async def get_conversations(limit: int = 50):
    """Obtém o histórico de conversas"""
    return {
        "total_conversations": len(conversation_logs),
        "conversations": conversation_logs[-limit:]
    }

@app.post("/conversations/log")
async def log_conversation(conversation: ConversationMessage):
    """Registra uma nova conversa"""
    conversation_data = {
        "id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "participant_id": conversation.participant_id,
        "message": conversation.message,
        "agent_response": conversation.agent_response,
        "timestamp": conversation.timestamp,
        "processed_at": datetime.now().isoformat()
    }
    
    conversation_logs.append(conversation_data)
    
    # Manter apenas as últimas 1000 conversas
    if len(conversation_logs) > 1000:
        conversation_logs.pop(0)
    
    return {"message": "Conversa registrada com sucesso", "conversation_id": conversation_data["id"]}

@app.get("/metrics")
async def get_metrics():
    """Obtém métricas gerais da aplicação"""
    total_interactions = sum(agent["metrics"]["total_interactions"] for agent in active_agents.values())
    total_errors = sum(agent["metrics"]["errors"] for agent in active_agents.values())
    
    return {
        "active_agents": len(active_agents),
        "total_interactions": total_interactions,
        "total_errors": total_errors,
        "total_conversations": len(conversation_logs),
        "uptime": "running",  # Implementar cálculo de uptime real
        "timestamp": datetime.now().isoformat()
    }

@app.get("/config")
async def get_config():
    """Obtém a configuração atual da aplicação"""
    return {
        "livekit_url": os.getenv("LIVEKIT_URL", "Não configurado"),
        "groq_enabled": bool(os.getenv("GROQ_API_KEY")),
        "assemblyai_enabled": bool(os.getenv("ASSEMBLYAI_API_KEY")),
        "railway_deployment": bool(os.getenv("RAILWAY_TOKEN")),
        "environment": os.getenv("APP_ENV", "development")
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Iniciando servidor API na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)