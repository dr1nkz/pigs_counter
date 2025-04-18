import cv2
import threading
import time


from utils import print_log


class CameraThread(threading.Thread):
    def __init__(self, camera_address, reconnect_delay=2):
        super().__init__()
        self.camera_address = camera_address
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.lock = threading.Lock()
        self.frame = None
        self.running = True

        # Свойства камеры
        self.fps = None
        self.width = None
        self.height = None

    def open_camera(self):
        cap = cv2.VideoCapture(self.camera_address)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if cap.isOpened():
            # Сохраняем параметры камеры
            self.fps = int(cap.get(cv2.CAP_PROP_FPS))
            self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(f"[INFO] Камера {self.camera_address} успешно открыта")
            print_log(f"[INFO] Камера {self.camera_address} успешно открыта")
            return cap
        else:
            print(f"[WARN] Не удалось открыть камеру {self.camera_address}")
            print_log(
                f"[WARN] Не удалось открыть камеру {self.camera_address}")
            return None

    def run(self):
        self.cap = self.open_camera()
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                print(
                    f"[INFO] Повторное подключение камеры {self.camera_address}...")
                print_log(
                    f"[INFO] Повторное подключение камеры {self.camera_address}...")
                time.sleep(self.reconnect_delay)
                self.cap = self.open_camera()
                continue

            if self.cap.grab():
                ret, frame = self.cap.retrieve()
                if ret:
                    with self.lock:
                        self.frame = frame
                else:
                    print(
                        f"[WARN] Не удалось извлечь кадр с камеры {self.camera_address}")
                    print_log(
                        f"[WARN] Не удалось извлечь кадр с камеры {self.camera_address}")
                    self.cap.release()
                    self.cap = None
            else:
                print(
                    f"[WARN] Не удалось захватить кадр с камеры {self.camera_address}")
                print_log(
                    f"[WARN] Не удалось захватить кадр с камеры {self.camera_address}")
                self.cap.release()
                self.cap = None

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def get_properties(self):
        return (self.fps, self.width, self.height)

    def stop(self):
        self.running = False
        self.join()
        if self.cap:
            self.cap.release()
