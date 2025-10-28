-- Создаём базу данных (если необходимо)
-- CREATE DATABASE postgres_db;

-- Создаём таблицу trucks, если её нет
CREATE TABLE IF NOT EXISTS trucks (
    truck_id VARCHAR(20),
    truck_plate VARCHAR(20),
    trailer_plate VARCHAR(20)
);

-- Создаём таблицу events, если её нет
CREATE TABLE IF NOT EXISTS events (
    event_id SERIAL PRIMARY KEY,
    truck_id VARCHAR(20),
    place VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    pigs_quantity INT NOT NULL,
    pigs_defect INT,
    truck_plate VARCHAR(20),
    trailer_plate VARCHAR(20),
    video_url VARCHAR(255)
);
