import logging
import queue
import paho.mqtt.client as mqtt

# Configuração básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MQTTEventConsumer")

class MQTTEventConsumer:
    """
    Classe consumidora responsável exclusivamente por receber mensagens do broker MQTT
    e repassá-las (via fila thread-safe) para a aplicação web tratar.
    """
    def __init__(
        self, 
        broker_host: str, 
        broker_port: int = 1883, 
        client_id: str = "web_event_consumer",
        keepalive: int = 60,

    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.keepalive = keepalive
        
        # Fila thread-safe onde a aplicação web vai consumir as mensagens recebidas
        self.message_queue: queue.Queue = queue.Queue()
        
        # Lista de tópicos que devem ser assinados
        self._topics_to_subscribe = []
        
        # Inicialização do cliente MQTT
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            
        # Callbacks do MQTT
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self._is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._is_connected = True
            logger.info(f"Consumer conectado ao broker em {self.broker_host}:{self.broker_port}")
            
            # Refaz as inscrições em caso de reconexão
            for topic in self._topics_to_subscribe:
                self.client.subscribe(topic, qos=1)
                logger.info(f"Inscrição renovada no tópico: {topic}")
        else:
            self._is_connected = False
            logger.error(f"Falha na conexão do Consumer. Código: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._is_connected = False
        if rc != 0:
            logger.warning(f"Conexão perdida com o broker (rc: {rc}). Tentando reconectar...")
        else:
            logger.info("Consumer desconectado do broker de forma limpa.")

    def _on_message(self, client, userdata, msg):
        """
        Intercepta a mensagem e apenas a empacota para a fila da aplicação web,
        sem aplicar nenhuma regra de negócio aqui.
        """
        event_packet = {
            "topic": msg.topic,
            "payload": msg.payload,  # Mantém como bytes ou converte para string se preferir
            "payload_str": msg.payload.decode("utf-8", errors="ignore"),
            "qos": msg.qos,
            "retain": msg.retain
        }
        
        # Joga para a fila da aplicação web processar depois
        try:
            self.message_queue.put_nowait(event_packet)
            logger.debug(f"Mensagem do tópico '{msg.topic}' encaminhada para a fila da aplicação.")
        except queue.Full:
            logger.error("A fila interna de mensagens MQTT está cheia! Mensagem descartada.")

    def subscribe_topic(self, topic_filter: str):
        """Adiciona um tópico para monitoramento."""
        if topic_filter not in self._topics_to_subscribe:
            self._topics_to_subscribe.append(topic_filter)
            
        if self._is_connected:
            self.client.subscribe(topic_filter, qos=1)
            logger.info(f"Assinado ao novo tópico: {topic_filter}")

    def connect(self):
        """Conecta ao broker e inicia a escuta em background."""
        try:
            logger.info(f"Conectando Consumer ao broker MQTT {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, self.keepalive)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Erro ao conectar Consumer: {e}")
            raise

    def disconnect(self):
        """Encerra a conexão."""
        logger.info("Encerrando Consumer MQTT...")
        self.client.loop_stop()
        self.client.disconnect()
        self._is_connected = False