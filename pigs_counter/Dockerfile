FROM python:3.10.12

WORKDIR /pigs_counter

COPY ./requirements.txt /app

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge