import os

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def baixar_episodios():
    limpar_tela()
    print("Executando script para baixar episódios específicos...")
    os.system('python3 Code/episodio.py')
    input("\nPressione Enter para voltar ao menu...")

def baixar_anime_completo():
    limpar_tela()
    print("Executando script para baixar um anime completo...")
    os.system('python3 Code/anime.py')
    input("\nPressione Enter para voltar ao menu...")

def buscar_anime():
    limpar_tela()
    print("Executando script de busca...")
    os.system('python3 Code/buscar.py')
    input("\nPressione Enter para voltar ao menu...")

def verificar_instalar_dependencias():
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("Bibliotecas necessárias não encontradas.")
        choice = input("Deseja instalar as bibliotecas necessárias? (s/n): ").strip().lower()
        if choice == 's':
            os.system('pip3 install -r requirements.txt')
        else:
            print("Instalação cancelada.")
            input("\nPressione Enter para continuar...")

def menu():
    verificar_instalar_dependencias()

    while True:
        limpar_tela()
        print("""
ANIMEOUT Downloader

1 - Buscar anime
2 - Baixar episódios
3 - Baixar anime completo
4 - Sair
""")
        opcao = input("Escolha: ")

        if opcao == '1':
            buscar_anime()
        elif opcao == '2':
            baixar_episodios()
        elif opcao == '3':
            baixar_anime_completo()
        elif opcao == '4':
            break

if __name__ == "__main__":
    menu()
