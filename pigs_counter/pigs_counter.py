from collections import defaultdict, deque
from dotenv import load_dotenv
import os
from datetime import datetime
import time
import ast

import cv2
import numpy as np
import paho.mqtt.client as mqtt

from ultralytics import solutions

from detector import YOLOv8, Detections
from db_utils import (
    insert_event_data,
    update_event_data,
    delete_event_data,
    get_event_id_by_start_time
)
from utils import (
    is_cross_of_line,
    print_log,
    count_states,
    count_states_single_state
)
from mqtt_notificator import send_mqtt_message
from camera_thread import CameraThread


load_dotenv()
MODEL_PATH = os.getenv('MODEL_PATH')
PT_MODEL_PATH = os.getenv('PT_MODEL_PATH')
CAM_ADDRESS = os.getenv('CAM_ADDRESS')
PIGS_COUNTER_ADDRESS = os.getenv('PIGS_COUNTER_ADDRESS')
LADDER_CAM_ADDRESS = os.getenv('LADDER_CAM_ADDRESS')
LADDER_MODEL_PATH = os.getenv('LADDER_MODEL_PATH')
START_DELAY = int(os.getenv('START_DELAY'))
END_DELAY = int(os.getenv('END_DELAY'))
LINE_COORDINATES = ast.literal_eval(os.getenv('LINE_COORDINATES'))
ALLOWED_ZONE = np.array(ast.literal_eval(os.getenv('ALLOWED_ZONE')))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'python/mqtt')
BROKER_HOST = os.getenv('BROKER_HOST', 'nanomq')


def count_pigs(address):
    """
    Запуск модели — теперь с использованием ultralytics.solutions.ObjectCounter
    Важное: логика с двумя камерами (cam и cam_ladder), запись видео в объединённом формате
    и старт/стоп события по детекции на трапе (ladder) сохранены без изменений.
    """

    pigs_detector = YOLOv8(path=MODEL_PATH,
                           conf_thres=0.3,
                           iou_thres=0.5)
    ladder_detector = YOLOv8(path=LADDER_MODEL_PATH,
                             conf_thres=0.3,
                             iou_thres=0.5)

    # Инициализация ObjectCounter — он заменяет ручную логику трекинга/подсчёта
    # NOTE: мы отключаем интерактивный показ (show_in/show_out = False) — у тебя нет cv2.imshow
    counter = solutions.ObjectCounter(
        region=LINE_COORDINATES,
        model=PT_MODEL_PATH,
        classes=[0],            # считаем класс 0 — как в оригинальном коде
        tracker="bytetrack.yaml",  # можно поменять при желании
        show_in=True,
        show_out=True,
    )

    while (True):
        cam = CameraThread(address)
        cam.start()
        time.sleep(5)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps, width1, height1 = cam.get_properties()
        print(f'fps: {fps} width1: {width1} height1: {height1}')
        print_log(f'fps: {fps} width1: {width1} height1: {height1}')

        cam_ladder = CameraThread(LADDER_CAM_ADDRESS)
        cam_ladder.start()
        time.sleep(5)
        fps2, width2, height2 = cam_ladder.get_properties()
        print(f'fps2: {fps2} width2: {width2} height2: {height2}')
        print_log(f'fps2: {fps2} width2: {width2} height2: {height2}')

        out = None
        rfid_received_message = False
        payload = None

        coordinates = defaultdict(lambda: deque(maxlen=2))

        # Counter of all pigs crossed the line (we'll keep the same variable but values come from ObjectCounter)
        pigs_counter = [0] * len(LINE_COORDINATES)
        result_counter = 0

        # Consecutive frames to start event
        consecutive_start_ladder = START_DELAY * fps
        consecutive_end_pigs = END_DELAY * fps
        consecutive_end_ladder = END_DELAY * fps
        consecutive_end_pig_human_from_ladder = 10 * fps
        start_flag = False
        before_event_delay_ladder = 0
        after_event_delay_pigs = deque(maxlen=consecutive_end_pigs)
        after_event_delay_pigs.append(0)
        after_event_delay_ladder = deque(maxlen=consecutive_end_ladder)
        after_event_delay_ladder.append(0)
        after_event_delay_pig_human_from_ladder = deque(
            maxlen=consecutive_end_pig_human_from_ladder)
        after_event_delay_pig_human_from_ladder.append(0)

        while True:
            frame = cam.get_frame()
            frame_ladder = cam_ladder.get_frame()
            if frame is None or frame_ladder is None:
                for i in range(1, 11):
                    time.sleep(1)
                    frame = cam.get_frame()
                    frame_ladder = cam_ladder.get_frame()
                    if frame is not None or frame_ladder is not None:
                        print(f'frame is ok  frame_ladder is ok')
                        print_log(f'frame is ok  frame_ladder is ok')
                        break
                    else:
                        print(
                            f'Try to get frame {i} frame is None: {frame is None}   frame_ladder is None: {frame_ladder is None}')
                        print_log(
                            f'Try to get frame {i} frame is None: {frame is None}   frame_ladder is None: {frame_ladder is None}')

            if frame is None or frame_ladder is None:
                break

            # Детектирование (лишь для дополнительной отрисовки — ObjectCounter сам делает детекцию внутри)
            detected_img = frame.copy()
            bounding_boxes_pigs, scores, class_ids = pigs_detector(
                detected_img)
            class_id_filter = 0
            bounding_boxes_pigs = np.array(bounding_boxes_pigs)[
                class_ids == class_id_filter] if len(bounding_boxes_pigs) > 0 else np.array([])
            scores = np.array(scores)[class_ids == class_id_filter] if len(
                scores) > 0 else np.array([])
            class_ids = np.array(class_ids)[class_ids == class_id_filter] if len(
                class_ids) > 0 else np.array([])

            # Get coords of detected ladders and check if it in area (логика без изменений)
            detected_img_ladder = frame_ladder.copy()
            bounding_boxes_ladder_pig_human, _, class_ids_ladder = ladder_detector(
                detected_img_ladder)
            detected_img_ladder = ladder_detector.draw_detections(
                detected_img_ladder)

            if len(bounding_boxes_ladder_pig_human) != 0 and ALLOWED_ZONE is not None:
                points = np.array([[(x_1 + x_2) / 2, (y_1 + y_2) / 2]
                                   for [x_1, y_1, x_2, y_2] in bounding_boxes_ladder_pig_human]).astype('int')

                point_in_zone = np.array(list(
                    map(lambda x: cv2.pointPolygonTest(ALLOWED_ZONE, x.tolist(), False) >= 0, points)))

                bounding_boxes_ladder_pig_human = np.array(
                    [box for index, box in enumerate(bounding_boxes_ladder_pig_human) if point_in_zone[index]])
                class_ids_ladder = np.array(
                    [class_id for index, class_id in enumerate(class_ids_ladder) if point_in_zone[index]])

            mask = np.isin(class_ids_ladder, [0])
            bounding_boxes_ladder = np.array(
                bounding_boxes_ladder_pig_human)[mask] if len(bounding_boxes_ladder_pig_human) > 0 else np.array([])
            mask = np.isin(class_ids_ladder, [1, 2])
            bounding_boxes_pig_human_from_ladder = np.array(
                bounding_boxes_ladder_pig_human)[mask] if len(bounding_boxes_ladder_pig_human) > 0 else np.array([])

            if len(bounding_boxes_pigs) != 0:  # objects detected
                after_event_delay_pigs.append(0)
            elif start_flag:
                after_event_delay_pigs.append(1)

            if len(bounding_boxes_pig_human_from_ladder) != 0:  # objects detected
                after_event_delay_pig_human_from_ladder.append(0)
            elif start_flag:
                after_event_delay_pig_human_from_ladder.append(1)

            if len(bounding_boxes_ladder) != 0:
                after_event_delay_ladder.append(0)
                if not start_flag:
                    before_event_delay_ladder += 1
                if before_event_delay_ladder == consecutive_start_ladder:
                    start_flag = True
                    before_event_delay_ladder = 0
                    try:
                        counter.reset()
                    except AttributeError:
                        # если reset нет в версии, пересоздаём объект
                        counter = solutions.ObjectCounter(
                            region=LINE_COORDINATES,
                            model=PT_MODEL_PATH,
                            classes=[0],
                            show_in=False,
                            show_out=False
                        )
            elif start_flag:
                after_event_delay_ladder.append(1)

            # Draw detections from the pigs_detector (kept for visual consistency)
            detected_img = pigs_detector.draw_detections(detected_img)

            # --- ЗАМЕНА: вместо ручного трекинга/подсчёта используем ObjectCounter ---
            # Обработка кадра ObjectCounter'ом (возвращает SolutionResults с plot_im, in_count, out_count и т.п.)
            try:
                results_counter = counter.process(detected_img)
            except Exception:
                # Если по каким-то причинам ObjectCounter упадёт, падаем обратно на "чистую" картинку
                results_counter = None

            if results_counter is not None:
                # annotated image from ObjectCounter
                detected_img = getattr(
                    results_counter, 'plot_im', detected_img)

                # ObjectCounter хранит кумулятивные счётчики in_count и out_count (см. docs)
                in_count = int(getattr(results_counter, 'in_count', 0))
                out_count = int(getattr(results_counter, 'out_count', 0))

                # итоговый счётчик - можно выбирать нужную метрику; здесь используем сумму in+out
                result_counter = out_count - in_count

                # Если нужно — можно получить classwise/region counts из results_counter (зависит от версии Ultralitycs)

                # Обновляем данные события в БД
                if start_flag:
                    try:
                        update_event_data(result_counter, 0, start_time_str)
                    except Exception:
                        # игнорируем ошибки БД здесь, чтобы не прерывать поток
                        pass

            # --- конец замены ---

            if start_flag:
                try:
                    out.isOpened()
                except:
                    start_time = datetime.now()
                    start_time_str = start_time.strftime(r'%Y-%m-%d %H:%M:%S')
                    start_time_dmy = start_time.strftime(r'%d.%m.%Y')
                    directory = f'../videos/{start_time_dmy}/'
                    if not os.path.isdir(directory):
                        os.mkdir(directory)

                    start_time_hms = start_time.strftime(r'%H.%M.%S')
                    filepath = (f'{directory}/.{start_time_hms}.mp4')
                    target_width = min(width1, width2)  # min width
                    target_height1 = int((height1 / width1) * target_width)
                    target_height2 = int((height2 / width2) * target_width)
                    target_height = target_height1 + target_height2
                    out = cv2.VideoWriter(
                        filepath, fourcc, fps, (target_width, target_height))
                    insert_event_data('A123BC13', 'Пандус 1',
                                      start_time_str, result_counter, 0)

            if (start_flag is True
                    and (after_event_delay_ladder.count(1) / len(after_event_delay_ladder)) >= 0.9
                    and len(after_event_delay_ladder) == after_event_delay_ladder.maxlen):
                print(f'Общее количество поросят: {result_counter}')
                print_log(f'Общее количество поросят: {result_counter}')
                end_time = datetime.now()
                end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
                if result_counter == 0:
                    delete_event_data(start_time_str)
                else:
                    if rfid_received_message:
                        update_event_data(
                            result_counter, 0, start_time_str, end_time_str, payload)
                    else:
                        update_event_data(
                            result_counter, 0, start_time_str, end_time_str)
                    send_mqtt_message(result_counter, start_time_str,
                                      end_time_str, platenumber=payload)
                # Release videowriter
                out.release()
                out = None
                end_time_hms = end_time.strftime(r'%H.%M.%S')
                event_id = get_event_id_by_start_time(start_time_str)
                filepath_end = (
                    f'{directory}/.{start_time_dmy} {start_time_hms}-{end_time_hms}.mp4')
                if os.path.isfile(filepath):
                    os.rename(filepath, filepath_end)
                # Reset variables
                pigs_counter = [0] * len(LINE_COORDINATES)
                coordinates.clear()
                after_event_delay_pigs.clear()
                after_event_delay_pigs.append(0)
                after_event_delay_ladder.clear()
                after_event_delay_ladder.append(0)
                after_event_delay_pig_human_from_ladder.clear()
                after_event_delay_pig_human_from_ladder.append(0)
                start_flag = False
                rfid_received_message = False

            else:
                # визуальная часть до старта — оставляем минимальную отрисовку
                font = cv2.FONT_HERSHEY_SIMPLEX
                fontScale = 1
                thickness = 2
                background_color = (254, 254, 254)

            if detected_img is None or detected_img_ladder is None:
                print(
                    f'detected_img: {detected_img is None}  detected_img_ladder: {detected_img_ladder is None}')
                print_log(
                    f'detected_img: {detected_img is None}  detected_img_ladder: {detected_img_ladder is None}')
                continue

            try:
                if out is not None and out.isOpened():
                    detected_img = cv2.resize(
                        detected_img, (target_width, target_height1))
                    detected_img_ladder = cv2.resize(
                        detected_img_ladder, (target_width, target_height2))
                    combined_frame = np.vstack(
                        (detected_img, detected_img_ladder))
                    out.write(combined_frame)
            except Exception:
                pass

        cam.stop()
        cam_ladder.stop()


def on_connect(client, userdata, flags, reason_code, properties):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    print(f"Connected with result code {reason_code}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """
    The callback for when a PUBLISH message is received from the server.
    """
    if (msg.topic == MQTT_TOPIC):
        print(msg.payload)
    # NOTE: MQTT handlers обновляют переменные-флаги в основной области видимости
    # чтобы это работало корректно при многопоточности/асинхронности, можно использовать очередь или
    # shared state; оставляем поведение как в оригинальном коде.
    global rfid_received_message, payload
    rfid_received_message = True
    payload = msg.payload


if __name__ == '__main__':
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(BROKER_HOST, 1883, 60)
    mqttc.loop_start()

    count_pigs(CAM_ADDRESS)
