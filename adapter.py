import os
import shutil

from pathlib import Path
from src import logger
from src.video2x import Video2X
from src.rabbit.connector import Connector
from src.rabbit.consumer import RabbitConsumer

class Model:
    def __init__(self) -> None:
        self.video2x = Video2X()

    def _create_upscaled_path(self, video_path):
        logger.info(video_path)
        
        parts = Path(video_path).parts
        storage_folder = parts[-3]
        temp_folder = parts[-2]
        
        storage_path = Path(os.getcwd()) / storage_folder
        upscale_path = storage_path / 'upscaled'
        
        input_path = storage_path / temp_folder / Path(video_path).name
        upscaled_path = upscale_path / Path(video_path).name
        returned_path = Path(storage_folder) / 'upscaled' / Path(video_path).name
        
        if upscale_path.exists() is False:
            upscale_path.mkdir()
        
        logger.info([str(input_path), str(upscaled_path)])
        return str(input_path), str(upscaled_path), str(returned_path)
    
    def __call__(self, video_path):
        
        input_path, upscaled_path, returned_path = self._create_upscaled_path(video_path)
        model_name = 'model_tensorrt'
        shutil.copy(input_path, upscaled_path)
        
        # self.video2x.upscale(
        #     model_name,
        #     input_path,
        #     upscaled_path,
        #     856,
        #     480,
        #     3,
        #     2,
        #     0,
        #     ''
        # )
        return returned_path


if __name__ == '__main__':
    con = Connector()
    model = Model()

    connection, channel, input_queue, output_queue = con.connect()

    cons = RabbitConsumer( 
        rabbit_channel=channel,
        rabbit_connection=connection,
        rabbit_input_queue=input_queue,
        rabbit_output_queue=output_queue,
        pipeline=model
    )
    cons.listen()
