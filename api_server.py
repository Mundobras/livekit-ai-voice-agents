import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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
    """Inicia um novo agente"""
    try:
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
        
    except Exception as e:
        logger.error(f"Erro ao iniciar agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def start_agent_process(agent_id: str, agent_config: AgentConfig):
    """Inicia o processo do agente"""
    try:
        # Atualizar status
        active_agents[agent_id]["status"] = "running"
        
        # Aqui você pode iniciar o agente específico baseado no tipo
        if agent_config.agent_type == "groq":
            # Importar e executar o agente Groq
            from groq_voice_agent import entrypoint
            # Implementar lógica para executar o agente
            logger.info(f"Agente Groq {agent_id} em execução")
        elif agent_config.agent_type == "advanced_groq":
            # Importar e executar o agente avançado
            from advanced_groq_agent import entrypoint
            # Implementar lógica para executar o agente
            logger.info(f"Agente avançado Groq {agent_id} em execução")
        else:
            # Agentes básicos
            logger.info(f"Agente básico {agent_id} em execução")
            
    except Exception as e:
        logger.error(f"Erro no processo do agente {agent_id}: {e}")
        active_agents[agent_id]["status"] = "error"
        active_agents[agent_id]["metrics"]["errors"] += 1

@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Para um agente específico"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    try:
        active_agents[agent_id]["status"] = "stopping"
        
        # Aqui você implementaria a lógica para parar o agente
        # Por exemplo, enviar sinal de parada para o processo
        
        # Remover do dicionário de agentes ativos
        agent_info = active_agents.pop(agent_id)
        
        logger.info(f"Agente {agent_id} parado com sucesso")
        
        return {
            "message": "Agente parado com sucesso",
            "agent_id": agent_id,
            "final_metrics": agent_info["metrics"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao parar agente {agent_id}: {e}")
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
    uvicorn.run(app, host=host, port=port) 