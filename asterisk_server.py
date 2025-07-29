#!/usr/bin/env python3
"""
Servidor FastAPI integrado com Asterisk
Sistema completo de chamadas SIP + WebRTC + IA
"""

import os
import json
import asyncio
import logging
import subprocess
import psutil
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

class WebRTCOffer(BaseModel):
    sdp: str
    type: str = "offer"

class WebRTCAnswer(BaseModel):
    sdp: str
    type: str = "answer"

# Gerenciador de chamadas ativas
active_calls: Dict[str, CallStatus] = {}
websocket_connections: List[WebSocket] = []

class AsteriskManager:
    """Gerenciador do Asterisk"""
    
    def __init__(self):
        self.asterisk_process = None
        self.config_dir = "/etc/asterisk"
        self.is_running = False
    
    async def start_asterisk(self):
        """Iniciar Asterisk"""
        try:
            logger.info("🚀 Iniciando Asterisk...")
            
            # Verificar se já está rodando
            if self.is_asterisk_running():
                logger.info("✅ Asterisk já está rodando")
                self.is_running = True
                return True
            
            # Copiar configurações
            await self.setup_configs()
            
            # Iniciar Asterisk
            cmd = ["asterisk", "-f", "-vvv", "-c"]
            self.asterisk_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Aguardar inicialização
            await asyncio.sleep(5)
            
            if self.is_asterisk_running():
                logger.info("✅ Asterisk iniciado com sucesso!")
                self.is_running = True
                return True
            else:
                logger.error("❌ Falha ao iniciar Asterisk")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar Asterisk: {e}")
            return False
    
    def is_asterisk_running(self) -> bool:
        """Verificar se Asterisk está rodando"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'asterisk' in proc.info['name'].lower():
                    return True
            return False
        except:
            return False
    
    async def setup_configs(self):
        """Configurar arquivos do Asterisk"""
        try:
            # Criar diretórios se não existirem
            os.makedirs(self.config_dir, exist_ok=True)
            os.makedirs("/var/log/asterisk", exist_ok=True)
            os.makedirs("/var/lib/asterisk/agi-bin", exist_ok=True)
            
            # Copiar configurações
            config_files = [
                "asterisk.conf",
                "sip.conf", 
                "extensions.conf",
                "confbridge.conf"
            ]
            
            for config_file in config_files:
                src = f"./asterisk/{config_file}"
                dst = f"{self.config_dir}/{config_file}"
                
                if os.path.exists(src):
                    with open(src, 'r') as f:
                        content = f.read()
                    
                    with open(dst, 'w') as f:
                        f.write(content)
                    
                    logger.info(f"✅ Configuração copiada: {config_file}")
            
            # Copiar AGI script
            agi_src = "./asterisk/agi-bin/ai_assistant.py"
            agi_dst = "/var/lib/asterisk/agi-bin/ai_assistant.py"
            
            if os.path.exists(agi_src):
                with open(agi_src, 'r') as f:
                    content = f.read()
                
                with open(agi_dst, 'w') as f:
                    f.write(content)
                
                # Tornar executável
                os.chmod(agi_dst, 0o755)
                logger.info("✅ AGI script configurado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar Asterisk: {e}")
    
    async def make_call(self, destination: str, caller_id: str = "1151996574") -> Dict[str, Any]:
        """Fazer chamada via Asterisk"""
        try:
            call_id = f"call_{int(datetime.now().timestamp())}"
            
            # Comando para originar chamada
            cmd = [
                "asterisk", "-rx",
                f"channel originate SIP/sip-provider/{destination} extension 1000@ai-bridge"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Registrar chamada ativa
                active_calls[call_id] = CallStatus(
                    call_id=call_id,
                    status="calling",
                    destination=destination,
                    start_time=datetime.now().isoformat(),
                    ai_enabled=True
                )
                
                logger.info(f"📞 Chamada iniciada: {call_id} -> {destination}")
                return {
                    "success": True,
                    "call_id": call_id,
                    "status": "calling",
                    "message": f"Chamada para {destination} iniciada"
                }
            else:
                logger.error(f"❌ Erro ao fazer chamada: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "Falha ao iniciar chamada"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao fazer chamada: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Erro interno ao fazer chamada"
            }
    
    async def hangup_call(self, call_id: str) -> bool:
        """Encerrar chamada"""
        try:
            if call_id in active_calls:
                # Comando para encerrar chamada
                cmd = ["asterisk", "-rx", "hangup request all"]
                subprocess.run(cmd, timeout=5)
                
                # Atualizar status
                active_calls[call_id].status = "ended"
                logger.info(f"📞 Chamada encerrada: {call_id}")
                return True
            else:
                logger.warning(f"⚠️ Chamada não encontrada: {call_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao encerrar chamada: {e}")
            return False

# Instância do gerenciador Asterisk
asterisk_manager = AsteriskManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando Asterisk AI Server...")
    await asterisk_manager.start_asterisk()
    yield
    # Shutdown
    logger.info("🛑 Encerrando Asterisk AI Server...")

# Criar aplicação FastAPI
app = FastAPI(
    title="Asterisk AI Voice Server",
    description="Sistema completo de chamadas SIP + WebRTC + IA",
    version="1.0.0",
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
        "message": "Asterisk AI Voice Server",
        "version": "1.0.0",
        "status": "running",
        "asterisk_running": asterisk_manager.is_running,
        "active_calls": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde"""
    return {
        "status": "healthy",
        "asterisk_running": asterisk_manager.is_asterisk_running(),
        "active_calls": len(active_calls),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/call/outbound")
async def make_outbound_call(call_request: CallRequest, background_tasks: BackgroundTasks):
    """Fazer chamada sainte"""
    try:
        logger.info(f"📞 Nova chamada sainte: {call_request.destination_number}")
        
        # Fazer chamada via Asterisk
        result = await asterisk_manager.make_call(
            destination=call_request.destination_number,
            caller_id=call_request.caller_id
        )
        
        if result["success"]:
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
                    "message": f"Chamada para {call_request.destination_number} iniciada com sucesso!",
                    "destination": call_request.destination_number,
                    "caller_id": call_request.caller_id,
                    "ai_enabled": call_request.ai_enabled,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao iniciar chamada: {result.get('error', 'Erro desconhecido')}"
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
        success = await asterisk_manager.hangup_call(call_id)
        
        if success:
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

@app.get("/asterisk/status")
async def asterisk_status():
    """Status do Asterisk"""
    try:
        # Verificar status via CLI
        cmd = ["asterisk", "-rx", "core show uptime"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        return {
            "running": asterisk_manager.is_asterisk_running(),
            "uptime": result.stdout if result.returncode == 0 else "N/A",
            "config_loaded": os.path.exists("/etc/asterisk/sip.conf"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/asterisk/reload")
async def reload_asterisk():
    """Recarregar configurações do Asterisk"""
    try:
        cmd = ["asterisk", "-rx", "core reload"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao recarregar: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "asterisk_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
