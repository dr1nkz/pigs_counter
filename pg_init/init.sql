-- Создаём базу данных (если необходимо)
-- CREATE DATABASE postgres_db;

-- Подключаемся к базе
\c postgres_db postgres_user;

-- Создаём таблицу events, если её нет
CREATE TABLE IF NOT EXISTS events (
    event_id SERIAL PRIMARY KEY,
    platenumber VARCHAR(20) NOT NULL,
    place VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    pigs_quantity INT NOT NULL,
    pigs_defect INT
);
