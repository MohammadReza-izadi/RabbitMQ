import logging

from rabbit import RabbitIntervalPublisher, ExchangeTypeEnum, ContentType, DeliveryMode

logging.basicConfig(level=logging.INFO)


def test():
    return {"hi": "bye"}


url = 'amqp://guest:guest@192.168.7.245:5672/%2F'
producer = RabbitIntervalPublisher(
    "routaa_exchange",
    ExchangeTypeEnum.DIRECT,
    "routaa_queue",
    "routaa_key",
    test,
    url
)
producer.set_message_content(ContentType.JSON)
producer.set_message_delivery_mode(DeliveryMode.PERSIST)
producer.run(True)
