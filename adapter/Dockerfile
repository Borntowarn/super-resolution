FROM python:3.10

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

COPY ./adapter/requirements.txt ./
RUN pip install -r requirements.txt

WORKDIR /app

COPY ./adapter adapter/
COPY ./rabbit rabbit/
COPY ./configs configs/

ENV LOGURU_COLORIZE "true"

CMD ["python", "-m", "adapter"]
