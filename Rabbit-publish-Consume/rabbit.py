import functools
import logging
import json
import time
from enum import Enum

import pika
from pika.exchange_type import ExchangeType
from pika import exceptions as pika_exceptions

LOGGER = logging.getLogger(__name__)


class ExchangeTypeEnum(Enum):
    DEFAULT = ""
    DIRECT = ExchangeType.direct.name
    TOPIC = ExchangeType.topic.name
    FANOUT = ExchangeType.fanout.name


class ContentType(Enum):
    JSON = "application/json"
    TEXT = "text/plain"


class DeliveryMode(Enum):
    NOT_PERSIST = 1
    PERSIST = 2


class RabbitReconnecting(object):
    RETRYING_MAX_ATTEMPTS = 3
    RETRYING_ATTEMPTS = 0
    SLEEP_BETWEEN_ATTEMPTS = 10
    _url = None

    def __init__(self, user_name: str, password: str, host: str, port: int, key_values: list[list[str]] = [],
                 virtual_host: str = "%2F"):
        self._url = self._param_to_url(user_name, password, host, port, virtual_host, key_values)

    @staticmethod
    def _param_to_url(user_name, password, host, port, virtual_host: str, key_values: list[list[str]]):
        url = 'amqp://' + user_name + ":" + str(password) + "@" + host + ":" + str(port) + "/" + virtual_host
        for i, key_value in enumerate(key_values):
            if i == 0:
                connector = "?"
            else:
                connector = "&"
            url = url + connector + key_value[0] + "=" + str(key_value[1])
        return url


class RabbitBlockPublisher(RabbitReconnecting):
    # we get queues as list, because 1)maybe publisher must publish to multiple queues 2) could declare all queues
    # later in class
    is_message_persisted = False

    def __init__(self, exchange: str, exchange_type: ExchangeTypeEnum, queue: list[str],
                 routing_key: str, amqp_url: str = None, user_name: str = None, password: str = None, host: str = None,
                 port: int = None, key_values: list[list[str]] = [],
                 virtual_host: str = "%2F"):
        self._connection = None
        self._channel = None
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key = routing_key
        self._url = amqp_url
        self.properties = pika.BasicProperties()
        if amqp_url is None:
            try:
                super().__init__(user_name, password, host, port, key_values, virtual_host)
            except TypeError as e:
                LOGGER.error(f"Must Define Url Or Other Connections Parameters")
                raise e

    def _connect(self):
        try:
            LOGGER.info('Connecting to %s', self._url)
            self._connection = pika.BlockingConnection(
                parameters=pika.URLParameters(self._url)
            )
        except pika_exceptions.AMQPConnectionError as e:
            LOGGER.warning(f'#{self.RETRYING_ATTEMPTS + 1} attempt for connecting url: {self._url} failed!')
            LOGGER.warning(f"reconnecting in {self.SLEEP_BETWEEN_ATTEMPTS}s ...")
            time.sleep(self.SLEEP_BETWEEN_ATTEMPTS)
            self.RETRYING_ATTEMPTS += 1
            if self.RETRYING_ATTEMPTS <= self.RETRYING_MAX_ATTEMPTS:
                self._connect()
            else:
                LOGGER.error(f"Can Not Connect To RabbitMQ with url: {self._url}")
                raise ConnectionError(f"Can Not Connect To RabbitMQ with url: {self._url}")

    def set_message_content(self, content_type: ContentType):
        self.properties.content_type = content_type.value

    def set_message_delivery_mode(self, delivery_mode: DeliveryMode):
        self.properties.delivery_mode = delivery_mode.value
        self.is_message_persisted = True

    def _create_channel(self):
        LOGGER.info('Creating Channel')
        self._channel = self._connection.channel()

    def _declare_queue(self, queue: str, durable: bool):
        LOGGER.info(f'Declaring queue: {queue}, durable: {durable}')
        if durable != self.is_message_persisted:
            LOGGER.warning(
                f"queue durable: {durable} and message persistent: {self.is_message_persisted} so message does not write to disk")

        self._channel.queue_declare(queue, durable=durable)

    def _declare_exchange(self):
        LOGGER.info(f'Declaring exchange: {self.exchange} with type: {self.exchange_type}')
        self._channel.exchange_declare(self.exchange, self.exchange_type)

    def _bind_queue(self, queue):
        LOGGER.info(f'Binding queue: {queue} to exchange: {self.exchange} with key: {self.routing_key}')
        self._channel.queue_bind(queue, self.exchange, self.routing_key)

    def publish(self, message):
        LOGGER.info(f'Publishing {str(message)[:20]} ... to exchange: {self.exchange} with key: {self.routing_key}')
        self._channel.basic_publish(exchange=self.exchange, routing_key=self.routing_key, body=message, properties=self.properties)

    def run(self, durable: bool = False):
        self._connect()
        self._create_channel()
        self._declare_exchange()
        for queue in self.queue:
            self._declare_queue(queue, durable)
            self._bind_queue(queue)


class RabbitIntervalPublisher(RabbitReconnecting):
    PUBLISH_INTERVAL = 10
    should_delivery_confirmation = False
    is_message_persisted = False

    def __init__(self, exchange: str, exchange_type: ExchangeTypeEnum, queue: str, routing_key: str,
                 message_function, amqp_url: str = None, user_name: str = None, password: str = None, host: str = None,
                 port: int = None, key_values: list[list[str]] = [],
                 virtual_host: str = "%2F"):
        self.durable = False
        self._connection = None
        self._channel = None
        self._deliveries = None
        self._acked = None
        self._nacked = None
        self._message_number = None
        self._stopping = False
        self._url = amqp_url
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key = routing_key
        self.message_function = message_function
        self.properties = pika.BasicProperties()
        if amqp_url is None:
            try:
                super().__init__(user_name, password, host, port, key_values, virtual_host)
            except TypeError as e:
                LOGGER.error(f"Must Define Url Or Other Connections Parameters")
                raise e

    def should_confirm_delivery(self, should_delivery_confirmation: bool):
        self.should_delivery_confirmation = should_delivery_confirmation

    def set_message_content(self, content_type: ContentType):
        self.properties.content_type = content_type.value

    def set_message_delivery_mode(self, delivery_mode: DeliveryMode):
        self.properties.delivery_mode = delivery_mode.value
        self.is_message_persisted = True

    def connect(self):
        LOGGER.info('Connecting to %s', self._url)
        return pika.SelectConnection(
            parameters=pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def on_connection_open(self, _unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.warning(f'Connection open failed, reopening in  seconds:{self.SLEEP_BETWEEN_ATTEMPTS}')
        if self.RETRYING_ATTEMPTS <= self.RETRYING_MAX_ATTEMPTS:
            self._connection.ioloop.call_later(self.SLEEP_BETWEEN_ATTEMPTS, self._connection.ioloop.stop)
        else:
            LOGGER.error(f"Can Not Connect To RabbitMQ with url: {self._url}")
            raise ConnectionError(f"Can Not Connect To RabbitMQ with url: {self._url}")
        self.RETRYING_ATTEMPTS += 1

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: %s',
                           reason)
            self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def open_channel(self):
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.exchange)

    def add_on_channel_close_callback(self):
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange %s', exchange_name)
        cb = functools.partial(self.on_exchange_declareok,
                               userdata=exchange_name)
        self._channel.exchange_declare(exchange=exchange_name,
                                       exchange_type=self.exchange_type,
                                       callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info('exchange declared: %s', userdata)
        self.setup_queue(self.queue)

    def setup_queue(self, queue_name: str):
        if self.durable != self.is_message_persisted:
            LOGGER.warning(
                f"queue durable: {self.durable} and message persistent: {self.is_message_persisted} so message does not write to disk")
        LOGGER.info('Declaring queue %s,  durable %s', queue_name, self.durable)
        self._channel.queue_declare(queue=queue_name, durable=self.durable,
                                    callback=self.on_queue_declareok)

    def on_queue_declareok(self, _unused_frame):
        LOGGER.info('Binding %s to %s with %s', self.exchange, self.queue,
                    self.routing_key)
        self._channel.queue_bind(self.queue,
                                 self.exchange,
                                 routing_key=self.routing_key,
                                 callback=self.on_bindok)

    def on_bindok(self, _unused_frame):
        LOGGER.info('queue bound')
        self.start_publishing()

    def start_publishing(self):
        LOGGER.info('Issuing consumer related RPC commands')
        if self.should_delivery_confirmation:
            self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        LOGGER.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        ack_multiple = method_frame.method.multiple
        delivery_tag = method_frame.method.delivery_tag

        LOGGER.info('Received %s for delivery tag: %i (multiple: %s)',
                    confirmation_type, delivery_tag, ack_multiple)

        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1

        del self._deliveries[delivery_tag]

        if ack_multiple:
            for tmp_tag in list(self._deliveries.keys()):
                if tmp_tag <= delivery_tag:
                    self._acked += 1
                    del self._deliveries[tmp_tag]

        LOGGER.info(
            'Published %i messages, %i have yet to be confirmed, '
            '%i were acked and %i were nacked', self._message_number,
            len(self._deliveries), self._acked, self._nacked)

    def schedule_next_message(self):
        LOGGER.info('Scheduling next message for %0.1f seconds',
                    self.PUBLISH_INTERVAL)
        self._connection.ioloop.call_later(self.PUBLISH_INTERVAL,
                                           self.publish_message)

    def publish_message(self):
        if self._channel is None or not self._channel.is_open:
            return
        message = self.message_function()
        self._channel.basic_publish(exchange=self.exchange, routing_key=self.routing_key, properties=self.properties,
                                    body=json.dumps(message, ensure_ascii=False))
        if self.should_delivery_confirmation:
            self._message_number += 1
            self._deliveries[self._message_number] = True
        LOGGER.info('Published message # %s', str(message))
        self.schedule_next_message()

    def run(self, durable: bool):
        self.durable = durable
        while not self._stopping:
            self._connection = None
            self._deliveries = {}
            self._acked = 0
            self._nacked = 0
            self._message_number = 0

            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                if (self._connection is not None and
                        not self._connection.is_closed):
                    self._connection.ioloop.start()

        LOGGER.info('Stopped')

    def stop(self):
        LOGGER.info('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        if self._channel is not None:
            LOGGER.info('Closing the channel')
            self._channel.close()

    def close_connection(self):
        if self._connection is not None:
            LOGGER.info('Closing connection')
            self._connection.close()


class RabbitConsumer(RabbitReconnecting):

    def __init__(self, exchange: str, exchange_type: ExchangeTypeEnum, queue: str, routing_key: str,
                 on_message_function,
                 amqp_url: str = None, user_name: str = None, password: str = None, host: str = None,
                 port: int = None, key_values: list[list[str]] = [],
                 virtual_host: str = "%2F"):
        self.durable = False
        self.should_reconnect = False
        self.was_consuming = False
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._consuming = False
        self._prefetch_count = 1
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key = routing_key
        self.on_message_function = on_message_function
        if amqp_url is None:
            try:
                super().__init__(user_name, password, host, port, key_values, virtual_host)
            except TypeError as e:
                LOGGER.error(f"Must Define Url Or Other Connections Parameters")
                raise e

    def connect(self):
        LOGGER.info('Connecting to %s', self._url)
        return pika.SelectConnection(
            parameters=pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def close_connection(self):
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            LOGGER.info('Connection is closing or already closed')
        else:
            LOGGER.info('Closing connection')
            self._connection.close()

    def on_connection_open(self, _unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.warning('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reconnect necessary: %s', reason)
            self.reconnect()

    def reconnect(self):
        if self.RETRYING_ATTEMPTS <= self.RETRYING_MAX_ATTEMPTS:
            self.should_reconnect = True
        else:
            self.should_reconnect = False
        self.RETRYING_ATTEMPTS += 1
        self.stop()

    def open_channel(self):
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.exchange)

    def add_on_channel_close_callback(self):
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self.close_connection()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange: %s', exchange_name)
        cb = functools.partial(
            self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=self.exchange_type,
            callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info('exchange declared: %s', userdata)
        self.setup_queue(self.queue)

    def setup_queue(self, queue_name):
        LOGGER.info('Declaring queue %s, durable %s', queue_name, self.durable)
        cb = functools.partial(self.on_queue_declareok, userdata=queue_name)
        self._channel.queue_declare(queue=queue_name, callback=cb, durable=self.durable)

    def on_queue_declareok(self, _unused_frame, userdata):
        queue_name = userdata
        LOGGER.info('Binding %s to %s with %s', self.exchange, queue_name,
                    self.routing_key)
        cb = functools.partial(self.on_bindok, userdata=queue_name)
        self._channel.queue_bind(
            queue_name,
            self.exchange,
            routing_key=self.routing_key,
            callback=cb)

    def on_bindok(self, _unused_frame, userdata):
        LOGGER.info('Queue bound: %s', userdata)
        self.set_qos()

    def set_qos(self):
        self._channel.basic_qos(
            prefetch_count=self._prefetch_count, callback=self.on_basic_qos_ok)

    def on_basic_qos_ok(self, _unused_frame):
        LOGGER.info('QOS set to: %d', self._prefetch_count)
        self.start_consuming()

    def start_consuming(self):
        LOGGER.info('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self.queue, self.on_message)
        self.was_consuming = True
        self._consuming = True

    def add_on_cancel_callback(self):
        LOGGER.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        LOGGER.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        self.on_message_function(body, properties.content_type)
        self.acknowledge_message(basic_deliver.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            cb = functools.partial(
                self.on_cancelok, userdata=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)

    def on_cancelok(self, _unused_frame, userdata):
        self._consuming = False
        LOGGER.info(
            'RabbitMQ acknowledged the cancellation of the consumer: %s',
            userdata)
        self.close_channel()

    def close_channel(self):
        LOGGER.info('Closing the channel')
        self._channel.close()

    def run(self, durable: bool):
        self.durable = durable
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        if not self._closing:
            self._closing = True
            LOGGER.info('Stopping')
            if self._consuming:
                self.stop_consuming()
                self._connection.ioloop.start()
            else:
                self._connection.ioloop.stop()
            LOGGER.info('Stopped')
        else:
            self._connection.ioloop.stop()


class RabbitReconnectingConsumer(RabbitConsumer):
    def __init__(self, exchange: str, exchange_type: ExchangeTypeEnum, queue: str, routing_key: str,
                 amqp_url: str = None, user_name: str = None, password: str = None, host: str = None,
                 port: int = None, key_values: list[list[str]] = [],
                 virtual_host: str = "%2F",
                 reconnect_delay: int = 10):
        super().__init__(exchange, exchange_type, queue, routing_key, amqp_url, user_name, password, host, port,
                         key_values, virtual_host)
        self.SLEEP_BETWEEN_ATTEMPTS = reconnect_delay
        print(super().__dict__)

    def run(self, durable: bool):
        while True:
            try:
                super().run(durable)
            except KeyboardInterrupt:
                self.stop()
                break
            self._maybe_reconnect()

    def _maybe_reconnect(self):
        if self.should_reconnect:
            self.stop()
            LOGGER.info('Reconnecting after %d seconds', self.SLEEP_BETWEEN_ATTEMPTS)
            time.sleep(self.SLEEP_BETWEEN_ATTEMPTS)
        else:
            LOGGER.error(f"Can Not Connect To RabbitMQ with url: {self._url}")
            raise ConnectionError(f"Can Not Connect To RabbitMQ with url: {self._url}")
