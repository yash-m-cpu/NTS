"""YOLO-based person detection engine using OpenCV DNN.

Loads pre-trained YOLOv4-tiny weights from the existing codebase,
filters strictly for human bodies (class 0: person), applies Non-Maximum
Suppression, and emits normalized BoundingBox and Detection entities.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.core.config import settings
from src.core.logging import logger
from src.core.schemas import BoundingBox, Detection


class YOLOPersonDetector:
    """Production person detector utilizing OpenCV DNN with YOLOv4-tiny."""

    def __init__(
        self,
        cfg_path: Optional[Path] = None,
        weights_path: Optional[Path] = None,
        conf_threshold: float = settings.CONFIDENCE_THRESHOLD,
        nms_threshold: float = settings.NMS_THRESHOLD,
        input_size: Tuple[int, int] = (settings.INPUT_WIDTH, settings.INPUT_HEIGHT)
    ):
        self.cfg_path = Path(cfg_path or settings.YOLO_CFG_PATH)
        self.weights_path = Path(weights_path or settings.YOLO_WEIGHTS_PATH)
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size

        self.net: Optional[cv2.dnn.Net] = None
        self.output_layers: List[str] = []
        self._is_initialized = False

        self._initialize_network()

    def _initialize_network(self) -> None:
        """Loads Darknet weights and config into OpenCV DNN."""
        if not self.cfg_path.exists() or not self.weights_path.exists():
            logger.warning(
                f"YOLO files not found at {self.cfg_path} or {self.weights_path}. "
                "Detector running in mock fallback mode."
            )
            return

        try:
            self.net = cv2.dnn.readNetFromDarknet(str(self.cfg_path), str(self.weights_path))
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            # Retrieve output layer names
            layer_names = self.net.getLayerNames()
            out_indices = self.net.getUnconnectedOutLayers()
            if len(out_indices.shape) == 1:
                self.output_layers = [layer_names[i - 1] for i in out_indices]
            else:
                self.output_layers = [layer_names[i[0] - 1] for i in out_indices]

            self._is_initialized = True
            logger.info("YOLOv4-tiny person detector initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self._is_initialized = False

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Executes forward pass on a BGR frame, returning confirmed person detections."""
        if not self._is_initialized or self.net is None:
            return []

        height, width = frame.shape[:2]
        if height == 0 or width == 0:
            return []

        # Construct blob (1/255 scale, RGB conversion, 416x416)
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0 / 255.0,
            size=self.input_size,
            mean=(0, 0, 0),
            swapRB=True,
            crop=False
        )

        self.net.setInput(blob)
        layer_outputs = self.net.forward(self.output_layers)

        boxes_px: List[List[int]] = []
        confidences: List[float] = []

        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                # Class 0 in COCO is 'person'
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])

                if class_id == 0 and confidence >= self.conf_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes_px.append([x, y, w, h])
                    confidences.append(confidence)

        if not boxes_px:
            return []

        # Apply Non-Maximum Suppression
        indices = cv2.dnn.NMSBoxes(
            boxes_px,
            confidences,
            self.conf_threshold,
            self.nms_threshold
        )

        detections: List[Detection] = []
        if len(indices) > 0:
            flat_indices = indices.flatten() if hasattr(indices, "flatten") else [i[0] for i in indices]
            for i in flat_indices:
                x, y, w, h = boxes_px[i]
                conf = confidences[i]

                # Convert to normalized [0.0, 1.0] coordinates with bounds clipping
                x1 = max(0.0, min(1.0, float(x) / width))
                y1 = max(0.0, min(1.0, float(y) / height))
                x2 = max(0.0, min(1.0, float(x + w) / width))
                y2 = max(0.0, min(1.0, float(y + h) / height))

                # Filter out degenerate zero-area boxes
                if x2 > x1 and y2 > y1:
                    detections.append(
                        Detection(
                            box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                            confidence=conf,
                            class_id=0,
                            class_name="person"
                        )
                    )

        return detections

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized
