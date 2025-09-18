import os
import serial
import random
from paho.mqtt import client as mqtt_client
from dotenv import load_dotenv


load_dotenv()
BROKER_HOST = os.getenv('BROKER_HOST', 'nanomq')
BROKER_PORT = int(os.getenv('BROKER_PORT', '1883'))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'python/mqtt')
CLIENT_ID = os.getenv('CLIENT_ID', 'python-mqtt-0')
# username = 'emqx'
# password = 'public'


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


def connect_mqtt():
    # client = mqtt_client.Client(client_id)
    client = mqtt_client.Client(
        mqtt_client.CallbackAPIVersion.VERSION2, CLIENT_ID)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT)
    return client


def get_main_serial():
    return serial.Serial(port="/dev/ttyr00", baudrate=57600, parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)


def get_all():
    Rfid = None
    cur_serial = get_main_serial()
    while True:
        raw_data = cur_serial.read(10).hex()
        if raw_data:  # если что-то считали
            bytes_list = [raw_data[i:i+2] for i in range(0, len(raw_data), 2)]

            # Проверяем, что нужные байты есть
            if len(bytes_list) >= 8:
                hex_str = ''.join(bytes_list[5:8])
                try:
                    decimal_value = int(hex_str, 16)
                    Rfid = decimal_value
                    break
                except ValueError:
                    print(f"Некорректные данные: {hex_str}")
            else:
                print(f"Недостаточно данных: {bytes_list}")

    cur_serial.close()
    client.publish(MQTT_TOPIC, Rfid, 1)
    return [Rfid]


client = connect_mqtt()

while True:
    # get_all()
    print(get_all())
    # time.sleep(1)
