import os
import json
import time
import queue
import logging  as logger# Ajustado para o módulo padrão (caso não tenha um arquivo logger.py próprio)
from comunicador.consumidorServer import MQTTEventConsumer
from comunicador.produtorServer import MQTTServerPublisher


# Configuração básica de logs
logger.basicConfig(
    level=logger.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logger.getLogger("MainNode")

# Configurações do Broker e do Nó
BROKER_HOST = "localhost"  # Altere para o IP do seu broker MQTT
BROKER_PORT = 1883
NODE_ID = "node_01" # não deve ser hard-encoded. mudar futuramente

# Tópicos (seguindo o padrão definido no produtorServer.py)
TOPIC_COMMANDS = f"testbed/nodes/{NODE_ID}/commands"
TOPIC_ACK = f"testbed/nodes/{NODE_ID}/ack"

# Pastas de Modelo e Dataset
DATASET_PATH = "/home/pi/Testbed/data/dataset/"
MODELS_PATH = "/home/pi/Testbed/data/models/"
OUTPUT_PATH = "/home/pi/Testbed/data/output/"


# ==========================================
# Funções executadas sob demanda via MQTT
# ==========================================

def start_benchmark(parameters: dict) -> bool:
    half_cores = parameters["half_cores"]
    language = parameters["language"]
    test_id = parameters["test_id"]
    architecture = parameters["architecture"]
    quant = parameters["quant"]
    fmt = parameters["format"]
    dataset_name = parameters["dataset_name"]

    model_path = f"{MODELS_PATH}/{fmt}/{architecture}_{quant}.{fmt}"
    data_path = DATASET_PATH + dataset_name
    output_path = OUTPUT_PATH + test_id

    cmd = f"python3 src/InferenceBenckmark/main.py "
    cmd += f"--images_folder ${data_path} "
    cmd+= f"--model_path ${model_path} "
    cmd += f"--language python"

    try:
        os.system(cmd)
        return True
    except Exception as e:
        logger.error(f"Não foi possível iniciar o benchmark: {e}")
        return False


def delete_test_dataset_folder(dataset_name: str) -> bool:
    try:
        cmd_delete = f"rm -rf {DATASET_PATH}{dataset_name}"
        os.system(cmd_delete)
        return True
    except Exception as e:
        logger.error(f"Erro durante a remoção da pasta {DATASET_PATH}{dataset_name}: {e}")
        return False

# Reativar função quando a opção de envio de modelo próprio for implementada
# def delete_test_model_folder(test_id: str) -> bool:
#     try:
#         cmd_delete = f"rm -rf {MODELS_PATH}{test_id}"
#         os.system(cmd_delete)
#         return True
#     except Exception as e:
#         logger.error(f"Erro durante a remoção da pasta {MODELS_PATH}{test_id}: {e}")
#         return False

def delete_test_output_folder(test_id: str) -> bool:

    try:
        cmd_delete = f"rm -rf {OUTPUT_PATH}{test_id}"
        os.system(cmd_delete)
        return True
    except Exception as e:
        logger.error(f"Erro durante a remoção da pasta {DATASET_PATH}{test_id}: {e}")
        return False


def delete_test_instance(test_id: str, dataset_name: str) -> bool:

    return delete_test_dataset_folder(dataset_name), delete_test_output_folder(test_id)


# ==========================================
# Envio de confirmação para o servidor
# ==========================================

def send_ack(publisher: MQTTServerPublisher, test_id: str, command: str, status: str, details=None):
    payload = json.dumps({
        "node_id": NODE_ID,
        "test_id": test_id,
        "command": command,
        "status": status,
        "details": details,
        "timestamp": time.time()
    })

    if not publisher._is_connected:
        logger.error("Não foi possível enviar confirmação: Publisher desconectado.")
        return

    # Usa o client interno do publisher para enviar ao tópico de confirmação (ACK)
    result = publisher.client.publish(TOPIC_ACK, payload, qos=1)
    
    if result.rc == 0:
        logger.info(f"Confirmação enviada para '{TOPIC_ACK}': {payload}")
    else:
        logger.error(f"Falha ao enviar confirmação (rc: {result.rc})")


# ==========================================1
# Loop Principal
# ==========================================

def main():
    consumer = MQTTEventConsumer(
        broker_host=BROKER_HOST,
        broker_port=BROKER_PORT,
        client_id=f"{NODE_ID}_consumer"
    )
    publisher = MQTTServerPublisher(
        broker_host=BROKER_HOST,
        broker_port=BROKER_PORT,
        client_id=f"{NODE_ID}_publisher"
    )

    try:
        # Conecta e assina o tópico de comandos
        consumer.subscribe_topic(TOPIC_COMMANDS)
        consumer.connect()
        publisher.connect()

        logger.info(f"Nó [{NODE_ID}] pronto. Aguardando comandos em '{TOPIC_COMMANDS}'...")

        while True:
            try:
                # Aguarda mensagem na fila (timeout permite capturar Ctrl+C sem travar)
                event = consumer.message_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            payload_str = event["payload_str"].strip()
            logger.info(f"Comando recebido: {payload_str}")

            # Interpreta o payload (aceita JSON ou texto simples)
            try:
                data = json.loads(payload_str)
                command_name = data.get("command")
                parameters = data.get("parameters", {})
            except json.JSONDecodeError:
                command_name = payload_str
                parameters = {}

            send_ack(publisher, command_name, "received")

            # Switch Case para redirecionar para a função correspondente
            try:
                match command_name:
                    case "start_benchmark":
                        result = start_benchmark(parameters)
                        send_ack(publisher, command_name, "Finished", result)

                    case "delete_test":
                        test_id = parameters.get("test_id")
                        result = delete_test_instance(test_id)
                        send_ack(publisher, command_name, "Finished", result)

                    case _:  # Equivalente ao 'default' do switch case
                        logger.warning(f"Comando desconhecido: '{command_name}'")
                        send_ack(publisher, command_name, "error", "Invalid Command")

            except Exception as e:
                logger.error(f"Erro ao executar '{command_name}': {e}")
                send_ack(publisher, command_name, "error", str(e))

    except KeyboardInterrupt:
        logger.info("Encerrando aplicação via teclado (Ctrl+C)...")

    finally:
        consumer.disconnect()
        publisher.disconnect()


if __name__ == "__main__":
    main()