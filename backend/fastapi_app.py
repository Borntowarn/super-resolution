import os.path
import tempfile
from threading import Lock

import requests
from fastapi import FastAPI, UploadFile
from fastapi.params import Body
from starlette.responses import HTMLResponse

from . import logger
from pathlib import Path
from .util import TempFolder
from .rabbit import process_file
from .rabbit import RabbitConnector
from .rabbit import VideoConsumerThread

tmp_folder = 'storage/tmp'

_temp_folder_obj = TempFolder(tmp_folder)
app = FastAPI(
    docs_url='/api/docs',
    on_startup=[_temp_folder_obj.delete_folder, _temp_folder_obj.make_folder],
    on_shutdown=[_temp_folder_obj.delete_folder],
)
callback_map = {}
check_lock = Lock()
con = RabbitConnector()

web_server_api_send_video_url = os.environ.get('WEBSITE_URL').rstrip('/')+'/loadVideo'


def send_processed_file(file, upload_id: int):
    with open(file, 'rb') as f:
        result = requests.post(
            web_server_api_send_video_url,
            files={'file': f},
            data={'upload_id': str(upload_id)},
            timeout=10
        )
        logger.info(f"Sent processed video to web server with {result.text}")


@app.post("/api/upload_file")
async def upload_file(
    file: UploadFile,
    upload_id: int = Body(embed=True),
    quality_upgrade: bool = Body(embed=True),
    generate_comments: bool = Body(embed=True)
):
    if file is None:
        return "Не выбран файл"
    if upload_id is None or upload_id < 0:
        return "Не указан или неверно введён upload_id"

    file_suffix = Path(file.filename).suffix
    tmp_filename = tempfile.mktemp(dir=tmp_folder, suffix=file_suffix)
    buffered_file = file.file
    with open(tmp_filename, 'wb') as f:
        f.write(buffered_file.read())
    try:
        with check_lock:
            callback_map[upload_id] = {
                'callback': lambda ready_file: send_processed_file(ready_file, upload_id),
                'path': tmp_filename
            }
        process_file(con, tmp_filename, upload_id)
    except Exception as e:
        print(f"Error: {e}")
    return "Hello " + file.filename + "!"


@app.get("/")
async def root():
    return HTMLResponse("<h1>Не расчитано для браузера!</h1>")


def main():
    video_processed_get_thread = VideoConsumerThread(con, check_lock, callback_map).start()

main()