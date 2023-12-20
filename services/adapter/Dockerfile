FROM python:3.10

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

COPY ./services/adapter/requirements.txt ./
RUN pip3 install -r requirements.txt

WORKDIR /app

COPY ./services/adapter adapter/
COPY ./services/rabbit rabbit/
COPY ./configs configs/

ENV LOGURU_COLORIZE "true"

CMD ["python", "-m", "adapter"]
