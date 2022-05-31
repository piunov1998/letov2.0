FROM python:3.10.4-slim

WORKDIR /app

RUN apt update && apt install -y --no-install-recommends ffmpeg

COPY requirements.txt requirements.txt
RUN pip install pip --upgrade
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ./src ./src

WORKDIR src

CMD ["python3.10", "bot.py"]