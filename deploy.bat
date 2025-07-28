@echo off
setlocal enabledelayedexpansion

REM 🚀 Script de Deploy para LiveKit AI Voice Agents (Windows)
REM Este script automatiza o processo de deploy no Railway

echo 🎤 LiveKit AI Voice Agents - Deploy Script
echo ==========================================

REM Verificar se o Railway CLI está instalado
echo [INFO] Verificando Railway CLI...
railway --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Railway CLI não encontrado!
    echo Instale com: npm install -g @railway/cli
    pause
    exit /b 1
)
echo [SUCCESS] Railway CLI encontrado

REM Verificar se está logado no Railway
echo [INFO] Verificando login no Railway...
railway whoami >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Não logado no Railway. Fazendo login...
    railway login
)
echo [SUCCESS] Logado no Railway

REM Verificar arquivo .env
echo [INFO] Verificando arquivo .env...
if not exist ".env" (
    echo [WARNING] Arquivo .env não encontrado. Criando a partir do exemplo...
    if exist "env.example" (
        copy env.example .env >nul
        echo [SUCCESS] Arquivo .env criado. Por favor, configure suas variáveis de ambiente.
        echo [WARNING] Edite o arquivo .env com suas chaves de API antes de continuar.
        pause
        exit /b 1
    ) else (
        echo [ERROR] Arquivo env.example não encontrado!
        pause
        exit /b 1
    )
)
echo [SUCCESS] Arquivo .env encontrado

REM Verificar dependências Python
echo [INFO] Verificando dependências Python...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt não encontrado!
    pause
    exit /b 1
)

REM Verificar se pip está disponível
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip não encontrado! Instale Python e pip primeiro.
    pause
    exit /b 1
)
echo [SUCCESS] Dependências Python verificadas

REM Instalar dependências
echo [INFO] Instalando dependências Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Erro ao instalar dependências!
    pause
    exit /b 1
)
echo [SUCCESS] Dependências instaladas

REM Inicializar projeto Railway
echo [INFO] Inicializando projeto Railway...
if not exist ".railway" (
    railway init
    if errorlevel 1 (
        echo [ERROR] Erro ao inicializar projeto Railway!
        pause
        exit /b 1
    )
    echo [SUCCESS] Projeto Railway inicializado
) else (
    echo [WARNING] Projeto Railway já inicializado
)

REM Configurar variáveis de ambiente no Railway
echo [INFO] Configurando variáveis de ambiente no Railway...
if exist ".env" (
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            echo [INFO] Configurando %%a...
            railway variables set "%%a=%%b" >nul 2>&1
            if errorlevel 1 (
                echo [WARNING] Erro ao configurar %%a
            )
        )
    )
)
echo [SUCCESS] Variáveis de ambiente configuradas

REM Fazer deploy
echo [INFO] Fazendo deploy no Railway...
railway up
if errorlevel 1 (
    echo [ERROR] Erro no deploy!
    pause
    exit /b 1
)
echo [SUCCESS] Deploy concluído!

REM Obter URL do projeto
echo [INFO] Obtendo URL do projeto...
for /f "tokens=*" %%i in ('railway status --json 2^>nul ^| findstr /C:"url"') do (
    set "status_line=%%i"
    for /f "tokens=2 delims=:," %%j in ("!status_line!") do (
        set "project_url=%%j"
        set "project_url=!project_url:"=!"
        set "project_url=!project_url: =!"
    )
)

if defined project_url (
    echo [SUCCESS] Projeto disponível em: !project_url!
    echo.
    echo 🔗 Links úteis:
    echo    API: !project_url!
    echo    Dashboard: !project_url!/frontend_management.html
    echo    Docs: !project_url!/docs
    echo    Health: !project_url!/health
) else (
    echo [WARNING] Não foi possível obter a URL do projeto
)

REM Testar a aplicação
echo [INFO] Testando aplicação...
if defined project_url (
    curl -s "!project_url!/health" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Aplicação pode não estar respondendo ainda. Aguarde alguns minutos.
    ) else (
        echo [SUCCESS] Aplicação está funcionando!
    )
)

echo.
echo [SUCCESS] 🎉 Deploy concluído com sucesso!
echo.
echo 📋 Próximos passos:
echo    1. Acesse o dashboard para gerenciar agentes
echo    2. Configure suas chaves de API no Railway
echo    3. Teste os agentes de voz
echo    4. Monitore os logs com: railway logs
echo.
echo 🔧 Comandos úteis:
echo    railway logs          # Ver logs em tempo real
echo    railway status        # Status do projeto
echo    railway variables     # Listar variáveis
echo    railway open          # Abrir no navegador
echo.

pause 