#!/bin/bash

# 🚀 Script de Deploy para LiveKit AI Voice Agents
# Este script automatiza o processo de deploy no Railway

set -e  # Parar em caso de erro

echo "🎤 LiveKit AI Voice Agents - Deploy Script"
echo "=========================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se o Railway CLI está instalado
check_railway_cli() {
    print_status "Verificando Railway CLI..."
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI não encontrado!"
        echo "Instale com: npm install -g @railway/cli"
        exit 1
    fi
    print_success "Railway CLI encontrado"
}

# Verificar se está logado no Railway
check_railway_login() {
    print_status "Verificando login no Railway..."
    if ! railway whoami &> /dev/null; then
        print_warning "Não logado no Railway. Fazendo login..."
        railway login
    fi
    print_success "Logado no Railway"
}

# Verificar arquivo .env
check_env_file() {
    print_status "Verificando arquivo .env..."
    if [ ! -f ".env" ]; then
        print_warning "Arquivo .env não encontrado. Criando a partir do exemplo..."
        if [ -f "env.example" ]; then
            cp env.example .env
            print_success "Arquivo .env criado. Por favor, configure suas variáveis de ambiente."
            print_warning "Edite o arquivo .env com suas chaves de API antes de continuar."
            exit 1
        else
            print_error "Arquivo env.example não encontrado!"
            exit 1
        fi
    fi
    print_success "Arquivo .env encontrado"
}

# Verificar dependências Python
check_python_deps() {
    print_status "Verificando dependências Python..."
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt não encontrado!"
        exit 1
    fi
    
    # Verificar se pip está disponível
    if ! command -v pip &> /dev/null; then
        print_error "pip não encontrado! Instale Python e pip primeiro."
        exit 1
    fi
    
    print_success "Dependências Python verificadas"
}

# Instalar dependências
install_dependencies() {
    print_status "Instalando dependências Python..."
    pip install -r requirements.txt
    print_success "Dependências instaladas"
}

# Inicializar projeto Railway
init_railway_project() {
    print_status "Inicializando projeto Railway..."
    
    # Verificar se já existe um projeto
    if [ -f ".railway" ]; then
        print_warning "Projeto Railway já inicializado"
        return
    fi
    
    railway init
    print_success "Projeto Railway inicializado"
}

# Configurar variáveis de ambiente no Railway
setup_railway_variables() {
    print_status "Configurando variáveis de ambiente no Railway..."
    
    # Carregar variáveis do arquivo .env
    if [ -f ".env" ]; then
        while IFS='=' read -r key value; do
            # Ignorar linhas vazias e comentários
            if [[ ! -z "$key" && ! "$key" =~ ^# ]]; then
                # Remover espaços e aspas
                key=$(echo "$key" | xargs)
                value=$(echo "$value" | xargs | sed 's/^"//;s/"$//')
                
                if [ ! -z "$key" ] && [ ! -z "$value" ]; then
                    print_status "Configurando $key..."
                    railway variables set "$key=$value" || print_warning "Erro ao configurar $key"
                fi
            fi
        done < .env
    fi
    
    print_success "Variáveis de ambiente configuradas"
}

# Fazer deploy
deploy_to_railway() {
    print_status "Fazendo deploy no Railway..."
    railway up
    print_success "Deploy concluído!"
}

# Obter URL do projeto
get_project_url() {
    print_status "Obtendo URL do projeto..."
    PROJECT_URL=$(railway status --json | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    if [ ! -z "$PROJECT_URL" ]; then
        print_success "Projeto disponível em: $PROJECT_URL"
        echo ""
        echo "🔗 Links úteis:"
        echo "   API: $PROJECT_URL"
        echo "   Dashboard: $PROJECT_URL/frontend_management.html"
        echo "   Docs: $PROJECT_URL/docs"
        echo "   Health: $PROJECT_URL/health"
    else
        print_warning "Não foi possível obter a URL do projeto"
    fi
}

# Testar a aplicação
test_application() {
    print_status "Testando aplicação..."
    
    if [ ! -z "$PROJECT_URL" ]; then
        # Testar endpoint de saúde
        if curl -s "$PROJECT_URL/health" > /dev/null; then
            print_success "Aplicação está funcionando!"
        else
            print_warning "Aplicação pode não estar respondendo ainda. Aguarde alguns minutos."
        fi
    fi
}

# Função principal
main() {
    echo ""
    print_status "Iniciando processo de deploy..."
    echo ""
    
    # Verificações
    check_railway_cli
    check_railway_login
    check_env_file
    check_python_deps
    
    echo ""
    print_status "Instalando dependências..."
    install_dependencies
    
    echo ""
    print_status "Configurando Railway..."
    init_railway_project
    setup_railway_variables
    
    echo ""
    print_status "Fazendo deploy..."
    deploy_to_railway
    
    echo ""
    get_project_url
    
    echo ""
    print_status "Testando aplicação..."
    test_application
    
    echo ""
    print_success "🎉 Deploy concluído com sucesso!"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Acesse o dashboard para gerenciar agentes"
    echo "   2. Configure suas chaves de API no Railway"
    echo "   3. Teste os agentes de voz"
    echo "   4. Monitore os logs com: railway logs"
    echo ""
    echo "🔧 Comandos úteis:"
    echo "   railway logs          # Ver logs em tempo real"
    echo "   railway status        # Status do projeto"
    echo "   railway variables     # Listar variáveis"
    echo "   railway open          # Abrir no navegador"
    echo ""
}

# Verificar argumentos
case "${1:-}" in
    --help|-h)
        echo "Uso: $0 [opção]"
        echo ""
        echo "Opções:"
        echo "  --help, -h     Mostrar esta ajuda"
        echo "  --check        Apenas verificar dependências"
        echo "  --deploy       Apenas fazer deploy"
        echo ""
        echo "Exemplos:"
        echo "  $0              # Deploy completo"
        echo "  $0 --check      # Verificar dependências"
        echo "  $0 --deploy     # Deploy sem verificações"
        exit 0
        ;;
    --check)
        print_status "Verificando dependências..."
        check_railway_cli
        check_railway_login
        check_env_file
        check_python_deps
        print_success "Todas as verificações passaram!"
        exit 0
        ;;
    --deploy)
        print_status "Deploy direto..."
        deploy_to_railway
        get_project_url
        test_application
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Opção desconhecida: $1"
        echo "Use --help para ver as opções disponíveis"
        exit 1
        ;;
esac 