import amqp

from typing import *
from loguru import logger
from .answer_template import RabbitAnswer

class RabbitPublisher:

    def __init__(
        self, 
        rabbit_channel,
        rabbit_connection,
        rabbit_output_queue: str
    ):

        assert rabbit_channel.is_open, 'Failed connection to RabbitMQ'

        self.rabbit_connection = rabbit_connection
        self.rabbit_channel = rabbit_channel
        self.rabbit_output_queue = rabbit_output_queue
    
    def _create_answer(self, path: str, video_id: int) -> None:
        return RabbitAnswer(path, video_id)
    
    def publish(self, path, video_id) -> None:
        answer = self._create_answer(path, video_id)
        msg = amqp.basic_message.Message(body=answer.json)
        self.rabbit_channel.basic_publish(msg, exchange='', routing_key=self.rabbit_output_queue)
        logger.info(f'Publish msg to {self.rabbit_output_queue}')