"""Async"""
import logging
import subprocess
import threading
import uuid
from time import sleep
from typing import Tuple
from pydantic import AmqpDsn

import pika

from models.requests import ForecastRequest


class AMQPRPCClient:
    """This publisher will send out messages to the specified fanout exchange"""
    __internal_lock = threading.Lock()
    responses = {}
    events = {}

    def __init__(self, amqp_url, exchange_name):
        """Create a new MessagePublisher

        :param amqp_url: AMQP URL specifying the connection details
        :param exchange_name: Name of the exchange the requests should be published to
        """
        self.__amqp_url: AmqpDsn = amqp_url
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
        self.__channel.exchange_declare(self.__exchange_name, exchange_type='fanout')
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
            self.__msg_callback_queue,
            self.__on_message_received,
            auto_ack=False,
            exclusive=True
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
        print(content)
        self.responses[properties.correlation_id] = content.decode('utf-8')
        print(self.responses[properties.correlation_id])
        self.__channel.basic_ack(method.delivery_tag)
        event: threading.Event = self.events[properties.correlation_id]
        event.set()

    def publish_message(self, message: str) -> Tuple[str, threading.Event]:
        """Publish a new message in the exchange for the calculation module

        :param message: The message that shall be transmitted
        :return: The correlation id used to send the message
        """
        __correlation_id = 'request#' + str(uuid.uuid4())
        __message_received_event = threading.Event()
        self.responses[__correlation_id] = None
        self.events[__correlation_id] = __message_received_event
        with self.__internal_lock:
            self.__channel.basic_publish(
                exchange=self.__exchange_name,
                routing_key='',
                properties=pika.BasicProperties(
                    reply_to=self.__msg_callback_queue,
                    correlation_id=__correlation_id
                ),
                body=message.encode('utf-8')
            )
            self.__logger.info('Published message')
        return __correlation_id, __message_received_event

