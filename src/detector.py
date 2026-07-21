import yaml
from pathlib import Path
from typing import List, Dict, Tuple
import cv2
import numpy as np

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

class PersonDetector:
    """
    Detector de personas altamente optimizado para CPU.
    """
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        model_name = self.config['model']['name']
        self.default_conf = self.config['model']['confidence_threshold']
        self.classes = self.config['model']['classes'] # [0]

        model_path = Path("models") / model_name
        self.onnx_path = model_path.with_suffix('.onnx')

        # Intentar cargar ONNX primero, si falla, PyTorch
        self.use_onnx = False
        if ONNX_AVAILABLE and self.onnx_path.exists():
            try:
                self._init_onnx()
            except Exception as e:
                print(f"[WARN] ONNX falló ({e}), usando PyTorch.")
                self._init_pytorch(model_path)
        elif ULTRALYTICS_AVAILABLE:
            self._init_pytorch(model_path)
        else:
            raise RuntimeError("No se encontró ONNX ni PyTorch. Instala: pip install ultralytics onnxruntime")

    def _init_onnx(self):
        providers = ['CPUExecutionProvider']
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(self.onnx_path), sess_options, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.use_onnx = True

    def _init_pytorch(self, model_path: Path):
        self.model = YOLO(str(model_path))
        self.model.to('cpu')
        self.use_onnx = False

    def detect(self, frame: np.ndarray, conf: float = None) -> List[Dict]:
        """
        Detecta personas en un frame.
        Devuelve una lista de detecciones con bounding boxes en coordenadas de 'frame'.
        """
        if conf is None:
            conf = self.default_conf

        if self.use_onnx:
            return self._detect_onnx(frame, conf)
        else:
            return self._detect_pytorch(frame, conf)

    def _detect_pytorch(self, frame, conf):
        results = self.model(frame, verbose=False, conf=conf, classes=self.classes)
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({'bbox': (x1, y1, x2, y2), 'confidence': float(box.conf[0])})
        return detections

    def _detect_onnx(self, frame: np.ndarray, conf: float) -> List[Dict]:
        h_orig, w_orig = frame.shape[:2]
        # Preprocesamiento básico (mejorado en la versión final)
        resized = cv2.resize(frame, (640, 640))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        input_tensor = rgb.astype(np.float32) / 255.0
        input_tensor = np.transpose(input_tensor, (2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)

        outputs = self.session.run(None, {self.input_name: input_tensor})

        predictions = np.squeeze(outputs[0]).T
        detections = []
        scale_x = w_orig / 640
        scale_y = h_orig / 640

        for pred in predictions:
            scores = pred[4:]
            class_id = np.argmax(scores)
            score = scores[class_id]
            if score < conf or class_id != 0:
                continue
            cx, cy, bw, bh = pred[:4]
            x1 = int((cx - bw/2) * scale_x)
            y1 = int((cy - bh/2) * scale_y)
            x2 = int((cx + bw/2) * scale_x)
            y2 = int((cy + bh/2) * scale_y)
            detections.append({'bbox': (max(0,x1), max(0,y1), min(w_orig,x2), min(h_orig,y2)), 'confidence': float(score)})

        return self._apply_nms(detections)

    @staticmethod
    def _apply_nms(detections: List[Dict], iou_thresh=0.5) -> List[Dict]:
        # Implementación simple de NMS (se puede mover a utils.py)
        if len(detections) <= 1:
            return detections
        boxes = np.array([d['bbox'] for d in detections])
        scores = np.array([d['confidence'] for d in detections])
        x1, y1 = boxes[:,0], boxes[:,1]
        x2, y2 = boxes[:,2], boxes[:,3]
        areas = (x2 - x1) * (y2 - y1)
        indices = np.argsort(scores)[::-1]
        keep = []
        while len(indices) > 0:
            i = indices[0]
            keep.append(i)
            if len(indices) == 1:
                break
            xx1 = np.maximum(x1[i], x1[indices[1:]])
            yy1 = np.maximum(y1[i], y1[indices[1:]])
            xx2 = np.minimum(x2[i], x2[indices[1:]])
            yy2 = np.minimum(y2[i], y2[indices[1:]])
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            overlap = (w * h) / (areas[i] + areas[indices[1:]] - (w * h))
            indices = indices[1:][overlap <= iou_thresh]
        return [detections[k] for k in keep]

# SINGLETON PARA REUTILIZAR EL MODELO ENTRE VIDEOS
_MODEL_INSTANCE = None
def get_detector(config_path: str = "config.yaml"):
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        _MODEL_INSTANCE = PersonDetector(config_path)
    return _MODEL_INSTANCE