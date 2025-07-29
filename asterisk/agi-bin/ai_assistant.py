#!/usr/bin/env python3
"""
Asterisk AGI Script para Assistente de IA
Integração com Groq AI e AssemblyAI para chamadas telefônicas
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests
import websocket
import threading
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/asterisk/ai_assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AsteriskAGI:
    """Classe para comunicação com Asterisk via AGI"""
    
    def __init__(self):
        self.env = {}
        self.setup_agi()
    
    def setup_agi(self):
        """Configurar ambiente AGI"""
        try:
            # Ler variáveis do ambiente AGI
            while True:
                line = sys.stdin.readline().strip()
                if line == '':
                    break
                key, value = line.split(':', 1)
                self.env[key.strip()] = value.strip()
            
            logger.info(f"AGI Environment: {self.env}")
        except Exception as e:
            logger.error(f"Erro ao configurar AGI: {e}")
    
    def execute(self, command: str) -> str:
        """Executar comando AGI"""
        try:
            print(command)
            sys.stdout.flush()
            result = sys.stdin.readline().strip()
            logger.info(f"AGI Command: {command} -> {result}")
            return result
        except Exception as e:
            logger.error(f"Erro ao executar comando AGI: {e}")
            return ""
    
    def answer(self):
        """Atender chamada"""
        return self.execute("ANSWER")
    
    def hangup(self):
        """Desligar chamada"""
        return self.execute("HANGUP")
    
    def say_text(self, text: str, escape_digits: str = ""):
        """Falar texto usando TTS"""
        return self.execute(f'SAY TEXT "{text}" "{escape_digits}"')
    
    def stream_file(self, filename: str, escape_digits: str = ""):
        """Reproduzir arquivo de áudio"""
        return self.execute(f'STREAM FILE {filename} "{escape_digits}"')
    
    def record_file(self, filename: str, format: str = "wav", escape_digits: str = "#", timeout: int = 10000):
        """Gravar áudio"""
        return self.execute(f'RECORD FILE {filename} {format} "{escape_digits}" {timeout}')
    
    def get_variable(self, variable: str) -> str:
        """Obter variável do canal"""
        result = self.execute(f"GET VARIABLE {variable}")
        return result.split('(')[1].split(')')[0] if '(' in result else ""
    
    def set_variable(self, variable: str, value: str):
        """Definir variável do canal"""
        return self.execute(f'SET VARIABLE {variable} "{value}"')

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

class AssemblyAISTT:
    """Cliente para AssemblyAI Speech-to-Text"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"authorization": api_key}
        self.base_url = "https://api.assemblyai.com/v2"
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcrever arquivo de áudio"""
        try:
            # Upload do arquivo
            with open(audio_file_path, 'rb') as f:
                upload_response = requests.post(
                    f"{self.base_url}/upload",
                    headers=self.headers,
                    files={'file': f},
                    timeout=30
                )
            
            if upload_response.status_code != 200:
                logger.error(f"Erro no upload: {upload_response.text}")
                return ""
            
            audio_url = upload_response.json()["upload_url"]
            
            # Solicitar transcrição
            transcript_request = {
                "audio_url": audio_url,
                "language_code": "pt"
            }
            
            transcript_response = requests.post(
                f"{self.base_url}/transcript",
                headers=self.headers,
                json=transcript_request,
                timeout=10
            )
            
            if transcript_response.status_code != 200:
                logger.error(f"Erro na transcrição: {transcript_response.text}")
                return ""
            
            transcript_id = transcript_response.json()["id"]
            
            # Aguardar conclusão
            while True:
                status_response = requests.get(
                    f"{self.base_url}/transcript/{transcript_id}",
                    headers=self.headers,
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    logger.error(f"Erro ao verificar status: {status_response.text}")
                    return ""
                
                status_data = status_response.json()
                
                if status_data["status"] == "completed":
                    return status_data["text"]
                elif status_data["status"] == "error":
                    logger.error(f"Erro na transcrição: {status_data}")
                    return ""
                
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Erro AssemblyAI: {e}")
            return ""

class AIAssistant:
    """Assistente de IA principal"""
    
    def __init__(self):
        self.agi = AsteriskAGI()
        self.groq = GroqAI(os.getenv("GROQ_API_KEY", ""))
        self.assembly = AssemblyAISTT(os.getenv("ASSEMBLYAI_API_KEY", ""))
        self.call_context = {
            "caller_id": self.agi.get_variable("CALLERID(num)"),
            "caller_name": self.agi.get_variable("CALLERID(name)"),
            "start_time": datetime.now().isoformat(),
            "conversation": []
        }
        
    def run(self):
        """Executar assistente de IA"""
        try:
            logger.info(f"🤖 Iniciando AI Assistant para chamada: {self.call_context}")
            
            # Atender chamada
            self.agi.answer()
            
            # Saudação inicial
            greeting = f"Olá! Eu sou seu assistente de IA. Como posso ajudá-lo hoje?"
            self.speak(greeting)
            
            # Loop principal de conversação
            conversation_count = 0
            max_turns = 10
            
            while conversation_count < max_turns:
                # Gravar fala do usuário
                audio_file = f"/tmp/user_audio_{int(time.time())}.wav"
                logger.info("🎤 Aguardando fala do usuário...")
                
                result = self.agi.record_file(audio_file, "wav", "#", 10000)
                
                if "timeout" in result.lower():
                    self.speak("Não ouvi nada. Posso ajudá-lo com mais alguma coisa?")
                    continue
                
                # Transcrever áudio
                logger.info("🔄 Transcrevendo áudio...")
                user_text = self.assembly.transcribe_audio(audio_file)
                
                if not user_text:
                    self.speak("Desculpe, não consegui entender. Pode repetir?")
                    continue
                
                logger.info(f"👤 Usuário disse: {user_text}")
                self.call_context["conversation"].append({
                    "role": "user",
                    "content": user_text,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Verificar se quer encerrar
                if any(word in user_text.lower() for word in ["tchau", "obrigado", "desligar", "encerrar"]):
                    self.speak("Obrigado por ligar! Tenha um ótimo dia!")
                    break
                
                # Gerar resposta IA
                logger.info("🧠 Gerando resposta IA...")
                ai_response = self.groq.generate_response(user_text, self.call_context)
                
                logger.info(f"🤖 IA responde: {ai_response}")
                self.call_context["conversation"].append({
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Falar resposta
                self.speak(ai_response)
                
                conversation_count += 1
                
                # Limpar arquivo temporário
                try:
                    os.remove(audio_file)
                except:
                    pass
            
            # Encerrar chamada
            if conversation_count >= max_turns:
                self.speak("Foi um prazer conversar com você! Até logo!")
            
            self.agi.hangup()
            
        except Exception as e:
            logger.error(f"❌ Erro no AI Assistant: {e}")
            self.speak("Desculpe, ocorreu um erro técnico. Encerrando chamada.")
            self.agi.hangup()
    
    def speak(self, text: str):
        """Falar texto usando TTS"""
        try:
            logger.info(f"🗣️ Falando: {text}")
            # Para produção, usar TTS real (Festival, eSpeak, etc.)
            # Por enquanto, usar SAY TEXT do Asterisk
            self.agi.say_text(text)
        except Exception as e:
            logger.error(f"Erro ao falar: {e}")

if __name__ == "__main__":
    try:
        assistant = AIAssistant()
        assistant.run()
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
