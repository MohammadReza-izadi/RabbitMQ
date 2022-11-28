import logging

from rabbit import RabbitReconnectingConsumer, ExchangeTypeEnum
import time

logging.basicConfig(level=logging.INFO)

def test():
    time.sleep(10)

amqp_url = 'amqp://guest:guest@192.168.7.245:5672/%2F'
consumer = RabbitReconnectingConsumer("routaa_exchange", ExchangeTypeEnum.DIRECT, "routaa_queue",
                                      "routing_key",test, amqp_url, reconnect_delay=10)
consumer.run(True)
