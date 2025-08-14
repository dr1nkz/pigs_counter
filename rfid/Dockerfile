FROM python:3.10.12

WORKDIR /rfid

COPY ./requirements.txt /rfid

RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge