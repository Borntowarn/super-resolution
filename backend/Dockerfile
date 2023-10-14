FROM python:3.10

WORKDIR /app

COPY ./backend/requirements.txt  ./

RUN pip install -r requirements.txt

COPY ./backend ./backend
COPY ./rabbit ./rabbit
COPY ./configs ./configs

ENV LOGURU_COLORIZE "true"

CMD ["python", "-m", "backend"]