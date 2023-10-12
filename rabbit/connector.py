import os
import amqp
import time

from loguru import logger
from typing import *
from dotenv import dotenv_values

class RabbitConnector:
    def __init__(self, env_path=None) -> None:
        if env_path:
            self._load_env_from_file(env_path)
        self._load_env_from_os()

    
    def _load_env_from_file(self, env_path):
        d = dict(dotenv_values(env_path))
        os.environ['RABBIT_URL'] = d.get('RABBIT_URL')
        os.environ['INPUT_QUEUE'] = d.get('INPUT_QUEUE')
        os.environ['OUTPUT_QUEUE'] = d.get('OUTPUT_QUEUE')
    
    
    def _load_env_from_os(self):
        self.url = os.environ.get('RABBIT_URL')
        self.host, self.virtual_host = self.url.split('@')[1].split('/')
        _, self.username, self.password = self.url.split('@')[0].split(':')
        self.username = self.username.replace('//', '')
        
        self.input_queue = os.environ.get('INPUT_QUEUE') 
        self.output_queue = os.environ.get('OUTPUT_QUEUE')

        if len(self.virtual_host) == 0:
            self.virtual_host = '/'

        logger.info('Envs are loaded')
    
    
    def _create_queue(self, channel, queue_name):
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            exclusive=False,  # если очередь уже существует,
            auto_delete=False,
            arguments={'x-queue-type=classic': 'classic'}
        )
        logger.info(f'Queue {queue_name} has been added')
    
    
    def __del__(self):
        self.connection.close()
    
    
    def __enter__(self):
        return self.connect()

    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()
    
    
    def connect(self) -> Any:
        tries = 0
        while True:
            try:
                tries += 1
                logger.info(f'Trying to connect at {tries} time')
                self.connection = amqp.Connection(
                    host=self.host,
                    userid=self.username,
                    password=self.password,
                    virtual_host=self.virtual_host
                )

                self.connection.connect()
                channel = self.connection.channel()
                logger.info('Connection successful')

                self._create_queue(channel,self.input_queue)
                self._create_queue(channel,self.output_queue)
                
                return self.connection, channel, self.input_queue, self.output_queue
            except Exception as e:
                logger.info(f'Connection failed. Waiting for a 5 seconds...')
                time.sleep(5)
