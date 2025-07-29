#!/usr/bin/env python3
"""
Script para criar salas no LiveKit
"""
import os
import asyncio
from dotenv import load_dotenv
from livekit.api import LiveKitAPI
from livekit.protocol import room as room_proto

load_dotenv()

async def create_room(room_name: str, max_participants: int = 10):
    """Cria uma nova sala no LiveKit"""
    
    # Verificar se as variáveis de ambiente estão configuradas
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([livekit_url, api_key, api_secret]):
        print("❌ Erro: Configure as variáveis LIVEKIT_URL, LIVEKIT_API_KEY e LIVEKIT_API_SECRET")
        return False
    
    try:
        # Inicializar API do LiveKit
        lk_api = LiveKitAPI(
            url=livekit_url,
            api_key=api_key,
            api_secret=api_secret,
        )
        
        # Verificar se a sala já existe
        print(f"🔍 Verificando se a sala '{room_name}' já existe...")
        list_request = room_proto.ListRoomsRequest(names=[room_name])
        room_list = await lk_api.room.list_rooms(list_request)
        
        if room_list.rooms:
            print(f"⚠️  Sala '{room_name}' já existe!")
            room_info = room_list.rooms[0]
            print(f"   📊 Participantes: {room_info.num_participants}")
            print(f"   🕐 Criada em: {room_info.creation_time}")
            return True
        
        # Criar nova sala
        print(f"🏗️  Criando sala '{room_name}'...")
        create_request = room_proto.CreateRoomRequest(
            name=room_name,
            max_participants=max_participants,
            empty_timeout=300,  # 5 minutos para limpar sala vazia
            metadata=f"Sala criada via script - {room_name}"
        )
        
        room = await lk_api.room.create_room(create_request)
        
        print(f"✅ Sala criada com sucesso!")
        print(f"   🏷️  Nome: {room.name}")
        print(f"   🆔 SID: {room.sid}")
        print(f"   👥 Max participantes: {room.max_participants}")
        print(f"   ⏰ Timeout: {room.empty_timeout}s")
        
        # Gerar token de acesso para teste
        from livekit.api import AccessToken, VideoGrants
        
        token = AccessToken(api_key, api_secret)
        token.with_identity("test-user")
        token.with_name("Usuário Teste")
        token.with_grants(VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        
        jwt_token = token.to_jwt()
        
        print(f"\n🎫 Token de acesso gerado:")
        print(f"   URL: {livekit_url}")
        print(f"   Token: {jwt_token}")
        print(f"\n🌐 Você pode usar estes dados para conectar à sala!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar sala: {e}")
        return False

async def list_rooms():
    """Lista todas as salas existentes"""
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([livekit_url, api_key, api_secret]):
        print("❌ Erro: Configure as variáveis de ambiente")
        return
    
    try:
        lk_api = LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)
        
        print("📋 Listando todas as salas...")
        list_request = room_proto.ListRoomsRequest()
        room_list = await lk_api.room.list_rooms(list_request)
        
        if not room_list.rooms:
            print("   📭 Nenhuma sala encontrada")
            return
        
        print(f"   🏠 Total: {len(room_list.rooms)} salas")
        print()
        
        for i, room in enumerate(room_list.rooms, 1):
            print(f"   {i}. 🏷️  {room.name}")
            print(f"      🆔 SID: {room.sid}")
            print(f"      👥 Participantes: {room.num_participants}")
            print(f"      🕐 Criada: {room.creation_time}")
            print()
            
    except Exception as e:
        print(f"❌ Erro ao listar salas: {e}")

async def main():
    """Função principal"""
    print("🎤 LiveKit Room Manager")
    print("=" * 40)
    
    while True:
        print("\nOpções:")
        print("1. 🏗️  Criar nova sala")
        print("2. 📋 Listar salas existentes")
        print("3. 🚪 Sair")
        
        choice = input("\nEscolha uma opção (1-3): ").strip()
        
        if choice == "1":
            room_name = input("Digite o nome da sala: ").strip()
            if room_name:
                max_participants = input("Max participantes (padrão 10): ").strip()
                max_participants = int(max_participants) if max_participants.isdigit() else 10
                await create_room(room_name, max_participants)
            else:
                print("❌ Nome da sala não pode estar vazio")
                
        elif choice == "2":
            await list_rooms()
            
        elif choice == "3":
            print("👋 Até logo!")
            break
            
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    asyncio.run(main())
