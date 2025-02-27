import psycopg2
import json


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

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        # print(f"Данные события {event_id} успешно обновлены")

    except Exception as e:
        print(f"Ошибка подключения: {event_id}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()
