import cv2
import numpy as np
import onnxruntime

from utils import nms, get_labelmap, sigmoid, box_cxcywh_to_xyxy


class RFDETR:
    """
    Модель RFDETR, преобразованная в onnx формат
    """

    MEANS = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    STDS = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, path, conf_thres=0.5, iou_thres=0.5, max_boxes=300):
        self.conf_threshold = conf_thres
        self.iou_threshold = iou_thres
        self.max_boxes = max_boxes

        self.initialize_model(path)

    def __call__(self, image):
        return self.detect_objects(image)

    def initialize_model(self, path):
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

        self.session = onnxruntime.InferenceSession(
            path, providers=providers
        )

        self.get_input_details()
        self.get_output_details()

    def get_input_details(self):
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        _, _, self.input_height, self.input_width = inp.shape

    def get_output_details(self):
        self.output_names = [d.name for d in self.session.get_outputs()]

    def detect_objects(self, image):
        self.img_height, self.img_width = image.shape[:2]

        tensor = self.prepare_input(image)
        outputs = self.inference(tensor)

        self.boxes, self.scores, self.class_ids = self.process_output(outputs)

        return self.boxes, self.scores, self.class_ids

    def prepare_input(self, img_bgr):
        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.input_width, self.input_height))

        img = img.astype(np.float32) / 255.0
        img = (img - self.MEANS) / self.STDS

        img = img.transpose(2, 0, 1)
        img = img[np.newaxis, ...]
        return img.astype(np.float32)

    def inference(self, tensor):
        outputs = self.session.run(
            self.output_names, {self.input_name: tensor}
        )
        return outputs

    def process_output(self, outputs):
        """
        RFDETR выдаёт:
        outputs[0] = boxes [N, 4]
        outputs[1] = logits [N, num_classes]
        outputs[2] = masks (иногда) — игнорируем здесь
        """

        pred_boxes = outputs[0][0]          # (N,4)
        pred_logits = outputs[1][0]         # (N,C)

        # Активируем вероятности
        probs = sigmoid(pred_logits)

        # максимальная уверенность по классам
        scores = np.max(probs, axis=1)
        class_ids = np.argmax(probs, axis=1)

        # Сортировка — оставляем только top-K запросов
        idx = np.argsort(scores)[::-1][:self.max_boxes]
        scores = scores[idx]
        class_ids = class_ids[idx]
        pred_boxes = pred_boxes[idx]

        # Фильтрация по уверенности
        mask = scores > self.conf_threshold
        scores = scores[mask]
        class_ids = class_ids[mask]
        pred_boxes = pred_boxes[mask]

        if len(scores) == 0:
            return np.array([]), np.array([]), np.array([])

        # Конвертация cxcywh → xyxy
        boxes_xyxy = box_cxcywh_to_xyxy(pred_boxes)

        # масштабируем обратно в исходный размер изображения
        boxes_xyxy[:, [0, 2]] *= self.img_width
        boxes_xyxy[:, [1, 3]] *= self.img_height

        # NMS
        keep = nms(boxes_xyxy, scores, self.iou_threshold)

        return boxes_xyxy[keep], scores[keep], class_ids[keep]

    def draw_detections(self, image):
        classes = get_labelmap()
        class_names = list(classes.values())

        rng = np.random.default_rng(5)
        colors = rng.uniform(0, 255, size=(len(class_names), 3))

        for box, score, cls in zip(self.boxes, self.scores, self.class_ids):
            x1, y1, x2, y2 = box.astype(int)
            color = colors[cls]

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

            caption = f"{class_names[cls]} {int(score * 100)}%"

            cv2.putText(
                image,
                caption,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2,
                cv2.LINE_AA
            )

        return image

    def get_boxes(self):
        return self.boxes
