from collections import defaultdict, deque
from dotenv import load_dotenv
import os
from datetime import datetime
import subprocess
import time
import ast

import supervision as sv
import cv2
import numpy as np
import torch
import paho.mqtt.client as mqtt

from detector import YOLOv8, Detections
from db_utils import (
    insert_event_data,
    update_event_data,
    delete_event_data,
    get_event_id_by_start_time,
    get_truck_id_by_start_time
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
CAM_ADDRESS = os.getenv('CAM_ADDRESS')
PIGS_COUNTER_ADDRESS = os.getenv('PIGS_COUNTER_ADDRESS')
LADDER_CAM_ADDRESS = os.getenv('LADDER_CAM_ADDRESS')
LADDER_MODEL_PATH = os.getenv('LADDER_MODEL_PATH')
START_DELAY = int(os.getenv('START_DELAY'))
END_DELAY = int(os.getenv('END_DELAY'))
END_DELAY_LADDER = int(os.getenv('END_DELAY_LADDER'))
LINE_COORDINATES = ast.literal_eval(os.getenv('LINE_COORDINATES'))
ALLOWED_ZONE = np.array(ast.literal_eval(os.getenv('ALLOWED_ZONE')))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'python/mqtt')
BROKER_HOST = os.getenv('BROKER_HOST', 'nanomq')
RFID_STUB = 'Считывание...'
payload = None
rfid_received_message = False


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
        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_activation_threshold=0.25)
        coordinates = defaultdict(lambda: deque(maxlen=2))
        pigs_states = defaultdict(list)
        global rfid_received_message, payload

        # Counter of all pigs crossed the line
        pigs_counter = [0] * len(LINE_COORDINATES)
        result_counter = 0

        # Consecutive frames to start event
        consecutive_start_ladder = START_DELAY * fps
        consecutive_end_ladder = END_DELAY * fps
        consecutive_end_rfid = END_DELAY_LADDER * fps
        start_flag = False
        before_event_delay_ladder = 0
        after_event_delay_ladder = deque(maxlen=consecutive_end_ladder)
        after_event_delay_ladder.append(0)
        after_event_delay_rfid = deque(maxlen=consecutive_end_rfid)
        after_event_delay_rfid.append(0)

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
                        filepath, fourcc, fps2, (target_width, target_height))
                    insert_event_data(RFID_STUB, 'Пандус 1',
                                      start_time_str, result_counter, 0)

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
                                    # if count_states_single_state(pigs_states[tracker_id], True) == len(LINE_COORDINATES) - 1:
                                    pigs_counter[id] += 1
                                elif not previous_cross and not current_cross:
                                    pigs_states[tracker_id][id] = False
                                    # if count_states_single_state(pigs_states[tracker_id], False) == len(LINE_COORDINATES) - 1:
                                    pigs_counter[id] -= 1

                # count_true = count_states(pigs_states, True)
                # count_false = count_states(pigs_states, False)
                # pigs_counter = count_true - count_false
                # pigs_counter = pigs_counter if pigs_counter >= 0 else 0
                result_counter = int(np.average(pigs_counter))
                if result_counter % 10 == 0 and rfid_received_message:
                    update_event_data(result_counter, 0, start_time_str, truck_id=str(
                        payload, encoding='utf-8'))
                else:
                    update_event_data(result_counter, 0, start_time_str)
                # update_event_data(result_counter, 0, start_time_str)
                if rfid_received_message:
                    after_event_delay_rfid.append(0)
                else:
                    after_event_delay_rfid.append(1)
                rfid_received_message = False

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
                cv2.rectangle(detected_img, (50, 70), (560, 170),
                              background_color, thickness=cv2.FILLED)
                for id, pig_counter in enumerate(pigs_counter):
                    cv2.putText(detected_img, f'{pig_counter}', (50 + 170*id, 150), font,
                                fontScale*3, (0, 255, 0), thickness*3, cv2.LINE_AA)

                empty_rate_ladder = after_event_delay_ladder.count(
                    1) / len(after_event_delay_ladder)
                after_event_delay_ladder_is_full = len(
                    after_event_delay_ladder) == after_event_delay_ladder.maxlen
                rfid_is_scanned = get_truck_id_by_start_time(
                    start_time_str) and get_truck_id_by_start_time(start_time_str) != RFID_STUB
                empty_rate_rfid = after_event_delay_rfid.count(
                    1) / len(after_event_delay_rfid)
                after_event_delay_rfid_is_full = len(
                    after_event_delay_rfid) == after_event_delay_rfid.maxlen

            if (start_flag is True
                    and empty_rate_ladder >= 0.9 and after_event_delay_ladder_is_full):
                # and ((not rfid_is_scanned and empty_rate_ladder >= 0.9 and after_event_delay_ladder_is_full)  # по трапу если метка не считана
                #      or (rfid_is_scanned and empty_rate_rfid >= 0.9 and after_event_delay_rfid_is_full))):  # по мметке если метка считана
                print(f'Общее количество поросят: {result_counter}')
                print_log(f'Общее количество поросят: {result_counter}')
                end_time = datetime.now()
                end_time_str = end_time.strftime(r'%Y-%m-%d %H:%M:%S')
                if result_counter == 0:
                    delete_event_data(start_time_str)
                else:
                    # if rfid_received_message:
                    #     update_event_data(
                    #         result_counter, 0, start_time_str, end_time_str, str(payload, encoding='utf-8'))
                    # else:
                    update_event_data(
                        result_counter, 0, start_time_str, end_time_str)
                    send_mqtt_message(result_counter, start_time_str,
                                      end_time_str, truck_id=str(payload, encoding='utf-8'))
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
                byte_track.reset()
                coordinates.clear()
                pigs_states.clear()
                after_event_delay_ladder.clear()
                after_event_delay_ladder.append(0)
                after_event_delay_rfid.clear()
                after_event_delay_rfid.append(0)
                start_flag = False
                rfid_received_message = False
            else:
                font = cv2.FONT_HERSHEY_SIMPLEX  # font
                fontScale = 1  # fontScale
                thickness = 2  # Line thickness of 2 px
                background_color = (254, 254, 254)

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
            except:
                pass

        cam.stop()
        cam_ladder.stop()


def on_connect(client, userdata, flags, reason_code, properties):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect()
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """
    The callback for when a PUBLISH message is received from the server.
    """
    if (msg.topic == MQTT_TOPIC):
        print(msg.payload)
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
