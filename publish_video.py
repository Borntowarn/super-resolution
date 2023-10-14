from pathlib import Path

from services.rabbit import RabbitConnector
from services.rabbit import RabbitPublisher

import os
import argparse

parser = argparse.ArgumentParser(description='Videos to RabbitMQ')
parser.add_argument('input', default='videos', type=str, help='Input dir/file relative !!!Storage!!! folder')

if __name__ == '__main__':
    con = RabbitConnector(env_path='configs/rabbit.env')
    connection, channel, input_queue, output_queue = con.connect()
    
    pub = RabbitPublisher(channel, connection, input_queue)
    
    args = parser.parse_args()
    path = Path(args.input)
    if os.path.isdir(path):
        files = list(path.rglob('*.mp4'))
        for vid_path in files:
            pub.publish(Path(vid_path).as_posix(), -1)
    else:
        pub.publish(path.as_posix(), -1)