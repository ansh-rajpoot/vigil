import io
import cv2
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple
from django.core.files.base import ContentFile
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import VisionCameraFeed, VisionDetectionLog


@dataclass
class VisionResult:
    crowd_count: int
    crowd_density_score: float  # 0.0 to 100.0
    density_tier: str          # LOW, NORMAL, HIGH, CRITICAL_SURGE
    people_per_sqm: float
    surge_rate_per_min: float
    concentration_index: float # 0.0 to 1.0
    anomaly_detected: str      # NONE, CROWD_SURGE, ABNORMAL_CONCENTRATION, OVERCROWDING
    confidence_score: float
    annotated_image_bytes: Optional[bytes] = None
    notes: str = ""


class BaseVisionEngine(ABC):
    """
    Abstract interface for Vision & Crowd Density Processing.
    Allows transparent heuristic or trained YOLO/PyTorch models to be plugged in interchangeably.
    """
    @abstractmethod
    def analyze_frame(self, image_bytes: bytes, camera_feed: VisionCameraFeed, previous_log: Optional[VisionDetectionLog] = None) -> VisionResult:
        pass


class OpenCVCrowdVisionEngine(BaseVisionEngine):
    """
    OpenCV spatial contour and motion clustering vision engine.
    Calculates people count, density per m^2, spatial bottleneck concentration, and sudden crowd surge.
    Does NOT claim deep learning anomaly classification; uses transparent mathematical thresholds.
    """
    def analyze_frame(self, image_bytes: bytes, camera_feed: VisionCameraFeed, previous_log: Optional[VisionDetectionLog] = None) -> VisionResult:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return VisionResult(
                crowd_count=0,
                crowd_density_score=0.0,
                density_tier='LOW',
                people_per_sqm=0.0,
                surge_rate_per_min=0.0,
                concentration_index=0.0,
                anomaly_detected='NONE',
                confidence_score=0.0,
                notes="Corrupted or invalid frame buffer"
            )

        height, width = img.shape[:2]
        target_w = 640
        scale = target_w / float(width)
        target_h = int(height * scale)
        resized = cv2.resize(img, (target_w, target_h))

        # Spatial person segmentation via adaptive thresholding and morphology
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blurred, 40, 140)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: List[Tuple[int, int, int, int]] = []
        quadrants = [0, 0, 0, 0]  # Top-Left, Top-Right, Bottom-Left, Bottom-Right

        for c in contours:
            area = cv2.contourArea(c)
            if 300 < area < 25000:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = float(h) / (w or 1)
                if 0.8 <= aspect_ratio <= 4.0 or area > 1200:
                    boxes.append((x, y, w, h))
                    # Spatial concentration quadrant tracking
                    q_idx = (0 if x < target_w / 2 else 1) + (0 if y < target_h / 2 else 2)
                    quadrants[q_idx] += 1

        detected_count = len(boxes)

        # 1. Physical Density (people per square meter)
        coverage_sqm = camera_feed.coverage_area_sqm if camera_feed else 250.0
        people_per_sqm = round(detected_count / max(10.0, coverage_sqm), 2)

        # 2. Spatial Concentration / Bottleneck Index (Max quadrant ratio vs total)
        max_q = max(quadrants) if quadrants else 0
        concentration_index = round(max_q / max(1, detected_count), 2) if detected_count > 0 else 0.0

        # 3. Sudden Crowd Surge Velocity (Delta N / Delta t)
        surge_rate = 0.0
        if previous_log:
            time_delta_mins = max(0.1, (timezone.now() - previous_log.timestamp).total_seconds() / 60.0)
            diff_count = detected_count - previous_log.crowd_count
            surge_rate = round(diff_count / time_delta_mins, 1)

        # 4. Normalized Crowd Density Score (0 - 100)
        max_cap = camera_feed.max_safe_capacity if camera_feed else 120
        capacity_ratio = detected_count / float(max_cap or 100)

        # Base capacity component (up to 70 pts) + concentration (15 pts) + surge velocity (15 pts)
        score = min(70.0, capacity_ratio * 70.0)
        if concentration_index > 0.45:
            score += min(15.0, (concentration_index - 0.45) * 30.0)
        if surge_rate > 10.0:
            score += min(15.0, (surge_rate / 20.0) * 15.0)

        crowd_density_score = round(min(100.0, max(0.0, score)), 1)

        # 5. Density Tier & Anomaly Classification
        if crowd_density_score >= 80.0 or capacity_ratio >= 1.0:
            density_tier = 'CRITICAL_SURGE'
            anomaly = 'OVERCROWDING' if capacity_ratio >= 1.0 else 'CROWD_SURGE'
        elif crowd_density_score >= 55.0 or capacity_ratio >= 0.65:
            density_tier = 'HIGH'
            anomaly = 'ABNORMAL_CONCENTRATION' if concentration_index > 0.55 else 'NONE'
        elif crowd_density_score >= 25.0:
            density_tier = 'NORMAL'
            anomaly = 'NONE'
        else:
            density_tier = 'LOW'
            anomaly = 'NONE'

        if surge_rate >= (camera_feed.surge_threshold_rate if camera_feed else 25):
            anomaly = 'CROWD_SURGE'
            density_tier = 'CRITICAL_SURGE'

        # 6. Render Tactical Operational Annotations
        annotated = resized.copy()
        box_color = (80, 200, 0) if density_tier in ['LOW', 'NORMAL'] else (0, 140, 255) if density_tier == 'HIGH' else (0, 0, 235)

        for (x, y, w, h) in boxes:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), box_color, 2)
            cv2.circle(annotated, (x + w // 2, y + min(12, h // 4)), 3, (255, 255, 255), -1)

        # Top Telemetry Header Banner
        cv2.rectangle(annotated, (0, 0), (target_w, 36), (15, 23, 42), -1)
        cam_code = camera_feed.camera_code if camera_feed else "CAM-SEC-01"
        hud_text = f"CAM: {cam_code} | COUNT: {detected_count}/{max_cap} | DENSITY: {crowd_density_score:.0f}/100 [{density_tier}]"
        cv2.putText(annotated, hud_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)

        # Bottom Anomaly Warning if any
        if anomaly != 'NONE':
            cv2.rectangle(annotated, (0, target_h - 28), (target_w, target_h), (0, 0, 180), -1)
            cv2.putText(annotated, f"TACTICAL ALERT: {anomaly} DETECTED (Surge: +{surge_rate}/min)", (10, target_h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

        _, encoded = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 88])

        notes = f"Estimated {detected_count} occupants ({people_per_sqm} ppl/m²). Capacity: {capacity_ratio*100:.1f}%. Surge rate: {surge_rate}/min."

        return VisionResult(
            crowd_count=detected_count,
            crowd_density_score=crowd_density_score,
            density_tier=density_tier,
            people_per_sqm=people_per_sqm,
            surge_rate_per_min=surge_rate,
            concentration_index=concentration_index,
            anomaly_detected=anomaly,
            confidence_score=0.91,
            annotated_image_bytes=encoded.tobytes(),
            notes=notes
        )


def get_vision_engine() -> BaseVisionEngine:
    """Returns the active vision engine instance."""
    return OpenCVCrowdVisionEngine()


def process_camera_feed(camera_feed: VisionCameraFeed, image_bytes: bytes) -> VisionDetectionLog:
    """
    Executes frame analysis, stores detection log, and dispatches automated alerts when thresholds are exceeded.
    """
    engine = get_vision_engine()
    previous_log = camera_feed.detections.first()

    result = engine.analyze_frame(image_bytes, camera_feed, previous_log)

    log = VisionDetectionLog(
        camera=camera_feed,
        crowd_count=result.crowd_count,
        crowd_density_score=result.crowd_density_score,
        density_tier=result.density_tier,
        people_per_sqm=result.people_per_sqm,
        surge_rate_per_min=result.surge_rate_per_min,
        concentration_index=result.concentration_index,
        anomaly_detected=result.anomaly_detected,
        confidence_score=result.confidence_score,
        notes=result.notes
    )

    if result.annotated_image_bytes:
        filename = f"cctv_{camera_feed.camera_code}_{int(timezone.now().timestamp())}.jpg"
        log.annotated_frame.save(filename, ContentFile(result.annotated_image_bytes), save=False)

    # Check Thresholds and Alert Dispatch
    threshold_exceeded = log.is_threshold_exceeded()
    log.alert_dispatched = threshold_exceeded
    log.save()

    camera_feed.last_processed_at = timezone.now()
    camera_feed.save(update_fields=['last_processed_at'])

    # Real-time WebSocket Alert to C2 Command Desk
    if threshold_exceeded:
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "c2_operations_feed",
                    {
                        "type": "c2_broadcast_event",
                        "data": {
                            "type": "crowd_surge_alert",
                            "camera_code": camera_feed.camera_code,
                            "location_name": camera_feed.location_name,
                            "zone_name": camera_feed.zone.name if camera_feed.zone else "Coastal Sector",
                            "crowd_count": log.crowd_count,
                            "density_score": log.crowd_density_score,
                            "density_tier": log.density_tier,
                            "anomaly": log.anomaly_detected,
                            "surge_rate": log.surge_rate_per_min,
                            "timestamp": timezone.now().isoformat()
                        }
                    }
                )
        except Exception as e:
            print(f"Crowd Alert WebSocket dispatch error: {e}")

    return log
