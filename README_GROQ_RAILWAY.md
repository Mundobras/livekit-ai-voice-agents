# 🎤 LiveKit AI Voice Agents

**Agentes de Voz por IA usando Groq + LiveKit + Railway**

Um sistema completo para criar e gerenciar agentes de voz inteligentes em tempo real, combinando a velocidade do Groq, a comunicação em tempo real do LiveKit e a facilidade de deploy do Railway.

## 🚀 Características Principais

### 🤖 Agentes de IA
- **Agente Groq Básico**: Transcrição e respostas simples
- **Agente Groq Avançado**: Múltiplas personalidades e funcionalidades especiais
- **Agente STT Básico**: Apenas transcrição com AssemblyAI
- **Agente STT Avançado**: Transcrição com análise de sentimento e moderação

### 🎭 Personalidades Disponíveis
- **Assistente**: Profissional e útil
- **Professor**: Educativo e didático
- **Amigo**: Casual e empático
- **Coach**: Motivacional e energético

### ⚡ Funcionalidades Especiais
- **Clima**: Informações meteorológicas
- **Horário**: Data e hora atual
- **Piadas**: Humor automático
- **Frases Inspiracionais**: Motivação
- **Calculadora**: Cálculos simples
- **Tradutor**: Tradução básica

### 📊 Monitoramento
- Métricas em tempo real
- Log de conversas
- Status dos agentes
- Dashboard interativo

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server    │    │   LiveKit       │
│   Management    │◄──►│   FastAPI       │◄──►│   Agents        │
│   Dashboard     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Groq API      │
                       │   (LLM)         │
                       └─────────────────┘
```

## 📁 Estrutura do Projeto

```
PROJETO LIVEKIT 2/
├── 📄 requirements.txt              # Dependências Python
├── 📄 env.example                   # Variáveis de ambiente
├── 📄 railway.json                  # Configuração Railway
├── 📄 Procfile                      # Comando de inicialização
├── 📄 runtime.txt                   # Versão Python
│
├── 🤖 groq_voice_agent.py           # Agente Groq básico
├── 🤖 advanced_groq_agent.py        # Agente Groq avançado
├── 🤖 stt_agent.py                  # Agente STT básico
├── 🤖 advanced_stt_agent.py         # Agente STT avançado
│
├── 🌐 api_server.py                 # Servidor FastAPI
├── 🌐 frontend_management.html      # Dashboard de gerenciamento
├── 🌐 frontend_example.html         # Frontend de exemplo
│
└── 📚 README_GROQ_RAILWAY.md        # Este arquivo
```

## 🛠️ Instalação e Configuração

### 1. Pré-requisitos
- Python 3.11+
- Conta no [LiveKit Cloud](https://livekit.io/)
- Conta no [Groq](https://groq.com/)
- Conta no [Railway](https://railway.app/)
- (Opcional) Conta no [AssemblyAI](https://assemblyai.com/)

### 2. Configuração Local

```bash
# Clonar o repositório
git clone <seu-repositorio>
cd PROJETO-LIVEKIT-2

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp env.example .env
# Editar .env com suas chaves de API
```

### 3. Variáveis de Ambiente

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here

# Groq Configuration (para LLM rápido)
GROQ_API_KEY=your_groq_api_key_here

# AssemblyAI Configuration (opcional)
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Railway Configuration (para deploy)
RAILWAY_TOKEN=your_railway_token_here
RAILWAY_PROJECT_ID=your_railway_project_id_here

# Application Configuration
APP_ENV=development
PORT=8000
HOST=0.0.0.0
```

## 🚀 Como Usar

### Execução Local

```bash
# Iniciar servidor API
python api_server.py

# Ou executar agente específico
python groq_voice_agent.py
python advanced_groq_agent.py
```

### Deploy no Railway

1. **Conectar ao Railway**:
```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Inicializar projeto
railway init
```

2. **Configurar Variáveis**:
```bash
# No dashboard do Railway, adicionar as variáveis de ambiente
railway variables set LIVEKIT_URL=wss://your-project.livekit.cloud
railway variables set GROQ_API_KEY=your_groq_api_key
# ... outras variáveis
```

3. **Deploy**:
```bash
# Deploy automático
railway up

# Ou via GitHub (recomendado)
# Conectar repositório no dashboard do Railway
```

### Acessar o Dashboard

Após o deploy, acesse:
- **API**: `https://seu-projeto.railway.app`
- **Dashboard**: `https://seu-projeto.railway.app/frontend_management.html`
- **Documentação API**: `https://seu-projeto.railway.app/docs`

## 📖 API Endpoints

### Agentes
- `POST /agents/start` - Iniciar novo agente
- `POST /agents/{id}/stop` - Parar agente
- `GET /agents` - Listar agentes ativos
- `GET /agents/{id}` - Status do agente

### Métricas
- `GET /metrics` - Métricas gerais
- `GET /conversations` - Histórico de conversas
- `POST /conversations/log` - Registrar conversa

### Sistema
- `GET /health` - Verificação de saúde
- `GET /config` - Configuração atual

## 🎯 Exemplos de Uso

### 1. Iniciar Agente Básico
```bash
curl -X POST "https://seu-projeto.railway.app/agents/start" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "groq",
    "room_name": "sala-teste-001",
    "personality": "assistant"
  }'
```

### 2. Iniciar Agente Avançado
```bash
curl -X POST "https://seu-projeto.railway.app/agents/start" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "advanced_groq",
    "room_name": "sala-reuniao-002",
    "personality": "teacher",
    "features": ["weather", "calculator"]
  }'
```

### 3. Verificar Status
```bash
curl "https://seu-projeto.railway.app/agents"
```

## 🔧 Configuração Avançada

### Personalização de Agentes

```python
# Em advanced_groq_agent.py
class AdvancedGroqAgent(Agent):
    def __init__(self):
        # Adicionar novas personalidades
        self.personalities["custom"] = {
            "name": "Agente Personalizado",
            "tone": "seu tom",
            "style": "seu estilo",
            "system_prompt": "Sua instrução personalizada"
        }
        
        # Adicionar novas funcionalidades
        self.special_functions["custom_function"] = self.your_custom_function
```

### Integração com Outros LLMs

```python
# Substituir Groq por OpenAI ou outros
import openai

class CustomLLMAgent(Agent):
    def __init__(self):
        self.llm_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def generate_response(self, user_message: str) -> str:
        response = self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )
        return response.choices[0].message.content
```

## 📊 Monitoramento e Métricas

### Métricas Disponíveis
- **Agentes Ativos**: Número de agentes em execução
- **Total de Interações**: Conversas processadas
- **Total de Conversas**: Histórico completo
- **Taxa de Erro**: Erros por agente
- **Tempo de Resposta**: Latência do sistema

### Logs Estruturados
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "participant_id": "user123",
  "user_message": "Olá, como vai?",
  "ai_response": "Oi! Vou muito bem, obrigado por perguntar!",
  "current_personality": "friend",
  "session_summary": {
    "total_interactions": 15,
    "personality_changes": 2,
    "special_functions_used": 3
  }
}
```

## 🔒 Segurança

### Boas Práticas
- ✅ Nunca commitar chaves de API
- ✅ Usar variáveis de ambiente
- ✅ Implementar rate limiting
- ✅ Validar inputs do usuário
- ✅ Monitorar logs de erro

### Configuração de Segurança
```python
# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/agents/start")
@limiter.limit("10/minute")
async def start_agent(request: Request, agent_config: AgentConfig):
    # Implementação
```

## 🚀 Roadmap

### Fase 1 - MVP ✅
- [x] Agentes básicos com Groq
- [x] API de gerenciamento
- [x] Dashboard web
- [x] Deploy no Railway

### Fase 2 - Melhorias 🔄
- [ ] Integração com TTS (Text-to-Speech)
- [ ] Suporte a múltiplos idiomas
- [ ] Análise de sentimento avançada
- [ ] Integração com bancos de dados

### Fase 3 - Escalabilidade 📈
- [ ] Load balancing
- [ ] Cache distribuído
- [ ] Métricas avançadas
- [ ] Integração com ferramentas de monitoramento

### Fase 4 - Recursos Avançados 🎯
- [ ] Agentes especializados por domínio
- [ ] Aprendizado contínuo
- [ ] Integração com APIs externas
- [ ] Interface de voz natural

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🆘 Suporte

### Problemas Comuns

**Erro: "GROQ_API_KEY not found"**
```bash
# Verificar se a variável está configurada
echo $GROQ_API_KEY
# Ou no Railway
railway variables list
```

**Erro: "LiveKit connection failed"**
```bash
# Verificar configuração do LiveKit
# 1. URL correta no formato wss://
# 2. API key e secret válidos
# 3. Projeto ativo no LiveKit Cloud
```

**Agente não responde**
```bash
# Verificar logs
railway logs
# Verificar status do agente
curl https://seu-projeto.railway.app/agents
```

### Recursos Úteis
- [Documentação LiveKit](https://docs.livekit.io/)
- [Documentação Groq](https://console.groq.com/docs)
- [Documentação Railway](https://docs.railway.app/)
- [Documentação FastAPI](https://fastapi.tiangolo.com/)

## 🎉 Conclusão

Este projeto demonstra como criar um sistema completo de agentes de voz por IA usando tecnologias modernas:

- **Groq**: Para inferência rápida de LLM
- **LiveKit**: Para comunicação em tempo real
- **Railway**: Para deploy simplificado
- **FastAPI**: Para API robusta
- **AssemblyAI**: Para transcrição de alta qualidade

O sistema é escalável, monitorável e fácil de usar, permitindo criar agentes de voz inteligentes para diversos casos de uso.

---

**Desenvolvido com ❤️ usando Groq + LiveKit + Railway** 