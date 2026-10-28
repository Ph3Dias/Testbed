import requests


def baixar_arquivo_grande(url, caminho_destino):
  # O parâmetro stream=True é fundamental para não carregar o arquivo todo na RAM
  try:
    with requests.get(url, stream=True) as resposta:
      # Lança uma exceção para códigos de status HTTP ruins (4xx ou 5xx)
      resposta.raise_for_status()

      # Opcional: Pegar o tamanho total do arquivo (se o servidor enviar o header)
      tamanho_total = int(resposta.headers.get("content-length", 0))
      tamanho_baixado = 0

      print(f"Iniciando download de: {url}")
      if tamanho_total > 0:
        print(
            f"Tamanho total: {tamanho_total / (1024 * 1024):.2f}"
            " MB\n"
        )

      # Abre o arquivo local para escrita em modo binário ('wb')
      with open(caminho_destino, "wb") as arquivo:
        # Itera sobre os blocos (chunks) recebidos da rede (ex: 8 KB por vez)
        for bloco in resposta.iter_content(chunk_size=8192):
          if bloco:  # Filtra keep-alive chunks
            arquivo.write(bloco)
            tamanho_baixado += len(bloco)

            # Exibe um progresso simples no console (se soubermos o tamanho)
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


# Exemplo de uso:
if __name__ == "__main__":
  # URL de exemplo (substitua pela URL do arquivo grande que deseja baixar)
  url_arquivo = (
      "https://cdn.akamai.steamstatic.com/client/installer/steam.deb"  # Arquivo de teste de 100MB
  )
  arquivo_saida = "steam.deb"

  baixar_arquivo_grande(url_arquivo, arquivo_saida)