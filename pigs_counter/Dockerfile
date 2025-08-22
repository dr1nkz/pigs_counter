FROM python:3.10.12

WORKDIR /pigs_counter

COPY ./requirements.txt /pigs_counter

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 

# Установка пакетов Python в правильном порядке
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge