import psycopg2
from datetime import datetime
import json
import os
from dotenv import load_dotenv


from utils import print_log


# Параметры подключения
load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
# DB_HOST = '192.168.1.116'
PORT = 5432
DB_NAME = "postgres_db"
DB_USER = "postgres_user"
DB_PASSWORD = "postgres_password"


def insert_event_data(truck_id: str, place: str, start_time: str, pigs_quantity: int, pigs_defect: int):
    """
    Insert event data

    :event_id: str - id of event
    :place: str - place where pigs unloaded
    :start_time: float - start time of event
    :end_time: float - end time of event
    :pigs_quantity: int - quantity of pigs
    :pigs_defect: int - quantity of defect pigs
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0
        query = f"""
            INSERT INTO events (truck_id, place, start_time, pigs_quantity, pigs_defect)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (truck_id, place, start_time,
                               pigs_quantity, pigs_defect))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        print(f"Данные события {event_id} успешно добавлены в таблицу events")

    except Exception as e:
        print(f"Ошибка подключения: {e}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def update_event_data(pigs_quantity: int, pigs_defect: int, start_time: str,
                      end_time: str = 'NULL', truck_id: str = 'NULL', video_url: str = 'NULL'):
    """
    Update event data

    :event_id: str - id of event
    :place: str - place where pigs unloaded
    :start_time: float - start time of event
    :end_time: float - end time of event
    :pigs_quantity: int - quantity of pigs
    :pigs_defect: int - quantity of defect pigs
    :truck_id: str - truck_id
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0
        # Список полей и значений
        fields = []
        values = []

        # Обновляем pigs_quantity и pigs_defect всегда
        fields.append('pigs_quantity = %s')
        values.append(pigs_quantity)

        fields.append('pigs_defect = %s')
        values.append(pigs_defect)

        # Обновляем end_time только если оно есть
        if end_time != 'NULL' and end_time is not None:
            fields.append('end_time = %s')
            values.append(end_time)

        # Обновляем truck_id только если оно есть
        if truck_id != 'NULL' and truck_id is not None:
            fields.append('truck_id = %s')
            values.append(truck_id)

        # Обновляем video_url только если оно есть
        if video_url != 'NULL' and video_url is not None:
            fields.append('video_url = %s')
            values.append(video_url)

        # Подтягиваем truck_plate и trailer_plate с COALESCE
        fields.append(
            'truck_plate = COALESCE((SELECT t.truck_plate FROM trucks t WHERE t.truck_id = e.truck_id), e.truck_plate)')
        fields.append(
            'trailer_plate = COALESCE((SELECT t.trailer_plate FROM trucks t WHERE t.truck_id = e.truck_id), e.trailer_plate)')

        # Условие WHERE по start_time
        values.append(start_time)

        # Формируем SQL
        query = f"""
        UPDATE events e
        SET {', '.join(fields)}
        WHERE e.start_time = %s;
        """

        # Выполняем запрос
        cursor.execute(query, tuple(values))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения: {e}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def set_event_video_url(start_time: str, video_url: str):
    """
    Update event data

    :start_time: float - start time of event
    :video_url: str - video_url
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0

        # Формируем SQL
        query = f"""
        UPDATE events e
        SET video_url = %s
        WHERE e.start_time = %s;
        """

        # Выполняем запрос
        cursor.execute(query, (video_url, start_time))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения: {e}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def update_video_url_to_archive(date: str):
    """
    Update video url to archive

    :date: str - video_url
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        old_prefix = f"http://192.168.1.116/files/data/{date}/"
        new_prefix = f"http://192.168.1.116/files/archive/{date}/"

        # Формируем SQL
        query = f"""
            UPDATE events
            SET video_url = REPLACE(video_url, %s, %s)
            WHERE video_url LIKE %s;
        """

        # Выполняем запрос
        cursor.execute(query, (old_prefix, new_prefix, f"%{old_prefix}%"))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения: {e}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def delete_event_data(start_time: str):
    """
    Delete event data

    :start_time: float - start time of event
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Удаление данных
        query = """
            DELETE FROM events WHERE start_time = %s;
        """

        cursor.execute(query, (start_time,))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения")
        print_log(f'Ошибка подключения {e}')

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def get_event_id_by_start_time(start_time: str):
    """
    Update event data

    :start_time: float - start time of event
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Получение данных
        query = """
            SELECT event_id FROM events WHERE start_time = %s;
        """

        cursor.execute(
            query, (start_time,))

        # Сохранить изменения и закрыть соединение
        result = cursor.fetchone()
        connection.commit()
        cursor.close()

        if result:
            # предполагаем, что event_id — целое число
            event_id = str(result[0])
        else:
            event_id = '0'
        return event_id

    except Exception as e:
        print(f"Ошибка подключения {e}")
        return '0'

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def get_truck_id_by_start_time(start_time: str):
    """
    Get truck_id

    :start_time: float - start time of event
    """

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=DB_HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Получение данных
        query = """
            SELECT truck_id FROM events WHERE start_time = %s;
        """

        cursor.execute(
            query, (start_time,))

        # Сохранить изменения и закрыть соединение
        result = cursor.fetchone()
        connection.commit()
        cursor.close()

        if result:
            # предполагаем, что event_id — целое число
            truck_id = str(result[0])
        else:
            truck_id = None
        return truck_id

    except Exception as e:
        print(f"Ошибка подключения {e}")
        return None

    finally:
        if 'connection' in locals() and connection:
            connection.close()
