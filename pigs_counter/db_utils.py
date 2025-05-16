import psycopg2
from datetime import datetime
import json


from utils import print_log


# Параметры подключения
HOST = "172.26.0.4"              # Имя сервиса PostgreSQL
PORT = 5432                      # Порт PostgreSQL
DB_NAME = "postgres_db"           # Имя базы данных
DB_USER = "postgres_user"           # Пользователь PostgreSQL
DB_PASSWORD = "postgres_password"   # Пароль PostgreSQL


def insert_event_data(platenumber: str, place: str, start_time: str, pigs_quantity: int, pigs_defect: int):
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
            host=HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0
        query = f"""
            INSERT INTO events (platenumber, place, start_time, pigs_quantity, pigs_defect)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (platenumber, place, start_time,
                               pigs_quantity, pigs_defect))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        print(f"Данные события {event_id} успешно добавлены в таблицу events")

    except Exception as e:
        print(f"Ошибка подключения: {event_id}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()


def update_event_data(pigs_quantity: int, pigs_defect: int, start_time: str, end_time: str = 'NULL'):
    """
    Update event data

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
            host=HOST,
            port=PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0
        if end_time == 'NULL':
            query = """
                UPDATE events
                SET pigs_quantity = %s, pigs_defect = %s
                WHERE start_time = %s;
            """

            cursor.execute(
                query, (pigs_quantity, pigs_defect, start_time))
        else:
            query = """
                UPDATE events
                SET end_time = %s, pigs_quantity = %s, pigs_defect = %s
                WHERE start_time = %s;
            """

            cursor.execute(
                query, (end_time, pigs_quantity, pigs_defect, start_time))
            print(f"Данные события {event_id} успешно обновлены")
            with open('/pigs_counter/log.log', 'a+') as log:
                time_str = datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')
                log.write(
                    f'{time_str} - Данные события {event_id} успешно обновлены\n')

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения: {event_id}")

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
            host=HOST,
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
        print_log(f'Ошибка подключения \'{start_time}\'')

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
            host=HOST,
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
        print(f"Ошибка подключения")
        return '0'

    finally:
        if 'connection' in locals() and connection:
            connection.close()
        return '0'
