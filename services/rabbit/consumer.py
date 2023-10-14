import json
import time
import traceback
from typing import *

from loguru import logger

from .publisher import RabbitPublisher


class RabbitConsumer:

    def __init__(
        self,
        rabbit_channel,
        rabbit_connection,
        rabbit_input_queue: str,
        rabbit_output_queue: str,
        pipeline: Callable
    ):

        assert rabbit_channel.is_open, 'Failed connection to RabbitMQ'

        self.rabbit_connection = rabbit_connection
        self.rabbit_channel = rabbit_channel

        self.rabbit_input_queue = rabbit_input_queue
        self.publisher = RabbitPublisher(rabbit_channel, rabbit_connection, rabbit_output_queue)

        self.pipeline = pipeline

        logger.info(f'Consumer gets pipeline: {pipeline.__class__.__name__}')

    def _process_video(self, video_path: str) -> None:
        try:
            logger.info('Start processing a video')
            start_time = time.time()
            upscaled_path = self.pipeline(video_path)
            end_time = time.time() - start_time
            logger.info(f'Video has been processed in {end_time}s')
        except Exception as e:
            upscaled_path = None
            logger.error(e)
        return upscaled_path

    def _listen_video(self) -> None:
        while True:
            message = self.rabbit_channel.basic_get(queue=self.rabbit_input_queue)
            if message:
                self.rabbit_channel.basic_ack(delivery_tag=message.delivery_tag)
                payload = json.loads(message.body)
                
                video_id = int(payload['upload_id'])
                video_path = payload['path']
                
                processed_path = self._process_video(video_path)
                self.publisher.publish(processed_path, video_id)
            else:
                break

    def listen(self) -> None:
        self.rabbit_channel.basic_qos(prefetch_size=0, prefetch_count=1, a_global=False)
        logger.info(f'Start consuming on {self.rabbit_input_queue}')
        while True:
            try:
                self._listen_video()
            except:
                logger.error(f'{traceback.format_exc()}')
