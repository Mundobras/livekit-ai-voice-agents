#!/usr/bin/env python3
"""
Servidor SIP Python Puro + IA
Sistema simplificado que funciona no Railway
Sem dependência do Asterisk - usando bibliotecas Python
"""

import os
import json
import asyncio
import logging
import socket
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import websockets
from contextlib import asynccontextmanager
import subprocess
import time

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

# Gerenciador de chamadas ativas
active_calls: Dict[str, CallStatus] = {}
websocket_connections: List[WebSocket] = []

class SimpleSIPClient:
    """Cliente SIP simplificado usando Python puro"""
    
    def __init__(self, sip_server: str, sip_port: int, username: str, password: str, caller_id: str):
        self.sip_server = sip_server
        self.sip_port = sip_port
        self.username = username
        self.password = password
        self.caller_id = caller_id
        self.socket = None
        self.registered = False
        
    def connect(self):
        """Conectar ao servidor SIP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(10)
            logger.info(f"🔌 Conectando ao SIP: {self.sip_server}:{self.sip_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar SIP: {e}")
            return False
    
    def register(self):
        """Registrar no servidor SIP"""
        try:
            if not self.socket:
                self.connect()
            
            # Mensagem SIP REGISTER simplificada
            register_msg = f"""REGISTER sip:{self.sip_server} SIP/2.0
Via: SIP/2.0/UDP {self.sip_server}:{self.sip_port}
From: <sip:{self.username}@{self.sip_server}>
To: <sip:{self.username}@{self.sip_server}>
Call-ID: {int(time.time())}@{self.sip_server}
CSeq: 1 REGISTER
Contact: <sip:{self.username}@{self.sip_server}:{self.sip_port}>
Authorization: Digest username="{self.username}", password="{self.password}"
Content-Length: 0

"""
            
            self.socket.sendto(register_msg.encode(), (self.sip_server, self.sip_port))
            
            # Aguardar resposta
            response, addr = self.socket.recvfrom(1024)
            response_str = response.decode()
            
            if "200 OK" in response_str:
                self.registered = True
                logger.info("✅ Registrado no SIP com sucesso!")
                return True
            else:
                logger.error(f"❌ Falha no registro SIP: {response_str}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no registro SIP: {e}")
            return False
    
    def make_call(self, destination: str) -> Dict[str, Any]:
        """Fazer chamada SIP"""
        try:
            if not self.registered:
                if not self.register():
                    return {"success": False, "error": "Falha no registro SIP"}
            
            call_id = f"call_{int(time.time())}"
            
            # Mensagem SIP INVITE
            invite_msg = f"""INVITE sip:{destination}@{self.sip_server} SIP/2.0
Via: SIP/2.0/UDP {self.sip_server}:{self.sip_port}
From: <sip:{self.caller_id}@{self.sip_server}>
To: <sip:{destination}@{self.sip_server}>
Call-ID: {call_id}@{self.sip_server}
CSeq: 1 INVITE
Contact: <sip:{self.username}@{self.sip_server}:{self.sip_port}>
Content-Type: application/sdp
Content-Length: 200

v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {self.sip_server}
s=AI Call
c=IN IP4 {self.sip_server}
t=0 0
m=audio 8000 RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000

"""
            
            self.socket.sendto(invite_msg.encode(), (self.sip_server, self.sip_port))
            
            # Aguardar resposta
            response, addr = self.socket.recvfrom(2048)
            response_str = response.decode()
            
            logger.info(f"📞 Resposta SIP: {response_str[:200]}...")
            
            if "100 Trying" in response_str or "180 Ringing" in response_str:
                return {
                    "success": True,
                    "call_id": call_id,
                    "status": "calling",
                    "message": f"Chamada para {destination} iniciada"
                }
            else:
                return {
                    "success": False,
                    "error": response_str,
                    "message": "Falha ao iniciar chamada"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao fazer chamada SIP: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Erro interno na chamada SIP"
            }
    
    def hangup_call(self, call_id: str) -> bool:
        """Encerrar chamada"""
        try:
            # Mensagem SIP BYE
            bye_msg = f"""BYE sip:{self.sip_server} SIP/2.0
Via: SIP/2.0/UDP {self.sip_server}:{self.sip_port}
From: <sip:{self.username}@{self.sip_server}>
To: <sip:{self.username}@{self.sip_server}>
Call-ID: {call_id}@{self.sip_server}
CSeq: 2 BYE
Content-Length: 0

"""
            
            self.socket.sendto(bye_msg.encode(), (self.sip_server, self.sip_port))
            logger.info(f"📴 Chamada {call_id} encerrada")
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

# Instância do cliente SIP
sip_client = SimpleSIPClient(
    sip_server="45.178.225.79",
    sip_port=5060,
    username="27861",
    password="OUmjchkR2025",
    caller_id="1151996574"
)

# Instância do Groq AI
groq_ai = GroqAI(os.getenv("GROQ_API_KEY", ""))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando Python SIP Server...")
    if sip_client.connect():
        logger.info("✅ Cliente SIP conectado")
    yield
    # Shutdown
    logger.info("🛑 Encerrando Python SIP Server...")

# Criar aplicação FastAPI
app = FastAPI(
    title="Python SIP AI Voice Server",
    description="Sistema SIP + IA usando Python puro (sem Asterisk)",
    version="2.0.0",
    lifespan=lifespan
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
        "message": "Python SIP AI Voice Server",
        "version": "2.0.0",
        "status": "running",
        "sip_connected": sip_client.socket is not None,
        "sip_registered": sip_client.registered,
        "active_calls": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde"""
    return {
        "status": "healthy",
        "sip_connected": sip_client.socket is not None,
        "sip_registered": sip_client.registered,
        "active_calls": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/call/outbound")
async def make_outbound_call(call_request: CallRequest, background_tasks: BackgroundTasks):
    """Fazer chamada sainte usando SIP Python"""
    try:
        logger.info(f"📞 Nova chamada sainte: {call_request.destination_number}")
        
        # Fazer chamada via cliente SIP Python
        result = sip_client.make_call(call_request.destination_number)
        
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
                    "message": f"Chamada SIP para {call_request.destination_number} iniciada!",
                    "destination": call_request.destination_number,
                    "caller_id": call_request.caller_id,
                    "ai_enabled": call_request.ai_enabled,
                    "sip_server": "45.178.225.79",
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao iniciar chamada SIP: {result.get('error', 'Erro desconhecido')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro ao fazer chamada sainte: {e}")
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
            success = sip_client.hangup_call(call_id)
            
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
                raise HTTPException(status_code=500, detail="Erro ao encerrar chamada SIP")
        else:
            raise HTTPException(status_code=404, detail="Chamada não encontrada")
            
    except Exception as e:
        logger.error(f"❌ Erro ao encerrar chamada: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

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

@app.get("/sip/status")
async def sip_status():
    """Status do cliente SIP"""
    return {
        "connected": sip_client.socket is not None,
        "registered": sip_client.registered,
        "server": f"{sip_client.sip_server}:{sip_client.sip_port}",
        "username": sip_client.username,
        "caller_id": sip_client.caller_id,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/sip/register")
async def register_sip():
    """Registrar no servidor SIP"""
    try:
        success = sip_client.register()
        return {
            "success": success,
            "registered": sip_client.registered,
            "message": "Registro SIP realizado" if success else "Falha no registro SIP",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no registro SIP: {str(e)}")

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

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "python_sip_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
