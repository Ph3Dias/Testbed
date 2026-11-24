# Testbed Inference Node

Nó de execução remoto controlado via **MQTT** para orquestração e execução de *benchmarks* de inferência e gerenciamento de diretórios de dados/saídas em ambientes de borda (como Raspberry Pi / Linux).

## Visão Geral da Arquitetura

O `main.py` atua como um nó ouvinte conectado a um *broker* MQTT:
* **Assinatura de comandos:** Escuta `testbed/nodes/<NODE_ID>/commands` e enfileira mensagens recebidas (`consumer.message_queue`).
* **Confirmação de estado (ACK):** Publica retornos em `testbed/nodes/<NODE_ID>/ack` indicando recebimento (`received`), conclusão (`Finished`) ou falha (`error`).
* **Execução sob demanda:** Dispara o módulo `start_benchmarking` (`src.InferenceBenckmark.main`) ou realiza limpeza de diretórios de dataset/saída.

---

## Tecnologias e Dependências

### Requisitos de Ambiente / Sistema
* **Python 3.10+** (utiliza sintaxe `match / case` no `main.py`).
* **Broker MQTT** acessível na rede (ex.: Eclipse Mosquitto), configurado no endereço `BROKER_HOST` e porta `BROKER_PORT` (padrão: `localhost:1883`)[cite: 1].
* **Sistema operacional tipo Unix/Linux** (os comandos de remoção usam `rm -rf` e os caminhos padrão apontam para `/home/pi/Testbed/data/...`)[cite: 1].

### Pacotes Externos (via `pip`)
Com base na lista de imports fornecida:
* `paho-mqtt` (`paho.mqtt.client`)
* `requests`
* `psutil`
* `prettytable`
* `numpy`
* `opencv-python` (`cv2`)
* `onnxruntime`
* `tqdm`

> **Nota sobre `logger`:** Na lista de imports aparece `import logger`, porém no `main.py` é utilizado o módulo padrão `logging` da biblioteca padrão do Python (com alias `logger`)[cite: 1]. Caso algum submódulo do projeto importe um pacote `logger` próprio, verifique se ele existe no caminho do projeto.

### Módulos da Biblioteca Padrão do Python (já incluídos)
`logging`, `queue`, `zipfile`, `json`, `subprocess`, `argparse`, `os`, `time`, `datetime`, `typing`, `multiprocessing`, `dataclasses`.

### Módulos Internos do Projeto
* `comunicador.consumidorServer` (`MQTTEventConsumer`)[cite: 1]
* `comunicador.produtorServer` (`MQTTServerPublisher`)[cite: 1]
* `src.InferenceBenckmark.main` (`start_benchmarking`)[cite: 1]

---

## Instalação

1. **Clone ou acesse o repositório do projeto:**
   ```bash
   cd /caminho/do/projeto