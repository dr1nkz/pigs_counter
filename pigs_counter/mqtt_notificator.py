import os
import json
import paho.mqtt.client as mqtt


MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'pigs_unloading')


def send_mqtt_message(platenumber: str, place: str, start_time: str,
                      end_time: str, pigs_quantity: int, pigs_defect: int):
    # Формируем payload для MQTT
    payload = {
        'title': 'Разгрузка',
        'start_time': start_time,
        'end_time': end_time,
        'pigs_quantity': pigs_quantity,
        'pigs_defect': pigs_defect,
        'platenumber': platenumber,
        'place': place,
    }

    # Отправляем в MQTT
    client = mqtt.Client(callback_api_version=5)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.publish(MQTT_TOPIC, json.dumps(payload))
    print(payload)
    client.disconnect()
    print(f"Данные отправлены в MQTT топик {MQTT_TOPIC}")
