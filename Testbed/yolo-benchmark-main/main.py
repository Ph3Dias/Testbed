import os
import json
import time
import queue
import logger
from comunicador.consumidorServer import MQTTEventConsumer
from comunicador.produtorServer import MQTTServerPublisher

# Configurações do Broker e do Nó
BROKER_HOST = "localhost"  # Altere para o IP do seu broker MQTT
BROKER_PORT = 1883
NODE_ID = "node_01"

# Tópicos (seguindo o padrão definido no produtorServer.py)
TOPIC_COMANDOS = f"testbed/nodes/{NODE_ID}/commands"
TOPIC_CONFIRMACAO = f"testbed/nodes/{NODE_ID}/ack"

# Pastas de Modelo e Dataset
DATASET_PATH = "/home/edgeai/Desktop/testbed/Testbed/dataset/"
MODELS_PATH = "/home/edgeai/Desktop/testbed/Testbed/models/"

# ==========================================
# Funções executadas sob demanda via MQTT
# ==========================================

def start_benchmark(model_architecture, model_format, model_quant, language) -> bool:

    try:
        cmd_benchmark = f"python3 src/InferenceBenckmark/main.py "
        cmd_benchmark += f"--images_folder ${DATASET_PATH} "
        cmd_benchmark += f"--model_path ${MODELS_PATH}/{model_format}/${model_architecture}_{model_quant}.{model_format} " 
        cmd_benchmark += f"--language {language}"
        
        os.system(cmd_benchmark)
        return True
    
    except:
        logger.error("Não foi possível iniciar o benchmark")
    
    return False  

def delete_test_dataset_folder(test_id) -> bool:
    
    try:
        cmd_delete = f"cd dataset/ && rm -r {test_id}"
        os.system(cmd_delete)
    
        return True
    
    except:
        logger.error(f"Erro durante a remoção da pasta dataset/{test_id}")
    return False

def delete_test_model_folder(test_id) -> bool:
    
    try:
        cmd_delete = f"cd models/ && rm -r {test_id}"
        os.system(cmd_delete)
    
        return True
    
    except:
        logger.error(f"Erro durante a remoção da pasta models/{test_id}")
    return False


# ==========================================
# Envio de confirmação para o servidor
# ==========================================

def send_ack(publisher: MQTTServerPublisher, command: str, status: str, details=None):
    
    payload = json.dumps({
        "node_id": NODE_ID,
        "command": command,
        "status": status,
        "details": details,
        "timestamp": time.time()
    })

    if not publisher._is_connected:
        logger.error("Não foi possível enviar confirmação: Publisher desconectado.")
        return

    # Usa o client interno do publisher para enviar ao tópico de confirmação (ACK)
    
    result = publisher.client.publish(TOPIC_CONFIRMACAO, payload, qos=1)
    
    if result.rc == 0:
        logger.info(f"Confirmação enviada para '{TOPIC_CONFIRMACAO}': {payload}")
    else:
        logger.error(f"Falha ao enviar confirmação (rc: {result.rc})")



# Mapa de roteamento: liga o nome do comando à função Python
ROTAS_COMANDOS = {
    "start_benchmark": start_benchmark,
    "delete_dataset": delete_test_dataset_folder,
    "delete_model": delete_test_model_folder
}


# ==========================================
# Loop Principal
# ==========================================

def main():
    consumer = MQTTEventConsumer(
        broker_host=BROKER_HOST, # precisa alterar esses campos
        broker_port=BROKER_PORT, # precisa alterar esses campos
        client_id=f"{NODE_ID}_consumer" # precisa alterar esses campos
    )
    publisher = MQTTServerPublisher(
        broker_host=BROKER_HOST, # precisa alterar esses campos
        broker_port=BROKER_PORT, # precisa alterar esses campos
        client_id=f"{NODE_ID}_publisher" # precisa alterar esses campos
    )

    try:
        # Conecta e assina o tópico de comandos
        consumer.subscribe_topic(TOPIC_COMANDOS)
        consumer.connect()
        publisher.connect()

        logger.info(f"Nó [{NODE_ID}] pronto. Aguardando comandos em '{TOPIC_COMANDOS}'...")

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
                dados = json.loads(payload_str)
                nome_comando = dados.get("comando")
                parametros = dados.get("parametros", {})
            except json.JSONDecodeError:
                nome_comando = payload_str
                parametros = {}

            # Redireciona para a função correspondente
            funcao = ROTAS_COMANDOS.get(nome_comando)

            if not funcao:
                logger.warning(f"Comando desconhecido: '{nome_comando}'")
                enviar_confirmacao(publisher, nome_comando, "erro", "Comando não reconhecido")
                continue

            # Executa a função e envia a confirmação ao terminar
            try:
                resultado = funcao(parametros)
                enviar_confirmacao(publisher, nome_comando, "concluido", resultado)
            except Exception as e:
                logger.error(f"Erro ao executar '{nome_comando}': {e}")
                enviar_confirmacao(publisher, nome_comando, "erro", str(e))

    except KeyboardInterrupt:
        logger.info("Encerrando aplicação via teclado (Ctrl+C)...")

    finally:
        consumer.disconnect()
        publisher.disconnect()


if __name__ == "__main__":
    print(delete_test_dataset_folder("b.txt"))