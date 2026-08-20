from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status

from common.utils import api_response
from .models import VisionCameraFeed, VisionDetectionLog
from .serializers import VisionCameraFeedSerializer, VisionDetectionLogSerializer
from .vision_analyzer import process_camera_feed
from accounts.permissions import authority_required, IsAuthority


@authority_required
def crowd_ai_c2_view(request):
    """Authority C2 AI CCTV & Vision Intelligence Center."""
    feeds = VisionCameraFeed.objects.filter(is_active=True)
    recent_detections = VisionDetectionLog.objects.all().order_by('-timestamp')[:20]

    return render(request, 'authority/crowd_ai.html', {
        'feeds': feeds,
        'recent_detections': recent_detections
    })


# API Endpoints
class CameraFeedsListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        feeds = VisionCameraFeed.objects.filter(is_active=True)
        return api_response(success=True, data=VisionCameraFeedSerializer(feeds, many=True).data)


class AnalyzeImageFrameAPIView(APIView):
    """
    Analyzes a CCTV frame or simulated image for crowd count, density score (0-100),
    sudden crowd surge, and spatial concentration bottlenecks.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        camera_id = request.data.get('camera_id')
        image_file = request.FILES.get('frame_image')

        camera_feed = None
        if camera_id:
            camera_feed = VisionCameraFeed.objects.filter(id=camera_id).first()

        if not image_file:
            # Fallback to camera feed's sample frame
            if camera_feed and camera_feed.sample_frame:
                try:
                    with open(camera_feed.sample_frame.path, 'rb') as f:
                        image_bytes = f.read()
                except Exception:
                    image_bytes = None
            else:
                image_bytes = None

            if not image_bytes:
                # Generate a clean dummy frame with person-like shapes if no sample exists
                import cv2
                import numpy as np
                dummy = np.zeros((480, 640, 3), dtype=np.uint8) + 40
                for x in [120, 200, 280, 360, 440, 520]:
                    cv2.rectangle(dummy, (x, 220), (x + 35, 340), (200, 200, 200), -1)
                _, enc = cv2.imencode('.jpg', dummy)
                image_bytes = enc.tobytes()
        else:
            image_bytes = image_file.read()

        if not camera_feed:
            camera_feed = VisionCameraFeed.objects.first()

        if not camera_feed:
            return api_response(success=False, message="No active camera feed configured", http_code=status.HTTP_400_BAD_REQUEST)

        log = process_camera_feed(camera_feed, image_bytes)

        return api_response(
            success=True,
            message="Frame analyzed successfully",
            data=VisionDetectionLogSerializer(log).data,
            http_code=status.HTTP_200_OK
        )
