# Testbed Inference Node

Nó de execução remoto controlado via **MQTT** para orquestração e execução de *benchmarks* de inferência e gerenciamento de diretórios de dados/saídas em ambientes de borda (como Raspberry Pi / Linux).

---

## Visão Geral da Arquitetura

O `main.py` atua como um nó ouvinte conectado a um *broker* MQTT:
* **Assinatura de comandos:** Escuta `testbed/nodes/<NODE_ID>/commands` e enfileira mensagens recebidas (`consumer.message_queue`).
* **Confirmação de estado (ACK):** Publica retornos em `testbed/nodes/<NODE_ID>/ack` indicando recebimento (`received`), conclusão (`Finished`) ou falha (`error`).
* **Execução sob demanda:** Dispara o módulo `start_benchmarking` (`src.InferenceBenckmark.main`) ou realiza limpeza de diretórios de dataset/saída.

---

## Tecnologias e Dependências

### 1. Requisitos de Sistema e Infraestrutura
* **Sistema Operacional:** Linux / Unix-like (ex.: Raspberry Pi OS, Ubuntu, Debian). Os comandos de limpeza utilizam `rm -rf` e os caminhos padrão apontam para `/home/pi/Testbed/data/...`.
* **Python 3.10 ou superior:** Obrigatório devido ao uso da instrução estrutural `match / case` no `main.py`.
* **Broker MQTT:** Servidor MQTT ativo na rede (ex.: **Eclipse Mosquitto**), acessível pelo IP e porta configurados em `BROKER_HOST` e `BROKER_PORT` (padrão: `localhost:1883`).

### 2. Bibliotecas Externas (PyPI / `pip`)

| Pacote (`pip`) | Módulo Importado | Finalidade no Projeto |
| :--- | :--- | :--- |
| `paho-mqtt` | `paho.mqtt.client` | Comunicação cliente MQTT (assinatura de comandos e publicação de ACKs). |
| `onnxruntime` | `onnxruntime` | Motor de execução e inferência dos modelos no formato `.onnx`. |
| `opencv-python` | `cv2` | Leitura, redimensionamento e pré-processamento de imagens dos datasets. |
| `numpy` | `numpy` | Manipulação de tensores, arrays multidimensionais e métricas numéricas. |
| `psutil` | `psutil` | Monitoramento de hardware (uso de CPU, memória e afinidade de núcleos). |
| `requests` | `requests` | Requisições HTTP (download de modelos, datasets ou envio de resultados). |
| `prettytable` | `prettytable` | Formatação tabular de relatórios e métricas no terminal/logs. |
| `tqdm` | `tqdm` | Exibição de barras de progresso durante loops de inferência ou downloads. |

> **Observação sobre `logger`:** Na lista de imports consta `import logger`, enquanto o `main.py` utiliza `import logging as logger` (biblioteca nativa). Caso exista um arquivo `logger.py` customizado dentro de algum submódulo do projeto, mantenha-o no `PYTHONPATH`; caso contrário, nenhuma instalação externa é necessária.

### 3. Módulos Nativos do Python (Biblioteca Padrão)
Não exigem instalação separada:
`logging`, `queue`, `zipfile`, `json`, `subprocess`, `argparse`, `os`, `time`, `datetime`, `typing`, `multiprocessing`, `dataclasses`.

### 4. Módulos Internos do Projeto
Devem estar presentes na estrutura de pastas do repositório:
* `comunicador/consumidorServer.py` (`MQTTEventConsumer`)
* `comunicador/produtorServer.py` (`MQTTServerPublisher`)
* `src/InferenceBenckmark/main.py` (`start_benchmarking`)

---

## Guia de Instalação Passo a Passo

### Passo 1: Atualizar o sistema e instalar dependências base (Linux / Raspberry Pi OS)
Algumas bibliotecas como `opencv-python` e `onnxruntime` exigem bibliotecas nativas do sistema operacional para manipulação de imagens e álgebra linear:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv libgl1 libglib2.0-0 libgomp1
```

### Passo 2: Instalar o Broker MQTT (Mosquitto) — *Opcional no nó*
Caso este dispositivo também hospede o *broker* MQTT (ou para testes locais com `mosquitto_pub`/`mosquitto_sub`):

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Passo 3: Criar e ativar um Ambiente Virtual (`venv`)
Isolar as dependências evita conflitos com pacotes do sistema operacional:

```bash
cd /caminho/do/seu/projeto
python3 -m venv .venv
source .venv/bin/activate
```

Atualize o `pip` antes de instalar os pacotes:
```bash
pip install --upgrade pip
```

### Passo 4: Instalar as bibliotecas Python
Instale todas as dependências necessárias de uma vez:

```bash
pip install paho-mqtt requests psutil prettytable numpy opencv-python onnxruntime tqdm
```

> **Dica para Raspberry Pi (ARM / 32-bit ou 64-bit):**
> * Se ocorrer erro ao compilar `opencv-python`, utilize a versão sem interface gráfica:
>   ```bash
>   pip install opencv-python-headless
>   ```
> * Certifique-se de utilizar sistema operacional **64-bit (`aarch64`)** para compatibilidade direta com os binários oficiais do `onnxruntime`.

### Passo 5: Validar a instalação
Execute o comando abaixo no terminal (com o ambiente virtual ativo) para confirmar que todas as bibliotecas foram carregadas sem erros:

```bash
python3 -c "import paho.mqtt.client, requests, psutil, prettytable, numpy, cv2, onnxruntime, tqdm; print('Todas as dependências foram instaladas com sucesso!')"
```

### Passo 6: Configurar diretórios e parâmetros do nó
Crie as pastas padrão configuradas no `main.py`:

```bash
mkdir -p /home/pi/Testbed/data/dataset
mkdir -p /home/pi/Testbed/data/models
mkdir -p /home/pi/Testbed/data/output
```

Em seguida, edite as constantes no início do arquivo `main.py` conforme a sua rede:
```python
BROKER_HOST = "localhost"  # IP do servidor Broker MQTT
BROKER_PORT = 1883
NODE_ID = "node_01"        # Identificador único deste nó
```

---

## Como Utilizar

### 1. Iniciar o Nó de Execução
Com o ambiente virtual ativado, inicie o script principal:

```bash
python3 main.py
```

Saída esperada no terminal:
```text
2026-11-24 12:00:00,000 [INFO] MainNode: Nó [node_01] pronto. Aguardando comandos em 'testbed/nodes/node_01/commands'...
```

Para encerrar a execução com segurança e desconectar os clientes MQTT, pressione `Ctrl + C`.

---

### 2. Comandos Suportados via MQTT

Os comandos devem ser enviados em formato **JSON** para o tópico `testbed/nodes/<NODE_ID>/commands`.

#### A) Iniciar Benchmark (`start_benchmark`)
O nó busca o modelo seguindo o padrão `<MODELS_PATH>/<format>/<architecture>_<quant>.<format>`, lê os dados em `<DATASET_PATH><dataset_name>` e grava os resultados em `<OUTPUT_PATH><test_id>`.

* **Tópico:** `testbed/nodes/node_01/commands`
* **Payload:**
```json
{
  "command": "start_benchmark",
  "parameters": {
    "test_id": "exp_001",
    "half_cores": false,
    "language": "python",
    "architecture": "resnet50",
    "quant": "fp32",
    "format": "onnx",
    "dataset_name": "imagenet_sample"
  }
}
```
* **Exemplo via terminal (`mosquitto_pub`):**
```bash
mosquitto_pub -h localhost -p 1883 -t "testbed/nodes/node_01/commands" -m '{"command": "start_benchmark", "parameters": {"test_id": "exp_001", "half_cores": false, "language": "python", "architecture": "resnet50", "quant": "fp32", "format": "onnx", "dataset_name": "imagenet_sample"}}'
```

#### B) Remover Instância de Teste (`delete_test`)
Remove tanto a pasta do dataset em `<DATASET_PATH><dataset_name>` quanto a pasta de saída gerada em `<OUTPUT_PATH><test_id>` (via `delete_instance_test`).

* **Tópico:** `testbed/nodes/node_01/commands`
* **Payload:**
```json
{
  "command": "delete_test",
  "parameters": {
    "test_id": "exp_001",
    "dataset_name": "imagenet_sample"
  }
}
```
* **Exemplo via terminal (`mosquitto_pub`):**
```bash
mosquitto_pub -h localhost -p 1883 -t "testbed/nodes/node_01/commands" -m '{"command": "delete_test", "parameters": {"test_id": "exp_001", "dataset_name": "imagenet_sample"}}'
```

---

### 3. Monitoramento de Confirmações (ACK)

O nó publica mensagens de status no tópico `testbed/nodes/<NODE_ID>/ack` em três momentos:
1. **`received`**: Assim que o comando é recebido da fila.
2. **`Finished`**: Quando a execução conclui (o campo `details` retorna o resultado da operação).
3. **`error`**: Caso o comando seja inválido ou ocorra alguma exceção durante a execução.

Para acompanhar as respostas em tempo real:
```bash
mosquitto_sub -h localhost -p 1883 -t "testbed/nodes/node_01/ack"
```

Exemplo de retorno:
```json
{
  "node_id": "node_01",
  "test_id": "start_benchmark",
  "command": "Finished",
  "status": true,
  "details": null,
  "timestamp": 1795520000.0
}
```