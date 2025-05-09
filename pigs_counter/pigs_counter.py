from collections import defaultdict, deque
from dotenv import load_dotenv
import os
from datetime import datetime
import subprocess
import time

import supervision as sv
import cv2
import numpy as np
import torch

from detector import YOLOv8, Detections
from db_utils import insert_event_data, update_event_data, delete_event_data
from utils import is_cross_of_line


load_dotenv()
MODEL_PATH = os.getenv('MODEL_PATH')
CAM_ADDRESS = os.getenv('CAM_ADDRESS')
PIGS_COUNTER_ADDRESS = os.getenv('PIGS_COUNTER_ADDRESS')
LADDER_CAM_ADDRESS = os.getenv('LADDER_CAM_ADDRESS')
LADDER_MODEL_PATH = os.getenv('LADDER_MODEL_PATH')
START_DELAY = int(os.getenv('START_DELAY'))
END_DELAY = int(os.getenv('END_DELAY'))
ALLOWED_ZONE = np.array([[985, 500], [1378, 540], [1380, 842], [749, 783]])
# ALLOWED_ZONE = np.array([[1378, 704], [1931, 760], [1934, 1186], [1048, 1102]])
LINE_COORDINATES = ((1443, 0), (1322, 1440))


def print_log(log_string: str):
    with open('/pigs_counter/log.log', 'a+') as log:
        time_str = datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')
        log.write(f'{time_str} - {log_string}\n')


def count_pigs(address):
    """
    Запуск модели
    """
    pigs_detector = YOLOv8(path=MODEL_PATH,
                           conf_thres=0.3,
                           iou_thres=0.5)
    ladder_detector = YOLOv8(path=LADDER_MODEL_PATH,
                             conf_thres=0.7,
                             iou_thres=0.5)

    while (True):
        # cv2.namedWindow('stream', cv2.WINDOW_NORMAL) # %1%
        cap = cv2.VideoCapture(address)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        width1 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height1 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cap_ladder = cv2.VideoCapture(LADDER_CAM_ADDRESS)
        width2 = int(cap_ladder.get(cv2.CAP_PROP_FRAME_WIDTH))
        height2 = int(cap_ladder.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out = None

        # Команда FFmpeg для стриминга
        # ffmpeg_cmd = [
        #     "ffmpeg",
        #     "-y",  # Перезаписывать выходные файлы
        #     "-f", "rawvideo",  # Формат входного видео
        #     "-vcodec", "rawvideo",
        #     "-pix_fmt", "bgr24",  # Формат пикселей
        #     "-s", f"{width1}x{height1}",  # Размер кадра
        #     "-r", str(fps),  # Частота кадров
        #     "-i", "-",  # Вход из stdin
        #     "-c:v", "libx264",  # Кодек для видео
        #     "-preset", "ultrafast",  # Предустановка для скорости кодирования
        #     "-pix_fmt", "yuv420p",  # Формат пикселей в выходном потоке
        #     "-f", "rtsp",  # Формат для RTSP
        #     PIGS_COUNTER_ADDRESS
        # ]

        # Открытие FFmpeg процесса
        # ffmpeg_process = subprocess.Popen(
        #     ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        start_time_milliseconds = 0  # 10 секунд
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time_milliseconds)

        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_activation_threshold=0.25)
        coordinates = defaultdict(lambda: deque(maxlen=2))
        pigs_states = defaultdict()

        # Counter of all pigs crossed the line
        pigs_counter = 0

        # Consecutive frames to start event
        consecutive_start_ladder = START_DELAY * fps
        consecutive_end_pigs = END_DELAY * fps
        consecutive_end_ladder = END_DELAY * fps
        start_flag = False
        before_event_delay_ladder = 0
        after_event_delay_pigs = deque(maxlen=consecutive_end_pigs)
        after_event_delay_pigs.append(0)
        after_event_delay_ladder = deque(maxlen=consecutive_end_ladder)
        after_event_delay_ladder.append(0)

        while True:
            # Захват картинки
            if not cap.isOpened():
                for i in range(1, 11):
                    cap = None
                    time.sleep(1)
                    cap = cv2.VideoCapture(address)
                    if cap.isOpened():
                        print(
                            f'Connection estabilished {i} cap: {cap.isOpened()}')
                        print_log(
                            f'Connection estabilished {i} cap: {cap.isOpened()}')
                        break
                    else:
                        print(f'Try to open capture {i} cap: {cap.isOpened()}')
                        print_log(
                            f'Try to open capture {i} cap: {cap.isOpened()}')

            if not cap_ladder.isOpened():
                for i in range(1, 11):
                    cap_ladder = None
                    time.sleep(1)
                    cap_ladder = cv2.VideoCapture(LADDER_CAM_ADDRESS)
                    if cap_ladder.isOpened():
                        print(
                            f'Connection estabilished {i} cap_ladder: {cap_ladder.isOpened()}')
                        print_log(
                            f'Connection estabilished {i} cap_ladder: {cap_ladder.isOpened()}')
                        break
                    else:
                        print(
                            f'Try to open capture {i} cap_ladder: {cap_ladder.isOpened()}')
                        print_log(
                            f'Try to open capture {i} cap_ladder: {cap_ladder.isOpened()}')

            if not cap.isOpened() or not cap_ladder.isOpened():
                break

            # Кадр с камеры
            ret, frame = cap.read()
            ret_ladder, frame_ladder = cap_ladder.read()
            if not ret or not ret_ladder:
                for i in range(1, 11):
                    time.sleep(1)
                    ret, frame = cap.read()
                    ret_ladder, frame_ladder = cap_ladder.read()
                    if ret and ret_ladder:
                        print(
                            f'Frame returned {i} ret: {ret}   ret_ladder: {ret_ladder}')
                        print_log(
                            f'Frame returned {i} ret: {ret}   ret_ladder: {ret_ladder}')
                        break
                    else:
                        print(
                            f'Try to get frame {i} ret: {ret}   ret_ladder: {ret_ladder}')
                        print_log(
                            f'Try to get frame {i} ret: {ret}   ret_ladder: {ret_ladder}')
                        if not ret:
                            cap = None
                            time.sleep(1)
                            cap = cv2.VideoCapture(address)
                        if not ret_ladder:
                            cap_ladder = None
                            time.sleep(1)
                            cap_ladder = cv2.VideoCapture(LADDER_CAM_ADDRESS)

            if not ret or not ret_ladder:
                break

            # Детектирование
            detected_img = frame.copy()
            bounding_boxes_pigs, scores, class_ids = pigs_detector(
                detected_img)
            class_id_filter = 0
            bounding_boxes_pigs = np.array(bounding_boxes_pigs)[
                class_ids == class_id_filter]
            scores = np.array(scores)[class_ids == class_id_filter]
            class_ids = np.array(class_ids)[class_ids == class_id_filter]

            # Get coords od detected ladders and check if it in area
            detected_img_ladder = frame_ladder.copy()
            bounding_boxes_ladder, _, _ = ladder_detector(detected_img_ladder)
            detected_img_ladder = ladder_detector.draw_detections(
                detected_img_ladder)

            if len(bounding_boxes_ladder) != 0 and ALLOWED_ZONE is not None:
                # Calculate the center points of the bounding boxes
                points = np.array([[(x_1 + x_2) / 2, (y_1 + y_2) / 2]
                                   for [x_1, y_1, x_2, y_2] in bounding_boxes_ladder]).astype('int')

                # Initialize an array to store whether points are within allowed zones
                point_in_zone = np.zeros(len(points), dtype=bool)

                # Update the boolean mask for points within the current allowed zone
                point_in_zone = np.array(list(
                    map(lambda x: cv2.pointPolygonTest(ALLOWED_ZONE, x.tolist(), False) >= 0, points)))

                # Use this mask to filter or index your points or bounding boxes
                bounding_boxes_ladder = np.array(
                    [box for index, box in enumerate(bounding_boxes_ladder) if point_in_zone[index]])

            if len(bounding_boxes_pigs) != 0:  # objects detected
                after_event_delay_pigs.append(0)
            elif start_flag:
                after_event_delay_pigs.append(1)

            if len(bounding_boxes_ladder) != 0:
                after_event_delay_ladder.append(0)
                if not start_flag:
                    before_event_delay_ladder += 1
                if before_event_delay_ladder == consecutive_start_ladder:
                    start_flag = True
                    before_event_delay_ladder = 0
            elif start_flag:
                after_event_delay_ladder.append(1)

            detected_img = pigs_detector.draw_detections(detected_img)

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
                                      start_time_str, pigs_counter, 0)

                detections = Detections(xyxy=bounding_boxes_pigs, confidence=scores,
                                        class_id=class_ids, tracker_id=[None] * len(bounding_boxes_pigs))
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
                            coordinates[tracker_id][0], LINE_COORDINATES)
                        current_cross = is_cross_of_line(
                            coordinates[tracker_id][-1], LINE_COORDINATES)
                        # print(f'current_cross {current_cross}  previous_cross {previous_cross}')

                        if previous_cross and not current_cross:  # Слева направо
                            pigs_states[tracker_id] = 'undefined'
                        elif not previous_cross and current_cross:  # Справа налево
                            pigs_states[tracker_id] = 'undefined'
                        elif pigs_states.get(tracker_id) == 'undefined':
                            if previous_cross and current_cross:
                                pigs_states[tracker_id] = True
                            elif not previous_cross and not current_cross:
                                pigs_states[tracker_id] = False

                count_true = sum(
                    value is True for value in pigs_states.values())  # Сумма True
                count_false = sum(
                    value is False for value in pigs_states.values())  # Сумма False
                pigs_counter = count_true - count_false
                pigs_counter = pigs_counter if pigs_counter >= 0 else 0
                update_event_data(pigs_counter, 0, start_time_str)

                # Visual
                line_color = (0, 0, 255)
                line_thickness = 5
                detected_img = cv2.line(detected_img, LINE_COORDINATES[0], LINE_COORDINATES[1],
                                        line_color, line_thickness, lineType=0)  # Draw line

                for tracker_id, bounding_box in zip(detections.tracker_id, bounding_boxes_pigs):
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

                empty_rate_pigs = after_event_delay_pigs.count(
                    1) / len(after_event_delay_pigs)
                after_event_delay_pigs_is_full = len(
                    after_event_delay_pigs) == after_event_delay_pigs.maxlen
                empty_rate_ladder = after_event_delay_ladder.count(
                    1) / len(after_event_delay_ladder)
                after_event_delay_ladder_is_full = len(
                    after_event_delay_ladder) == after_event_delay_ladder.maxlen

            if start_flag is True and empty_rate_pigs >= 0.9 and after_event_delay_pigs_is_full and empty_rate_ladder >= 0.9 and after_event_delay_ladder_is_full:
                print(f'Общее количество поросят: {pigs_counter}')
                print_log(f'Общее количество поросят: {pigs_counter}')
                end_time = datetime.now()
                end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
                if pigs_counter == 0:
                    delete_event_data(start_time)
                else:
                    update_event_data(
                        pigs_counter, 0, start_time_str, end_time_str)
                # Release videowriter
                out.release()
                out = None
                # Reset variables
                pigs_counter = 0
                byte_track.reset()
                coordinates.clear()
                pigs_states.clear()
                after_event_delay_pigs.clear()
                after_event_delay_pigs.append(0)
                after_event_delay_ladder.clear()
                after_event_delay_ladder.append(0)
                start_flag = False
            else:
                font = cv2.FONT_HERSHEY_SIMPLEX  # font
                fontScale = 1  # fontScale
                thickness = 2  # Line thickness of 2 px
                background_color = (254, 254, 254)

                # consecutive and counter on the frame
                cv2.rectangle(detected_img, (width1 - 270, 70), (width1 - 50, 170),
                              background_color, thickness=cv2.FILLED)
                cv2.putText(detected_img, f'{(consecutive_end_pigs / fps):.1f}s', (width1 - 270, 150), font,
                            fontScale*3, (0, 255, 0), thickness*3, cv2.LINE_AA)

            if detected_img is None or detected_img_ladder is None:
                print(
                    f'detected_img: {detected_img is None}  detected_img_ladder: {detected_img_ladder is None}')
                print_log(
                    f'detected_img: {detected_img is None}  detected_img_ladder: {detected_img_ladder is None}')
                continue

            try:
                if out.isOpened():
                    detected_img = cv2.resize(
                        detected_img, (target_width, target_height1))
                    detected_img_ladder = cv2.resize(
                        detected_img_ladder, (target_width, target_height2))
                    combined_frame = np.vstack(
                        (detected_img, detected_img_ladder))
                    out.write(combined_frame)
                    # update_event_data(pigs_counter, 0, start_time_str)
            except:
                pass

            # ffmpeg_process.stdin.write(detected_img.tobytes())

        print(f'cap: {cap.isOpened()}   cap_ladder: {cap_ladder.isOpened()}')
        print_log(
            f'cap: {cap.isOpened()}   cap_ladder: {cap_ladder.isOpened()}')
        cv2.destroyAllWindows()
        cap.release()
        cap_ladder.release()
        # ffmpeg_process.stdin.close()
        # ffmpeg_process.wait()


if __name__ == '__main__':
    count_pigs(CAM_ADDRESS)
