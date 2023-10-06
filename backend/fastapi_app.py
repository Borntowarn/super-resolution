import os.path
import pathlib
import tempfile
from threading import Event, Lock

import requests
from fastapi import FastAPI, UploadFile
from fastapi.params import Body
from starlette.responses import HTMLResponse

from .rabbit.connectorAMQP import Connector
from backend import logger
from backend.rabbit.processed_video_consumer import VideoConsumerThread
from backend.rabbit.publisher import process_file
from util.TempFolder import TempFolder

tmp_folder = 'storage/tmp'

_temp_folder_obj = TempFolder(tmp_folder)
app = FastAPI(docs_url='/api/docs',
              on_startup=[_temp_folder_obj.delete_folder, _temp_folder_obj.make_folder],
              on_shutdown=[_temp_folder_obj.delete_folder],
              )
callback_map = {}
check_lock = Lock()
new_item_event = Event()
con = Connector(
    env_path='configs/rabbit.env'
)

web_server_api_send_video_url = os.environ.get('WEBSITE_URL','http://u1988986.isp.regruhosting.ru').rstrip('/')+'/loadVideo'


def send_processed_file(file, upload_id: int):
    print(file)
    with open(file, 'rb') as f:
        result = requests.post(web_server_api_send_video_url, files={'file': f}, data={'upload_id': str(upload_id)}, timeout=10)
        print("Sending_video: ", result.text)


@app.post("/api/upload_file")
async def upload_file(file: UploadFile,
                      upload_id: int = Body(embed=True),
                      quality_upgrade: bool = Body(embed=True),
                      generate_comments: bool = Body(embed=True)):
    if file is None:
        return "Не выбран файл"
    if upload_id is None or upload_id < 0:
        return "Не указан или неверно введён upload_id"

    file_suffix = pathlib.Path(file.filename).suffix
    tmp_filename = tempfile.mktemp(dir=tmp_folder, suffix=file_suffix)
    buffered_file = file.file
    with open(tmp_filename, 'wb') as f:
        f.write(buffered_file.read())
    try:
        print(f"Sent processing {tmp_filename} to RabbitMQ")
        with check_lock:
            callback_map[upload_id] = {'callback': lambda ready_file: send_processed_file(ready_file, upload_id),
                                       'path': tmp_filename}
        new_item_event.set()
        logger.info("SET")
        logger.info(tmp_filename)
        process_file(con, tmp_filename, upload_id)
        print(f"Done")
        # await send_processed_file(tmp_filename, upload_id)
    except Exception as e:
        print(f"Ошибка обработки {e}")
    return "Hello " + file.filename + "!"


@app.get("/")
async def root():
    return HTMLResponse("<h1>Не расчитано для браузера!</h1>")


def main():
    video_processed_get_thread = VideoConsumerThread(con, check_lock, callback_map, new_item_event).start()


main()
