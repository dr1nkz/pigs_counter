import cv2
import numpy as np
import torch
from super_gradients.training import models
from super_gradients.common.object_names import Models

from utils import nms, xywh2xyxy, get_labelmap


class YOLONASDetector:
    """
    Класс для работы с моделью YOLO-NAS (.pth) от SuperGradients
    """

    def __init__(self, path, conf_thres=0.7, iou_thres=0.5, device=None):
        self.conf_threshold = conf_thres
        self.iou_threshold = iou_thres
        self.path = path
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu")

        # Загружаем модель
        self.model = models.get(
            Models.YOLO_NAS_M,
            num_classes=self._get_num_classes_from_ckpt(),
            checkpoint_path=path
        ).to(self.device)
        self.model.eval()

        # Попробуем достать имена классов из checkpoint
        ckpt = torch.load(path, map_location='cpu')
        if "classes" in ckpt:
            # super_gradients обычно сохраняет dict {id: name}
            self.class_names = list(ckpt["classes"].values())
        else:
            # если нет - сделаем просто numbered labels
            num_classes = self._get_num_classes_from_ckpt()
            self.class_names = [f"class_{i}" for i in range(num_classes)]

        self.boxes, self.scores, self.class_ids = [], [], []

    def __call__(self, image):
        return self.detect_objects(image)

    def _get_num_classes_from_ckpt(self):
        ckpt = torch.load(self.path, map_location='cpu')

        if 'net' not in ckpt:
            raise ValueError("Чекпойнт не содержит ключа 'net'")

        state_dict = ckpt['net']  # теперь правильно

        for key, value in state_dict.items():
            if 'cls_pred.weight' in key:
                return value.shape[0]  # <- число классов

        raise ValueError("Не найден слой классификации в state_dict")

    def detect_objects(self, image):
        """
        Детекция объектов на изображении.
        :param image: np.array (BGR)
        :return: boxes, scores, class_ids
        """
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.model.predict(img_rgb, conf=self.conf_threshold)
        pred = results.prediction

        if pred.bboxes_xyxy.shape[0] == 0:
            self.boxes, self.scores, self.class_ids = [], [], []
            return [], [], []

        boxes = pred.bboxes_xyxy  # (N, 4), уже в формате XYXY
        scores = pred.confidence
        class_ids = pred.labels

        keep = nms(boxes, scores, self.iou_threshold)
        self.boxes = boxes[keep]
        self.scores = scores[keep]
        self.class_ids = class_ids[keep]

        return boxes, scores, class_ids

    def draw_detections(self, image):
        """
        Рисование прямоугольников на изображении.
        """
        if len(self.boxes) == 0:
            return image
        class_names = self.class_names
        rng = np.random.default_rng(3)
        colors = rng.uniform(0, 255, size=(len(class_names), 3))

        for box, score, class_id in zip(self.boxes, self.scores, self.class_ids):
            color = colors[class_id]
            x1, y1, x2, y2 = box.astype(int)

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            caption = f'{int(score * 100)}%'

            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            thickness = 2
            background_color = (254, 254, 254)
            (_, text_height), baseline = cv2.getTextSize(
                caption, font, fontScale, thickness)

            x, y = x1, y1 - 4 * thickness
            cv2.rectangle(image, (x, y - text_height), (x2, y + int(baseline/2)),
                          background_color, thickness=cv2.FILLED)
            cv2.putText(image, caption, (x1 + 140, y1 - 4 * thickness),
                        font, fontScale, color, thickness, cv2.LINE_AA)

        return image
