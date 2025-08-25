import os
import json
import paho.mqtt.client as mqtt


BROKER_HOST = os.getenv('BROKER_HOST', 'nanomq')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_NOTIFICATIONS_TOPIC = os.getenv(
    'MQTT_NOTIFICATIONS_TOPIC', 'pigs_unloading')


def send_mqtt_message(pigs_quantity: int, start_time: str, end_time: str, platenumber: str = 'None', place: str = 'None', pigs_defect: int = 0):
    # Формируем payload для MQTT
    payload = {
        'title': 'Разгрузка',
        'start_time': start_time,
        'end_time': end_time,
        'pigs_quantity': pigs_quantity,
        'platenumber': platenumber,
        'pigs_defect': pigs_defect,
        'place': place,
    }

    # Отправляем в MQTT
    client = mqtt.Client(callback_api_version=5)
    client.connect(BROKER_HOST, MQTT_PORT, 60)
    try:
        client.publish(MQTT_NOTIFICATIONS_TOPIC, json.dumps(payload))
        print(payload)
        client.disconnect()
        print(f"Данные отправлены в MQTT топик {MQTT_NOTIFICATIONS_TOPIC}")
    except:
        print(
            f"Ошибка при отправке данных {payload} MQTT топик {MQTT_NOTIFICATIONS_TOPIC}")
