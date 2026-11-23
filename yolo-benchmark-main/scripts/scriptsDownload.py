import requests
import zipfile


def baixar_modelo(url, caminho_destino):

  try:
    with requests.get(url, stream=True) as resposta:
      resposta.raise_for_status()
      tamanho_total = int(resposta.headers.get("content-length", 0))
      tamanho_baixado = 0

      print(f"Iniciando download de: {url}")
      
      if tamanho_total > 0:
        print(
            f"Tamanho total: {tamanho_total / (1024 * 1024):.2f}"
            " MB\n"
        )

      with open(caminho_destino, "wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=8192):
          if bloco:  
            arquivo.write(bloco)
            tamanho_baixado += len(bloco)

            if tamanho_total > 0:    
              progresso = (tamanho_baixado / tamanho_total) * 100
    
              print(
                  f"Baixado: {tamanho_baixado / (1024 * 1024):.2f} MB"
                  f" ({progresso:.1f}%)",
                  end="\r",
              )

      print(f"\nDownload concluído com sucesso! Salvo em: {caminho_destino}")

  except requests.exceptions.RequestException as e:
    print(f"\nErro durante o download: {e}")

def baixar_dataset(url, caminho_zip, pasta_destino):  
    print(f"Baixando arquivo zip de: {url}")    
    with requests.get(url, stream=True) as resposta:
        resposta.raise_for_status()
        with open(caminho_zip, "wb") as arquivo:
            for bloco in resposta.iter_content(chunk_size=8192):
                if bloco:
                    arquivo.write(bloco)
    
    print("Download concluído!")


    print(f"Descompactando em: {pasta_destino}")
    with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
        zip_ref.extractall(pasta_destino)
    print("Descompactação concluída com sucesso!")


# Exemplo de uso:
if __name__ == "__main__":
  # URL de exemplo (substitua pela URL do arquivo grande que deseja baixar)
  url_arquivo = (
      "https://cdn.akamai.steamstatic.com/client/installer/steam.deb"  # Arquivo de teste de 100MB
  )
  arquivo_saida = "/home/pedrodias3/Desktop/steam.deb"

  baixar_modelo(url_arquivo, arquivo_saida)
  