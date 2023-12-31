import os
from pathlib import Path

from dotenv import dotenv_values
from loguru import logger

from rabbit import RabbitConnector, RabbitConsumer

from .video2x import Video2X


class Model:
    def __init__(self, folder_envs) -> None:
        self.video2x = Video2X()
        self._load_folder_envs(folder_envs)
    
    
    def _load_folder_envs(self, env_path):
        d = dict(dotenv_values(env_path))
        logger.info(d)
        self.upscaled_folder_name = d['UPSCALED_FOLDER']

    def _create_pathes(self, video_path):
        logger.info(video_path)
        
        video_path = Path(video_path) # relative video path
        root_path = os.getcwd()
        storage_folder_name = video_path.parts[0] 
        
        storage_folder = os.path.join(root_path, storage_folder_name) # storage dir
        upscaled_folder = os.path.join(storage_folder, self.upscaled_folder_name) # storage upscaled dir
        
        input_path = os.path.join(os.getcwd(), video_path) # video abspath
        upscaled_path = os.path.join(upscaled_folder, video_path.name) # relative by storage folder upscaled path
        returned_path = os.path.join(storage_folder_name, self.upscaled_folder_name, video_path.name)
        
        if os.path.exists(upscaled_folder) is False:
            os.mkdir(upscaled_folder)
        
        logger.info([input_path, upscaled_path, returned_path])
        return input_path, upscaled_path, returned_path
    
    def __call__(self, video_path):
        
        input_path, upscaled_path, returned_path = self._create_pathes(video_path)
        model_name = 'model_tensorrt'
        # shutil.copy(input_path, upscaled_path)
        
        self.video2x.upscale(
            model_name, # model name in triton
            input_path, # video path
            upscaled_path, # upscaled path
            856, # target width
            480, # target height
            1, # process number
            0, # frame threshold
        )
        return returned_path


if __name__ == '__main__':
    model = Model('configs/folder.env')
    
    con = RabbitConnector()

    connection, channel, input_queue, output_queue = con.connect()

    cons = RabbitConsumer( 
        rabbit_channel=channel,
        rabbit_connection=connection,
        rabbit_input_queue=input_queue,
        rabbit_output_queue=output_queue,
        pipeline=model
    )
    cons.listen()
