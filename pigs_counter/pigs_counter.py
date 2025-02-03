from collections import defaultdict, deque
from dotenv import load_dotenv
import os
from datetime import datetime
import subprocess

import supervision as sv
import cv2
import numpy as np
import torch

from detector import YOLOv8, Detections
from db_utils import insert_event_data, update_event_data
from utils import is_cross_of_line


load_dotenv()
MODEL_PATH = os.getenv('MODEL_PATH')
CAM_ADDRESS = os.getenv('CAM_ADDRESS')
PIGS_COUNTER_ADDRESS = os.getenv('PIGS_COUNTER_ADDRESS')


def count_pigs(address):
    """
    Запуск модели
    """
    yolov8_detector = YOLOv8(path=MODEL_PATH,
                             conf_thres=0.3,
                             iou_thres=0.5)

    while (True):
        # cv2.namedWindow('stream', cv2.WINDOW_NORMAL) # %1%
        cap = cv2.VideoCapture(address)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = None

        # Команда FFmpeg для стриминга
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Перезаписывать выходные файлы
            "-f", "rawvideo",  # Формат входного видео
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",  # Формат пикселей
            "-s", f"{width}x{height}",  # Размер кадра
            "-r", str(fps),  # Частота кадров
            "-i", "-",  # Вход из stdin
            "-c:v", "libx264",  # Кодек для видео
            "-preset", "ultrafast",  # Предустановка для скорости кодирования
            "-pix_fmt", "yuv420p",  # Формат пикселей в выходном потоке
            "-f", "rtsp",  # Формат для RTSP
            PIGS_COUNTER_ADDRESS
        ]

        # Открытие FFmpeg процесса
        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
        line_coordinates = ((1443, 0), (1322, 1440))

        start_time_milliseconds = 0  # 10 секунд
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time_milliseconds)

        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_activation_threshold=0.25)
        coordinates = defaultdict(lambda: deque(maxlen=2))
        pigs_states = defaultdict()

        # Counter of all pigs crossed the line
        pigs_counter = 0

        # Consecutive frames to start event
        consecutive_start = 1 * fps
        consecutive_end = 20 * fps
        start_flag = False
        before_event_delay = 0
        after_event_delay = 0

        print(cap)
        print(cap.isOpened())
        while cap.isOpened():  # and end_time is None:
            # Кадр с камеры
            ret, frame = cap.read()
            if not ret:
                break

            # Детектирование
            detected_img = frame.copy()
            bounding_boxes, scores, class_ids = yolov8_detector(detected_img)

            class_id_filter = 0
            bounding_boxes = np.array(bounding_boxes)[
                class_ids == class_id_filter]
            scores = np.array(scores)[class_ids == class_id_filter]
            class_ids = np.array(class_ids)[class_ids == class_id_filter]

            if len(bounding_boxes) != 0:  # objects detected
                if not start_flag:
                    before_event_delay += 1
                if before_event_delay == consecutive_start:
                    start_flag = True
                    before_event_delay = 0
            elif start_flag:
                after_event_delay += 1

            detected_img = yolov8_detector.draw_detections(detected_img)

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
                    filepath = (f'{directory}/{start_time_hms}.mp4')
                    out = cv2.VideoWriter(
                        filepath, fourcc, fps, (width, height))
                    insert_event_data('A123BC13', 'Пандус 1',
                                      start_time_str, pigs_counter, 0)

                detections = Detections(xyxy=bounding_boxes, confidence=scores,
                                        class_id=class_ids, tracker_id=[None] * len(bounding_boxes))
                if len(detections.xyxy) != 0:
                    detections = byte_track.update_with_detections(
                        detections=detections)

                # Bottom center anchors to dictionary
                for tracker_id, xyxy in zip(detections.tracker_id, detections.xyxy):
                    if tracker_id != -1:
                        x_1 = xyxy[0]
                        y_1 = xyxy[1]
                        x_2 = xyxy[2]
                        y_2 = int(xyxy[3])
                        point = [int((x_1 + x_2) / 2), int((y_1 + y_2) / 2)]
                        coordinates[tracker_id].append(point)

                # Check if pig crossed the line left or right
                for tracker_id in coordinates.keys():
                    if len(coordinates[tracker_id]) == coordinates[tracker_id].maxlen:
                        # print(tracker_id)
                        # print(coordinates[tracker_id])
                        previous_cross = is_cross_of_line(
                            coordinates[tracker_id][0], line_coordinates)
                        current_cross = is_cross_of_line(
                            coordinates[tracker_id][-1], line_coordinates)
                        # print(f'current_cross {current_cross}  previous_cross {previous_cross}')

                        if previous_cross and not current_cross:  # Слева направо
                            pigs_states[tracker_id] = None
                        elif not previous_cross and current_cross:  # Справа налево
                            pigs_states[tracker_id] = None
                        elif pigs_states.get(tracker_id) is None:
                            if previous_cross and current_cross:
                                pigs_states[tracker_id] = True
                            elif not previous_cross and not current_cross:
                                pigs_states[tracker_id] = False

                count_true = sum(
                    value is True for value in pigs_states.values())  # Сумма True
                pigs_counter = count_true

                # Visual
                line_color = (0, 0, 255)
                line_thickness = 5
                detected_img = cv2.line(detected_img, line_coordinates[0], line_coordinates[1],
                                        line_color, line_thickness, lineType=0)  # Draw line

                for tracker_id, bounding_box in zip(detections.tracker_id, bounding_boxes):
                    caption = f'#{tracker_id}'  # caption
                    font = cv2.FONT_HERSHEY_SIMPLEX  # font
                    fontScale = 1  # fontScale
                    thickness = 2  # Line thickness of 2 px
                    x_1 = bounding_box[0]
                    y_1 = bounding_box[1]
                    x_2 = bounding_box[2]
                    y_2 = bounding_box[3]

                    x, y = int(x_1), int(y_1 - 4 * thickness)
                    (text_width, text_height), baseline = cv2.getTextSize(
                        caption, font, fontScale, thickness)
                    background_color = (254, 254, 254)

                    # tracker_id on the frame
                    # cv2.rectangle(detected_img, (x, y - text_height), (x + text_width, y + int(baseline/2)),
                    #                 background_color, thickness=cv2.FILLED)
                    cv2.putText(detected_img, caption, (x, y), font,
                                fontScale, (0, 0, 255), thickness, cv2.LINE_AA)
                    # cv2.putText(detected_img, f'{pigs_states.get(tracker_id)}', (x, y), font,
                    #             fontScale, (255, 0, 0), thickness, cv2.LINE_AA)

                    # counter on the frame
                    cv2.rectangle(detected_img, (50, 70), (220, 170),
                                  background_color, thickness=cv2.FILLED)
                    cv2.putText(detected_img, f'{pigs_counter}', (50, 150), font,
                                fontScale*3, (0, 255, 0), thickness*3, cv2.LINE_AA)

            if after_event_delay == consecutive_end:
                out.release()
                out = None
                print(f'Общее количество поросят: {pigs_counter}')
                end_time = datetime.now()
                end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
                update_event_data(
                    pigs_counter, 0, start_time_str, end_time_str)
            else:
                font = cv2.FONT_HERSHEY_SIMPLEX  # font
                fontScale = 1  # fontScale
                thickness = 2  # Line thickness of 2 px
                background_color = (254, 254, 254)

                # consecutive and counter on the frame
                cv2.rectangle(detected_img, (width - 270, 70), (width - 50, 170),
                              background_color, thickness=cv2.FILLED)
                cv2.putText(detected_img, f'{(consecutive_end / fps):.1f}s', (width - 270, 150), font,
                            fontScale*3, (0, 255, 0), thickness*3, cv2.LINE_AA)

            if detected_img is None:
                continue

            # cv2.imshow('stream', detected_img) # %1%
            try:
                if out.isOpened():
                    out.write(detected_img)
                    update_event_data(pigs_counter, 0, start_time_str)
            except:
                pass

            ffmpeg_process.stdin.write(detected_img.tobytes())
            # if cv2.waitKey(1) & 0xFF == ord('q'): # %1%
            #     out.release()
            #     out = None
            #     print(f'Общее количество поросят: {pigs_counter}')
            #     end_time = datetime.now()
            #     end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
            #     update_event_data(
            #         pigs_counter, 0, start_time_str, end_time_str)
            #     break

        cv2.destroyAllWindows()
        cap.release()
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()


if __name__ == '__main__':
    count_pigs(CAM_ADDRESS)
