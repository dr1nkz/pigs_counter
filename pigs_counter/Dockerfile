FROM python:3.10.12

WORKDIR /pigs_counter

COPY ./requirements.txt /pigs_counter

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка пакетов Python в правильном порядке
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.26 && \
    pip install --no-cache-dir cython>=3.0.0 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge