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
from utils import is_cross_of_line, print_log, count_states
from camera_thread import CameraThread


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
LINE_COORDINATES = (
    # ((1266, 0), (1162, 1080)),
    ((1472, 0), (1383, 1080)),
    # ((1682, 0), (1623, 1080))
)
# LINE_COORDINATES = (
#     ((666, 0), (562, 1080)),
#     ((872, 0), (783, 1080)),
#     ((1082, 0), (1023, 1080))
# )
# LINE_COORDINATES = (((888, 0), (750, 1440)), ((1163, 0),
#                     (1045, 1440)), ((1443, 0), (1364, 1440)))


def count_pigs(address):
    """
    Запуск модели
    """
    pigs_detector = YOLOv8(path=MODEL_PATH,
                           conf_thres=0.3,
                           iou_thres=0.5)
    ladder_detector = YOLOv8(path=LADDER_MODEL_PATH,
                             conf_thres=0.3,
                             iou_thres=0.5)

    while (True):
        # cap = cv2.VideoCapture(address, cv2.CAP_FFMPEG)
        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # fps = int(cap.get(cv2.CAP_PROP_FPS))
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # width1 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        # height1 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cam = CameraThread(address)
        cam.start()
        time.sleep(5)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps, width1, height1 = cam.get_properties()
        print(f'fps: {fps} width1: {width1} height1: {height1}')
        print_log(f'fps: {fps} width1: {width1} height1: {height1}')

        # cap_ladder = cv2.VideoCapture(LADDER_CAM_ADDRESS, cv2.CAP_FFMPEG)
        # cap_ladder.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # width2 = int(cap_ladder.get(cv2.CAP_PROP_FRAME_WIDTH))
        # height2 = int(cap_ladder.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cam_ladder = CameraThread(LADDER_CAM_ADDRESS)
        cam_ladder.start()
        time.sleep(5)
        fps2, width2, height2 = cam_ladder.get_properties()
        print(f'fps2: {fps2} width2: {width2} height2: {height2}')
        print_log(f'fps2: {fps2} width2: {width2} height2: {height2}')

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

        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_activation_threshold=0.25)
        coordinates = defaultdict(lambda: deque(maxlen=2))
        pigs_states = defaultdict(list)

        # Counter of all pigs crossed the line
        pigs_counter = 0

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
            # # Захват картинки
            # if not cap.isOpened():
            #     for i in range(1, 11):
            #         cap = None
            #         time.sleep(1)
            #         cap = cv2.VideoCapture(address, cv2.CAP_FFMPEG)
            #         cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            #         if cap.isOpened():
            #             print(
            #                 f'Connection estabilished {i} cap: {cap.isOpened()}')
            #             print_log(
            #                 f'Connection estabilished {i} cap: {cap.isOpened()}')
            #             break
            #         else:
            #             print(f'Try to open capture {i} cap: {cap.isOpened()}')
            #             print_log(
            #                 f'Try to open capture {i} cap: {cap.isOpened()}')

            # if not cap_ladder.isOpened():
            #     for i in range(1, 11):
            #         cap_ladder = None
            #         time.sleep(1)
            #         cap_ladder = cv2.VideoCapture(
            #             LADDER_CAM_ADDRESS, cv2.CAP_FFMPEG)
            #         cap_ladder.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            #         if cap_ladder.isOpened():
            #             print(
            #                 f'Connection estabilished {i} cap_ladder: {cap_ladder.isOpened()}')
            #             print_log(
            #                 f'Connection estabilished {i} cap_ladder: {cap_ladder.isOpened()}')
            #             break
            #         else:
            #             print(
            #                 f'Try to open capture {i} cap_ladder: {cap_ladder.isOpened()}')
            #             print_log(
            #                 f'Try to open capture {i} cap_ladder: {cap_ladder.isOpened()}')

            # if not cap.isOpened() or not cap_ladder.isOpened():
            #     break

            # # Кадр с камеры
            # cap.grab()
            # ret, frame = cap.read()
            # cap_ladder.grab()
            # ret_ladder, frame_ladder = cap_ladder.read()
            # if not ret or not ret_ladder:
            #     for i in range(1, 11):
            #         time.sleep(1)
            #         cap.grab()
            #         ret, frame = cap.read()
            #         cap_ladder.grab()
            #         ret_ladder, frame_ladder = cap_ladder.read()
            #         if ret and ret_ladder:
            #             print(
            #                 f'Frame returned {i} ret: {ret}   ret_ladder: {ret_ladder}')
            #             print_log(
            #                 f'Frame returned {i} ret: {ret}   ret_ladder: {ret_ladder}')
            #             break
            #         else:
            #             print(
            #                 f'Try to get frame {i} ret: {ret}   ret_ladder: {ret_ladder}')
            #             print_log(
            #                 f'Try to get frame {i} ret: {ret}   ret_ladder: {ret_ladder}')
            #             cap = None
            #             cap_ladder = None
            #             time.sleep(1)
            #             cap = cv2.VideoCapture(address, cv2.CAP_FFMPEG)
            #             cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            #             cap_ladder = cv2.VideoCapture(
            #                 LADDER_CAM_ADDRESS, cv2.CAP_FFMPEG)
            #             cap_ladder.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # if not ret or not ret_ladder:
            #     break

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
            bounding_boxes_ladder_pig_human, _, class_ids_ladder = ladder_detector(
                detected_img_ladder)
            detected_img_ladder = ladder_detector.draw_detections(
                detected_img_ladder)

            if len(bounding_boxes_ladder_pig_human) != 0 and ALLOWED_ZONE is not None:
                # Calculate the center points of the bounding boxes
                points = np.array([[(x_1 + x_2) / 2, (y_1 + y_2) / 2]
                                   for [x_1, y_1, x_2, y_2] in bounding_boxes_ladder_pig_human]).astype('int')

                # Initialize an array to store whether points are within allowed zones
                point_in_zone = np.zeros(len(points), dtype=bool)

                # Update the boolean mask for points within the current allowed zone
                point_in_zone = np.array(list(
                    map(lambda x: cv2.pointPolygonTest(ALLOWED_ZONE, x.tolist(), False) >= 0, points)))

                # Use this mask to filter or index your points or bounding boxes
                bounding_boxes_ladder_pig_human = np.array(
                    [box for index, box in enumerate(bounding_boxes_ladder_pig_human) if point_in_zone[index]])
                class_ids_ladder = np.array(
                    [class_id for index, class_id in enumerate(class_ids_ladder) if point_in_zone[index]])

            mask = np.isin(class_ids_ladder, [0])
            bounding_boxes_ladder = np.array(
                bounding_boxes_ladder_pig_human)[mask]
            mask = np.isin(class_ids_ladder, [1, 2])
            bounding_boxes_pig_human_from_ladder = np.array(
                bounding_boxes_ladder_pig_human)[mask]

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
                        if pigs_states.get(tracker_id) is None:
                            pigs_states[tracker_id] = [
                                None] * len(LINE_COORDINATES)
                        for id, line_coordinate in enumerate(LINE_COORDINATES):
                            previous_cross = is_cross_of_line(
                                coordinates[tracker_id][0], line_coordinate)
                            current_cross = is_cross_of_line(
                                coordinates[tracker_id][-1], line_coordinate)

                            if previous_cross and not current_cross:  # Слева направо
                                pigs_states[tracker_id][id] = 'undefined'
                            elif not previous_cross and current_cross:  # Справа налево
                                pigs_states[tracker_id][id] = 'undefined'
                            elif pigs_states.get(tracker_id)[id] == 'undefined':
                                if previous_cross and current_cross:
                                    pigs_states[tracker_id][id] = True
                                elif not previous_cross and not current_cross:
                                    pigs_states[tracker_id][id] = 'undefined'
                                    # pigs_states[tracker_id][id] = False

                count_true = count_states(pigs_states, True)
                count_false = count_states(pigs_states, False)
                pigs_counter = count_true - count_false
                pigs_counter = pigs_counter if pigs_counter >= 0 else 0
                update_event_data(pigs_counter, 0, start_time_str)

                # Visual
                line_color = (0, 0, 255)
                line_thickness = 5
                for line_coordinate in LINE_COORDINATES:
                    detected_img = cv2.line(detected_img, line_coordinate[0], line_coordinate[1],
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
                empty_rate_pig_human_from_ladder = after_event_delay_pig_human_from_ladder.count(
                    1) / len(after_event_delay_pig_human_from_ladder)
                after_event_delay_human_from_ladder_is_full = len(
                    after_event_delay_pig_human_from_ladder) == after_event_delay_pig_human_from_ladder.maxlen

            if (start_flag is True
                    # and empty_rate_pigs >= 0.9 and after_event_delay_pigs_is_full
                    and empty_rate_ladder >= 0.9 and after_event_delay_ladder_is_full
                    and empty_rate_pig_human_from_ladder >= 0.9 and after_event_delay_human_from_ladder_is_full):
                print(f'Общее количество поросят: {pigs_counter}')
                print_log(f'Общее количество поросят: {pigs_counter}')
                end_time = datetime.now()
                end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
                if pigs_counter == 0:
                    delete_event_data(start_time_str)
                else:
                    update_event_data(
                        pigs_counter, 0, start_time_str, end_time_str)
                # Release videowriter
                out.release()
                out = None
                end_time_hms = end_time.strftime(r'%H.%M.%S')
                filepath_end = (
                    f'{directory}/.{start_time_dmy} {start_time_hms}-{end_time_hms}.mp4')
                if os.path.isfile(filepath):
                    os.rename(filepath, filepath_end)
                # Reset variables
                pigs_counter = 0
                byte_track.reset()
                coordinates.clear()
                pigs_states.clear()
                after_event_delay_pigs.clear()
                after_event_delay_pigs.append(0)
                after_event_delay_ladder.clear()
                after_event_delay_ladder.append(0)
                after_event_delay_pig_human_from_ladder.clear()
                after_event_delay_pig_human_from_ladder.append(0)
                start_flag = False
            else:
                font = cv2.FONT_HERSHEY_SIMPLEX  # font
                fontScale = 1  # fontScale
                thickness = 2  # Line thickness of 2 px
                background_color = (254, 254, 254)

                # consecutive and counter on the frame
                cv2.rectangle(detected_img, (width1 - 270, 70), (width1 - 50, 170),
                              background_color, thickness=cv2.FILLED)
                # cv2.putText(detected_img, f'{(consecutive_end_pigs / fps):.1f}s', (width1 - 270, 150), font,
                #             fontScale*3, (0, 255, 0), thickness*3, cv2.LINE_AA)

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

        # cap.release()
        # cap_ladder.release()
        cam.stop()
        cam_ladder.stop()
        # ffmpeg_process.stdin.close()
        # ffmpeg_process.wait()


if __name__ == '__main__':
    count_pigs(CAM_ADDRESS)
