# Dockerfile para Asterisk AI Voice System
FROM ubuntu:22.04

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    asterisk \
    asterisk-modules \
    asterisk-config \
    asterisk-core-sounds-en \
    asterisk-core-sounds-pt-br \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    wget \
    git \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário asterisk
RUN useradd -r -d /var/lib/asterisk -s /bin/bash asterisk

# Configurar diretórios
RUN mkdir -p /etc/asterisk \
    /var/lib/asterisk/agi-bin \
    /var/log/asterisk \
    /var/spool/asterisk \
    /var/run/asterisk \
    && chown -R asterisk:asterisk /var/lib/asterisk \
    && chown -R asterisk:asterisk /var/log/asterisk \
    && chown -R asterisk:asterisk /var/spool/asterisk \
    && chown -R asterisk:asterisk /var/run/asterisk

# Copiar arquivos do projeto
WORKDIR /app
COPY . /app/

# Instalar dependências Python
COPY requirements-asterisk.txt /app/
RUN pip3 install --no-cache-dir -r requirements-asterisk.txt

# Copiar configurações do Asterisk
COPY asterisk/*.conf /etc/asterisk/
COPY asterisk/agi-bin/* /var/lib/asterisk/agi-bin/
RUN chmod +x /var/lib/asterisk/agi-bin/*

# Configurar Supervisor
COPY supervisor.conf /etc/supervisor/conf.d/asterisk-ai.conf

# Criar diretório static se não existir
RUN mkdir -p /app/static

# Expor portas
EXPOSE 8000 5060/udp 10000-20000/udp

# Comando de inicialização
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
