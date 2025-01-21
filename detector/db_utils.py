import psycopg2
import json


def insert_event_data(platenumber: str, place: str, start_time: str, end_time: str, pigs_quantity: int, pigs_defect: int):
    """
    Insert_event_data

    :event_id: str - id of event
    :place: str - place where pigs unloaded
    :start_time: float - start time of event
    :end_time: float - end time of event
    :pigs_quantity: int - quantity of pigs
    :pigs_defect: int - quantity of defect pigs
    """

    # Параметры подключения
    host = "localhost"      # Имя контейнера PostgreSQL
    port = 5432                      # Порт PostgreSQL
    dbname = "postgres_db"           # Имя базы данных
    user = "postgres_user"           # Пользователь PostgreSQL
    password = "postgres_password"   # Пароль PostgreSQL

    try:
        # Установить соединение
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        cursor = connection.cursor()
        # Вставка данных
        event_id = 0
        query = f"""
            INSERT INTO events (platenumber, place, start_time, end_time, pigs_quantity, pigs_defect)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (platenumber, place, start_time,
                               end_time, pigs_quantity, pigs_defect))

        # Сохранить изменения и закрыть соединение
        connection.commit()
        cursor.close()
        print(f"Данные события {event_id} успешно добавлены в таблицу events")

    except Exception as e:
        print(f"Ошибка подключения: {event_id}")

    finally:
        if 'connection' in locals() and connection:
            connection.close()
