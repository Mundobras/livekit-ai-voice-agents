"""
LiveKit + AssemblyAI Real-time Speech-to-Text Agent

Este agente conecta-se ao LiveKit para capturar áudio em tempo real
e usa AssemblyAI para transcrever o speech em texto em tempo real.

Baseado no tutorial: https://www.assemblyai.com/blog/livekit-realtime-speech-to-text
"""

import os
import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions
from livekit.agents.llm import llm
from livekit.agents.llm.llm import StopResponse
from livekit.agents.llm.llm import ChatContext, ChatMessage
from livekit.agents.llm.llm import RoomOutputOptions
from livekit.agents.llm.llm import AutoSubscribe
import assemblyai

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("transcriber")

class Transcriber(Agent):
    """
    Agente de transcrição que converte speech em texto em tempo real.
    
    Este agente:
    1. Conecta-se ao LiveKit e escuta áudio dos participantes
    2. Usa AssemblyAI para transcrever o áudio em tempo real
    3. Publica as transcrições de volta para a sala
    4. Executa lógica customizada quando uma fala é completada
    """
    
    def __init__(self):
        super().__init__(
            instructions="not-needed",  # Não precisa de instruções pois só transcreve
            stt=assemblyai.STT(),  # Usa AssemblyAI para Speech-to-Text
        )
    
    async def on_user_turn_completed(self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """
        Executado quando um usuário completa uma fala.
        
        Args:
            chat_ctx: Contexto da conversa
            new_message: Mensagem com o texto transcrito
        """
        user_transcript = new_message.text_content
        logger.info(f"Transcrição completada: {user_transcript}")
        
        # Aqui você pode adicionar lógica customizada como:
        # - Análise de sentimento
        # - Moderação de conteúdo
        # - Logging para analytics
        # - Integração com outros sistemas
        
        # Para um agente que só transcreve (sem conversação), 
        # levantamos StopResponse para parar o pipeline LLM
        raise StopResponse()

async def entrypoint(ctx: JobContext):
    """
    Ponto de entrada do agente - executado quando o LiveKit inicia um job.
    
    Args:
        ctx: Contexto do job com informações da sala
    """
    logger.info(f"Iniciando agente de transcrição para sala: {ctx.room.name}")
    
    # Conecta à sala e se inscreve automaticamente em todos os tracks de áudio
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Cria uma sessão do agente que gerencia entrada/saída
    session = AgentSession()
    
    # Inicia a sessão do agente
    await session.start(
        agent=Transcriber(),  # Instância do nosso agente
        room=ctx.room,  # Sala do LiveKit
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,  # Envia transcrições para o frontend
            audio_enabled=False,  # Não envia áudio (só transcreve)
        ),
    )

if __name__ == "__main__":
    # Executa o agente como um worker do LiveKit
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 