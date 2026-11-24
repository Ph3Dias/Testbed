import logging
import paho.mqtt.client as mqtt

# Configuração básica de logs para monitorar eventos do broker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MQTTServerPublisher")

class MQTTServerPublisher:
    """
    Classe responsável por gerenciar a conexão com o broker MQTT 
    e publicar mensagens para os nós da aplicação web.
    """
    def __init__(
        self, 
        broker_host: str, 
        broker_port: int = 1883, 
        client_id: str = "web_server_publisher",
        keepalive: int = 60,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.keepalive = keepalive
        
        # Inicialização do cliente MQTT (utilizando a versão moderna da API Callback)
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        # Registro de Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        self._is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback executada quando o cliente se conecta ao broker."""
        if rc == 0:
            self._is_connected = True
            logger.info(f"Conectado com sucesso ao broker MQTT em {self.broker_host}:{self.broker_port}")
        else:
            self._is_connected = False
            logger.error(f"Falha na conexão com o broker MQTT. Código de retorno: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback executada quando a conexão é perdida."""
        self._is_connected = False
        if rc != 0:
            logger.warning(f"Conexão perdida inesperadamente com o broker MQTT (rc: {rc}). Tentando reconectar...")
        else:
            logger.info("Desconectado do broker MQTT de forma limpa.")

    def _on_publish(self, client, userdata, mid):
        """Callback executada quando uma mensagem é publicada com sucesso."""
        logger.debug(f"Mensagem (MID: {mid}) publicada com sucesso.")

    def connect(self):
        """Inicia a conexão com o broker MQTT em background."""
        try:
            logger.info(f"Conectando ao broker MQTT {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, self.keepalive)
            # Inicia o loop de rede em uma thread separada para não bloquear o servidor web
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Erro ao tentar conectar ao broker MQTT: {e}")
            raise

    def disconnect(self):
        """Encerra a conexão com o broker e para o loop de rede."""
        logger.info("Encerrando conexão com o broker MQTT...")
        self.client.loop_stop()
        self.client.disconnect()
        self._is_connected = False

    def publish_to_node(self, node_id: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        """
        Publica uma mensagem para um nó específico via tópico estruturado.
        
        Padrão de tópico adotado: 'testbed/nodes/{node_id}/command'
        """
        if not self._is_connected:
            logger.error("Falha ao publicar: Cliente não está conectado ao broker MQTT.")
            return False

        topic = f"testbed/nodes/{node_id}/command"
        
        try:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            
            # Aguarda o envio síncrono opcional ou valida o status do buffer
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Mensagem enviada para o nó [{node_id}] no tópico '{topic}'. Payload: {payload}")
                return True
            else:
                logger.error(f"Erro ao enfileirar mensagem para o nó [{node_id}]. Código: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Exceção ao publicar mensagem para o nó [{node_id}]: {e}")
            return False