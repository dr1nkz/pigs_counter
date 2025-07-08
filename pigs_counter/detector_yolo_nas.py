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

    def __init__(self, checkpoint_path, conf_thres=0.7, iou_thres=0.5, device=None):
        self.conf_threshold = conf_thres
        self.iou_threshold = iou_thres
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu")
        self.model = models.get(Models.YOLO_NAS_M,
                                num_classes=1,
                                checkpoint_path=checkpoint_path).to(self.device)
        self.model.eval()

    def __call__(self, image):
        return self.detect_objects(image)

    def detect_objects(self, image):
        """
        Детекция объектов на изображении.
        :param image: np.array (BGR)
        :return: boxes, scores, class_ids
        """
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        predictions = self.model.predict(img_rgb, conf=self.conf_threshold)
        # type: super_gradients.training.models.detection_predictions.DetectionPrediction
        pred = predictions.prediction

        if pred.bboxes.shape[0] == 0:
            return [], [], []

        boxes = pred.bboxes.cpu().numpy()  # xyxy
        scores = pred.confidence.cpu().numpy()
        class_ids = pred.labels.cpu().numpy()

        # NMS уже встроен в predict, но ты можешь применить свою nms:
        keep = nms(boxes, scores, self.iou_threshold)
        return boxes[keep], scores[keep], class_ids[keep]

    def draw_detections(self, image):
        """
        Рисование прямоугольников на изображении.
        """
        classes = get_labelmap()
        class_names = list(classes.values())
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

    def set_results(self, boxes, scores, class_ids):
        self.boxes = boxes
        self.scores = scores
        self.class_ids = class_ids


pigs_detector = YOLONASDetector(
    checkpoint_path="checkpoints/test/average_model.pth",
    conf_thres=0.3,
    iou_thres=0.5
)
