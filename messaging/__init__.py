"""Async"""
import logging
import threading
import uuid
from time import sleep

import pika

from models.requests import ForecastRequest


class AMQPRPCClient:
    """This publisher will send out messages to the specified fanout exchange"""
    __internal_lock = threading.Lock()
    responses = {}

    def __init__(self, amqp_url, exchange_name):
        """Create a new MessagePublisher

        :param amqp_url: AMQP URL specifying the connection details
        :param exchange_name: Name of the exchange the requests should be published to
        """
        self.__amqp_url = amqp_url
        self.__exchange_name = exchange_name

        # Create a Logger for the Publisher
        self.__logger = logging.getLogger(__name__)

        # Create connection parameters
        connection_parameters = pika.URLParameters(self.__amqp_url)
        connection_parameters.client_properties = {
            'connection_name': 'water-usage-forecasts#' + str(uuid.uuid1())
        }
        # Create a connection
        self.__connection = pika.BlockingConnection(
            parameters=connection_parameters
        )
        # Open a channel and generate a unique and exclusive queue to which there should be answers
        self.__channel = self.__connection.channel()
        self.__queue = self.__channel.queue_declare('', exclusive=True, auto_delete=True)
        self.__msg_callback_queue = self.__queue.method.queue

        # Create a thread which will check for incoming data events and handle those
        self.__thread = threading.Thread(target=self.__process_data_events)
        self.__thread.setDaemon(True)
        # Start the message receiving thread
        self.__thread.start()

    def __process_data_events(self):
        """Check for new incoming data"""
        self.__channel.basic_consume(
            self.__msg_callback_queue, self.__on_message_received, auto_ack=False
        )

        while True:
            with self.__internal_lock:
                self.__connection.process_data_events()
                sleep(0.1)

    def __on_message_received(
            self,
            channel: pika.spec.Channel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            content: bytes
    ):
        """Handle the received message by adding it to the stack of responses

        :param channel:
        :param method:
        :param properties:
        :param content:
        :return:
        """
        self.responses[properties.correlation_id] = content
        self.__channel.basic_ack(method.delivery_tag)

    def publish_message(self, request: ForecastRequest) -> str:
        """Publish a new message in the exchange for the calculation module

        :param request:
        :return: The correlation id used to send the message
        """
        __correlation_id = 'request#' + str(uuid.uuid4())
        self.responses[__correlation_id] = None
        with self.__internal_lock:
            self.__channel.basic_publish(
                exchange=self.__exchange_name,
                routing_key='',
                properties=pika.BasicProperties(
                    reply_to=self.__msg_callback_queue,
                    correlation_id=__correlation_id
                ),
                body=request.json(by_alias=True).encode('utf-8')
            )
            self.__logger.info('Published message')
        return __correlation_id
