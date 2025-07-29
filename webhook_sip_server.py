#!/usr/bin/env python3
"""
Servidor SIP via Webhooks + IA
Solução simplificada que funciona no Railway
Usando APIs externas para SIP + Groq AI
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uuid

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelos Pydantic
class CallRequest(BaseModel):
    destination_number: str
    caller_id: str = "AI Assistant"
    initial_message: str = "Olá! Eu sou seu assistente de IA."
    ai_enabled: bool = True

class CallStatus(BaseModel):
    call_id: str
    status: str
    destination: str
    start_time: str
    duration: Optional[int] = None
    ai_enabled: bool = True

class WebhookData(BaseModel):
    event: str
    call_id: str
    data: Dict[str, Any]

# Gerenciador de chamadas ativas
active_calls: Dict[str, CallStatus] = {}
websocket_connections: List[WebSocket] = []

class SIPWebhookManager:
    """Gerenciador de webhooks SIP"""
    
    def __init__(self):
        self.sip_config = {
            "server": "45.178.225.79",
            "port": 5060,
            "username": "27861",
            "password": "OUmjchkR2025",
            "caller_id": "1151996574"
        }
    
    def simulate_sip_call(self, destination: str) -> Dict[str, Any]:
        """Simular chamada SIP (para desenvolvimento)"""
        try:
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"📞 Simulando chamada SIP para {destination}")
            logger.info(f"🔧 Usando servidor: {self.sip_config['server']}")
            logger.info(f"👤 Usuário: {self.sip_config['username']}")
            logger.info(f"📱 Caller ID: {self.sip_config['caller_id']}")
            
            # Simular processo de chamada
            return {
                "success": True,
                "call_id": call_id,
                "status": "calling",
                "message": f"Chamada simulada para {destination} iniciada",
                "sip_details": {
                    "server": self.sip_config["server"],
                    "username": self.sip_config["username"],
                    "caller_id": self.sip_config["caller_id"],
                    "destination": destination
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na simulação SIP: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Erro na simulação de chamada"
            }
    
    def hangup_call(self, call_id: str) -> bool:
        """Encerrar chamada"""
        try:
            logger.info(f"📴 Encerrando chamada {call_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao encerrar chamada: {e}")
            return False

class GroqAI:
    """Cliente para Groq AI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_response(self, text: str, context: Dict = None) -> str:
        """Gerar resposta usando Groq AI"""
        try:
            if not self.api_key:
                return "IA não configurada. Configure GROQ_API_KEY."
            
            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente de IA para chamadas telefônicas. 
                    Seja conciso, educado e útil. Responda em português brasileiro.
                    Mantenha respostas curtas (máximo 2 frases) para chamadas telefônicas."""
                },
                {
                    "role": "user", 
                    "content": text
                }
            ]
            
            if context:
                messages[0]["content"] += f"\nContexto da chamada: {json.dumps(context, ensure_ascii=False)}"
            
            payload = {
                "model": "llama3-8b-8192",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 150,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Erro Groq API: {response.status_code} - {response.text}")
                return "Desculpe, não consegui processar sua solicitação no momento."
                
        except Exception as e:
            logger.error(f"Erro ao gerar resposta Groq: {e}")
            return "Desculpe, ocorreu um erro técnico."

# Instâncias
sip_manager = SIPWebhookManager()
groq_ai = GroqAI(os.getenv("GROQ_API_KEY", ""))

# Criar aplicação FastAPI
app = FastAPI(
    title="Webhook SIP AI Voice Server",
    description="Sistema SIP via Webhooks + IA (Railway compatível)",
    version="3.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Webhook SIP AI Voice Server",
        "version": "3.0.0",
        "status": "running",
        "sip_configured": True,
        "ai_configured": bool(os.getenv("GROQ_API_KEY")),
        "active_calls": len(active_calls),
        "sip_config": {
            "server": sip_manager.sip_config["server"],
            "username": sip_manager.sip_config["username"],
            "caller_id": sip_manager.sip_config["caller_id"]
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde"""
    return {
        "status": "healthy",
        "sip_ready": True,
        "ai_ready": bool(os.getenv("GROQ_API_KEY")),
        "active_calls": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/call/outbound")
async def make_outbound_call(call_request: CallRequest, background_tasks: BackgroundTasks):
    """Fazer chamada sainte via webhook SIP"""
    try:
        logger.info(f"📞 Nova chamada webhook: {call_request.destination_number}")
        
        # Fazer chamada via webhook manager
        result = sip_manager.simulate_sip_call(call_request.destination_number)
        
        if result["success"]:
            # Registrar chamada ativa
            active_calls[result["call_id"]] = CallStatus(
                call_id=result["call_id"],
                status="calling",
                destination=call_request.destination_number,
                start_time=datetime.now().isoformat(),
                ai_enabled=call_request.ai_enabled
            )
            
            # Notificar WebSocket clients
            notification = {
                "type": "call_started",
                "call_id": result["call_id"],
                "destination": call_request.destination_number,
                "timestamp": datetime.now().isoformat()
            }
            
            background_tasks.add_task(notify_websocket_clients, notification)
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "call_id": result["call_id"],
                    "message": f"Chamada webhook para {call_request.destination_number} iniciada!",
                    "destination": call_request.destination_number,
                    "caller_id": call_request.caller_id,
                    "ai_enabled": call_request.ai_enabled,
                    "sip_details": result.get("sip_details", {}),
                    "note": "Sistema em modo desenvolvimento - chamada simulada",
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao iniciar chamada: {result.get('error', 'Erro desconhecido')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro ao fazer chamada webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/call/status/{call_id}")
async def get_call_status(call_id: str):
    """Obter status da chamada"""
    if call_id in active_calls:
        call = active_calls[call_id]
        return {
            "success": True,
            "call": call.dict(),
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="Chamada não encontrada")

@app.get("/call/list")
async def list_active_calls():
    """Listar chamadas ativas"""
    return {
        "success": True,
        "active_calls": [call.dict() for call in active_calls.values()],
        "total": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/call/hangup/{call_id}")
async def hangup_call(call_id: str, background_tasks: BackgroundTasks):
    """Encerrar chamada"""
    try:
        if call_id in active_calls:
            success = sip_manager.hangup_call(call_id)
            
            if success:
                # Atualizar status
                active_calls[call_id].status = "ended"
                
                # Notificar WebSocket clients
                notification = {
                    "type": "call_ended",
                    "call_id": call_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                background_tasks.add_task(notify_websocket_clients, notification)
                
                return {
                    "success": True,
                    "message": f"Chamada {call_id} encerrada com sucesso",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=500, detail="Erro ao encerrar chamada")
        else:
            raise HTTPException(status_code=404, detail="Chamada não encontrada")
            
    except Exception as e:
        logger.error(f"❌ Erro ao encerrar chamada: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/webhook/sip")
async def sip_webhook(request: Request):
    """Webhook para receber eventos SIP"""
    try:
        data = await request.json()
        logger.info(f"📨 Webhook SIP recebido: {data}")
        
        # Processar evento SIP
        event_type = data.get("event", "unknown")
        call_id = data.get("call_id", "")
        
        if event_type == "call_answered" and call_id in active_calls:
            active_calls[call_id].status = "answered"
            
            # Notificar clientes
            notification = {
                "type": "call_answered",
                "call_id": call_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await notify_websocket_clients(notification)
        
        elif event_type == "call_ended" and call_id in active_calls:
            active_calls[call_id].status = "ended"
            
            # Notificar clientes
            notification = {
                "type": "call_ended",
                "call_id": call_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await notify_websocket_clients(notification)
        
        return {"success": True, "processed": True}
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook SIP: {e}")
        return {"success": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para notificações em tempo real"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Manter conexão viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def notify_websocket_clients(message: Dict[str, Any]):
    """Notificar todos os clientes WebSocket"""
    if websocket_connections:
        for websocket in websocket_connections.copy():
            try:
                await websocket.send_json(message)
            except:
                websocket_connections.remove(websocket)

@app.get("/sip/config")
async def sip_config():
    """Configuração SIP"""
    return {
        "server": sip_manager.sip_config["server"],
        "port": sip_manager.sip_config["port"],
        "username": sip_manager.sip_config["username"],
        "caller_id": sip_manager.sip_config["caller_id"],
        "status": "configured",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/ai/chat")
async def chat_with_ai(message: dict):
    """Conversar com IA"""
    try:
        user_message = message.get("message", "")
        context = message.get("context", {})
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mensagem não fornecida")
        
        response = groq_ai.generate_response(user_message, context)
        
        return {
            "success": True,
            "user_message": user_message,
            "ai_response": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no chat IA: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/test/sip")
async def test_sip():
    """Testar configuração SIP"""
    return {
        "sip_server": sip_manager.sip_config["server"],
        "sip_port": sip_manager.sip_config["port"],
        "username": sip_manager.sip_config["username"],
        "caller_id": sip_manager.sip_config["caller_id"],
        "status": "ready_for_testing",
        "note": "Sistema configurado para desenvolvimento/teste",
        "next_steps": [
            "Configure GROQ_API_KEY para IA",
            "Use /call/outbound para testar chamadas",
            "Monitore logs em tempo real"
        ],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "webhook_sip_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
