"""
LiveKit + AssemblyAI Advanced Speech-to-Text Agent

Versão avançada do agente com recursos adicionais:
- Análise de sentimento
- Moderação de conteúdo
- Logging estruturado
- Métricas em tempo real
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("advanced_transcriber")

class AdvancedTranscriber(Agent):
    """
    Agente avançado de transcrição com recursos adicionais.
    """
    
    def __init__(self):
        super().__init__(
            instructions="not-needed",
            stt=assemblyai.STT(),
        )
        
        # Métricas em tempo real
        self.metrics = {
            "total_transcriptions": 0,
            "total_words": 0,
            "session_start": datetime.now(),
            "participants": set()
        }
        
        # Palavras para moderação (exemplo)
        self.moderation_words = {
            "inappropriate": ["palavrao1", "palavrao2"],
            "spam": ["spam", "promoção", "venda"]
        }
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Análise simples de sentimento baseada em palavras-chave.
        Em produção, você usaria um modelo de ML mais sofisticado.
        """
        positive_words = ["bom", "ótimo", "excelente", "gosto", "legal", "feliz"]
        negative_words = ["ruim", "péssimo", "terrível", "não gosto", "triste", "raiva"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = positive_count / (positive_count + negative_count + 1)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = negative_count / (positive_count + negative_count + 1)
        else:
            sentiment = "neutral"
            confidence = 0.5
            
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_words": positive_count,
            "negative_words": negative_count
        }
    
    def check_moderation(self, text: str) -> Dict[str, Any]:
        """
        Verifica se o texto contém conteúdo que precisa de moderação.
        """
        text_lower = text.lower()
        issues = []
        
        for category, words in self.moderation_words.items():
            found_words = [word for word in words if word in text_lower]
            if found_words:
                issues.append({
                    "category": category,
                    "words": found_words
                })
        
        return {
            "needs_moderation": len(issues) > 0,
            "issues": issues
        }
    
    def update_metrics(self, text: str, participant_id: str):
        """
        Atualiza métricas em tempo real.
        """
        self.metrics["total_transcriptions"] += 1
        self.metrics["total_words"] += len(text.split())
        self.metrics["participants"].add(participant_id)
        
        # Log das métricas a cada 10 transcrições
        if self.metrics["total_transcriptions"] % 10 == 0:
            logger.info(f"Métricas: {self.metrics}")
    
    async def on_user_turn_completed(self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """
        Processamento avançado quando uma fala é completada.
        """
        user_transcript = new_message.text_content
        participant_id = chat_ctx.participant.identity if chat_ctx.participant else "unknown"
        
        # Análise de sentimento
        sentiment_analysis = self.analyze_sentiment(user_transcript)
        
        # Verificação de moderação
        moderation_check = self.check_moderation(user_transcript)
        
        # Atualização de métricas
        self.update_metrics(user_transcript, participant_id)
        
        # Log estruturado
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "participant_id": participant_id,
            "transcript": user_transcript,
            "sentiment": sentiment_analysis,
            "moderation": moderation_check,
            "word_count": len(user_transcript.split())
        }
        
        logger.info(f"Transcrição processada: {json.dumps(log_data, ensure_ascii=False)}")
        
        # Ações baseadas na análise
        if moderation_check["needs_moderation"]:
            logger.warning(f"Conteúdo que precisa de moderação detectado: {moderation_check}")
            # Aqui você pode implementar ações como:
            # - Alertar moderadores
            # - Mutar o participante
            # - Registrar incidente
        
        if sentiment_analysis["sentiment"] == "negative" and sentiment_analysis["confidence"] > 0.7:
            logger.info(f"Sentimento negativo detectado com alta confiança: {sentiment_analysis}")
            # Aqui você pode implementar ações como:
            # - Alertar sobre possível conflito
            # - Sugerir intervenção
        
        # Para um agente que só transcreve, parar o pipeline
        raise StopResponse()

async def entrypoint(ctx: JobContext):
    """
    Ponto de entrada do agente avançado.
    """
    logger.info(f"Iniciando agente avançado de transcrição para sala: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    session = AgentSession()
    
    await session.start(
        agent=AdvancedTranscriber(),
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            audio_enabled=False,
        ),
    )

if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 