import json
import amqp

from .. import logger


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

    def publish(self, body) -> None:
        body = json.dumps(body, ensure_ascii=False)
        msg = amqp.basic_message.Message(body=body)
        self.rabbit_channel.basic_publish(msg, exchange='', routing_key=self.rabbit_output_queue)
        logger.info(f'Publish msg to {self.rabbit_output_queue}')


def process_file(con, path, upload_id):
    logger.info(f"Sent processing {path} to RabbitMQ")
    with con as (connection, channel, input_queue, output_queue):
        pub = RabbitPublisher(
            channel,
            connection,
            output_queue
        )
        pub.publish({'path': path, 'upload_id': upload_id})