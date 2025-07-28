# 🎤 LiveKit + AssemblyAI Speech-to-Text em Tempo Real

Este projeto demonstra como integrar **LiveKit** (plataforma de comunicação em tempo real) com **AssemblyAI** (API de Speech-to-Text) para criar um sistema de transcrição de áudio em tempo real.

## 📋 Visão Geral

O projeto implementa um agente de IA que:
- Conecta-se ao LiveKit para capturar streams de áudio
- Usa AssemblyAI para transcrever speech em texto em tempo real
- Publica as transcrições de volta para a sala
- Inclui recursos avançados como análise de sentimento e moderação

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   LiveKit       │    │   AI Agent      │
│   (Web App)     │◄──►│   Server        │◄──►│   (Python)      │
│                 │    │                 │    │                 │
│ - Transcrições  │    │ - WebRTC        │    │ - AssemblyAI    │
│ - Métricas      │    │ - Rooms         │    │ - Análise       │
│ - UI/UX         │    │ - Participants  │    │ - Moderação     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Funcionalidades

### ✅ Básicas
- [x] Transcrição de speech em tempo real
- [x] Integração com LiveKit
- [x] Interface web responsiva
- [x] Logging estruturado

### ✅ Avançadas
- [x] Análise de sentimento
- [x] Moderação de conteúdo
- [x] Métricas em tempo real
- [x] Logging estruturado
- [x] Configuração flexível

## 📦 Instalação

### Pré-requisitos
- Python 3.8+
- Conta no [LiveKit Cloud](https://livekit.io)
- Conta na [AssemblyAI](https://assemblyai.com) (opcional)

### 1. Clone o repositório
```bash
git clone <repository-url>
cd livekit-stt-project
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
cp env.example .env
```

Edite o arquivo `.env` com suas credenciais:
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
```

## 🎯 Como Usar

### 1. Configurar LiveKit

1. Acesse [livekit.io](https://livekit.io) e crie uma conta
2. Crie um novo projeto
3. Vá em `Settings > Keys` e copie as credenciais
4. Adicione as credenciais ao arquivo `.env`

### 2. Executar o Agente

#### Agente Básico
```bash
python stt_agent.py dev
```

#### Agente Avançado (com análise de sentimento)
```bash
python advanced_stt_agent.py dev
```

### 3. Testar com o Frontend

1. Abra `frontend_example.html` no navegador
2. Clique em "Conectar" para simular a conexão
3. Observe as transcrições em tempo real

### 4. Usar com LiveKit Agents Playground

1. Acesse [agents-playground.livekit.io](https://agents-playground.livekit.io)
2. Conecte-se à sua sala
3. Execute o agente Python
4. Fale e veja as transcrições aparecerem

## 📁 Estrutura do Projeto

```
livekit-stt-project/
├── stt_agent.py              # Agente básico de transcrição
├── advanced_stt_agent.py     # Agente avançado com análise
├── frontend_example.html     # Interface web de demonstração
├── requirements.txt          # Dependências Python
├── env.example              # Exemplo de configuração
└── README.md                # Esta documentação
```

## 🔧 Configuração Avançada

### Personalizar Análise de Sentimento

No arquivo `advanced_stt_agent.py`, você pode modificar as palavras-chave:

```python
positive_words = ["bom", "ótimo", "excelente", "gosto", "legal", "feliz"]
negative_words = ["ruim", "péssimo", "terrível", "não gosto", "triste", "raiva"]
```

### Configurar Moderação

Adicione palavras para moderação:

```python
self.moderation_words = {
    "inappropriate": ["palavrao1", "palavrao2"],
    "spam": ["spam", "promoção", "venda"]
}
```

### Logging Personalizado

Configure o nível de log:

```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🎨 Personalização do Frontend

O arquivo `frontend_example.html` inclui:

- Interface responsiva e moderna
- Métricas em tempo real
- Lista de participantes
- Análise de sentimento visual
- Controles de conexão

Para integrar com seu próprio frontend, use o SDK do LiveKit:

```javascript
import { Room, RoomEvent } from 'livekit-client';

const room = new Room();
await room.connect('your-livekit-url', 'your-token');

room.on(RoomEvent.DataReceived, (payload, participant) => {
    if (payload.topic === 'transcription') {
        console.log('Transcrição:', payload.data);
    }
});
```

## 🔍 Monitoramento e Debug

### Logs do Agente

O agente gera logs estruturados:

```
2024-01-15 10:30:15 - transcriber - INFO - Iniciando agente de transcrição para sala: meeting-room-1
2024-01-15 10:30:16 - transcriber - INFO - Transcrição completada: Olá, como vocês estão hoje?
```

### Métricas Disponíveis

- Total de transcrições
- Total de palavras
- Participantes ativos
- Duração da sessão
- Análise de sentimento
- Alertas de moderação

## 🚨 Solução de Problemas

### Erro de Conexão
```
Error: Failed to connect to LiveKit server
```
- Verifique as credenciais no arquivo `.env`
- Confirme se o LiveKit server está ativo
- Verifique a conectividade de rede

### Erro de Transcrição
```
Error: AssemblyAI API error
```
- Verifique se a chave da API está configurada
- Confirme se há créditos disponíveis na conta
- Verifique se o áudio está sendo capturado corretamente

### Performance
- Use `AutoSubscribe.AUDIO_ONLY` para economizar banda
- Configure `transcription_enabled=False` se não precisar do frontend
- Monitore o uso de CPU e memória

## 🔒 Segurança

- Nunca commite o arquivo `.env` no repositório
- Use tokens temporários para produção
- Implemente autenticação adequada
- Monitore logs para atividades suspeitas

## 📈 Próximos Passos

### Melhorias Sugeridas
- [ ] Integração com banco de dados para persistência
- [ ] API REST para consulta de transcrições
- [ ] Interface de administração
- [ ] Suporte a múltiplos idiomas
- [ ] Integração com sistemas de notificação
- [ ] Análise de sentimento mais avançada
- [ ] Detecção de emoções
- [ ] Speaker diarization

### Casos de Uso
- Reuniões corporativas com transcrição
- Eventos ao vivo com legendas
- Aplicações de acessibilidade
- Análise de call centers
- Educação online
- Podcasts com transcrição automática

## 📚 Recursos Adicionais

- [LiveKit Documentation](https://docs.livekit.io/)
- [AssemblyAI Documentation](https://www.assemblyai.com/docs)
- [LiveKit Agents Guide](https://docs.livekit.io/agents/)
- [WebRTC Fundamentals](https://webrtc.org/getting-started/overview)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙏 Agradecimentos

- [LiveKit](https://livekit.io) pela plataforma de comunicação em tempo real
- [AssemblyAI](https://assemblyai.com) pela API de Speech-to-Text
- Comunidade open source por inspiração e contribuições

---

**Desenvolvido com ❤️ para demonstrar o poder da integração LiveKit + AssemblyAI** 