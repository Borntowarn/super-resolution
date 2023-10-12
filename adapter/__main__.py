import os
import shutil

from loguru import logger
from pathlib import Path
from .video2x import Video2X
from rabbit import RabbitConnector
from rabbit import RabbitConsumer


class Model:
    def __init__(self) -> None:
        self.video2x = Video2X()

    def _create_pathes(self, video_path):
        logger.info(video_path)
        
        video_path = Path(video_path)
        root_path = os.getcwd()
        storage_folder_name = video_path.parts[0]
        upscaled_folder_name = 'upscaled'
        
        storage_folder = os.path.join(root_path, storage_folder_name)
        upscaled_folder = os.path.join(storage_folder, upscaled_folder_name)
        
        input_path = os.path.join(os.getcwd(), video_path)
        upscaled_path = os.path.join(upscaled_folder, video_path.name)
        returned_path = os.path.join(storage_folder_name, upscaled_folder_name, video_path.name)
        
        if os.path.exists(upscaled_folder) is False:
            os.mkdir(upscaled_folder)
        
        logger.info([input_path, upscaled_path, returned_path])
        return input_path, upscaled_path, returned_path
    
    def __call__(self, video_path):
        
        input_path, upscaled_path, returned_path = self._create_pathes(video_path)
        model_name = 'model_tensorrt'
        # shutil.copy(input_path, upscaled_path)
        
        self.video2x.upscale(
            model_name,
            input_path,
            upscaled_path,
            856,
            480,
            1,
            0,
        )
        return returned_path


if __name__ == '__main__':
    con = RabbitConnector()
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
