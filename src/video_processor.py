import cv2
import yaml
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from src.detector import get_detector
from src.database import MetadataStore

class VideoProcessor:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.output_dir = Path(self.config['output']['base_dir'])
        self.save_clips = self.config['output']['save_clips']
        self.save_metadata = self.config['output']['save_metadata']

        # Parámetros de procesamiento
        self.inference_size = self.config['processing']['inference_size']
        self.motion_fps = self.config['processing']['motion_analysis_fps']
        self.motion_min_area = self.config['processing']['motion_min_area']
        self.motion_threshold = self.config['processing']['motion_threshold']
        self.motion_absence_close = self.config['processing']['motion_absence_to_close']
        self.ai_skip = self.config['processing']['skip_frames_in_segment']
        self.min_detections = self.config['processing']['min_person_detections']
        self.absence_seconds = self.config['processing']['min_absence_seconds']
        self.roi_upsample = self.config['processing'].get('roi_upsample', False)
        self.margin_seconds = self.config['processing']['margin_seconds']

        # ROI
        self.roi_config = self.config.get('roi', {})
        self.roi_enabled = self.roi_config.get('enabled', False)

        self.detector = get_detector(config_path)
        self.metadata_store = MetadataStore()

    def _apply_roi(self, frame: np.ndarray) -> np.ndarray:
        if not self.roi_enabled:
            return frame
        h, w = frame.shape[:2]
        x1 = int(w * self.roi_config.get('x1', 0.0))
        y1 = int(h * self.roi_config.get('y1', 0.0))
        x2 = int(w * self.roi_config.get('x2', 1.0))
        y2 = int(h * self.roi_config.get('y2', 1.0))
        margin = self.roi_config.get('margin', 0)
        x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
        x2, y2 = min(w, x2 + margin), min(h, y2 + margin)
        return frame[y1:y2, x1:x2]

    def process_video(self, video_path: str, progress_callback=None) -> List[Dict]:
        events = []
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            print(f"[ERROR] Video no encontrado: {video_path}")
            return events

        # Obtener timestamp de video
        video_timestamp = self._parse_video_timestamp(video_path_obj.stem)
        if video_timestamp is None:
            print(f"[WARN] No se pudo extraer timestamp de {video_path_obj.name}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"[ERROR] No se pudo abrir {video_path}")
            return events

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0

        analyze_every_n_frames = max(1, int(fps / self.motion_fps))

        segments = []
        current_segment_start = -1
        last_motion_idx = -1
        frame_idx = 0
        prev_gray = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Procesar solo frames seleccionados para movimiento
            if frame_idx % analyze_every_n_frames != 0:
                frame_idx += 1
                continue

            roi_frame = self._apply_roi(frame)
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)

            motion_detected = False
            if prev_gray is not None:
                frame_delta = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                valid_contours = [c for c in contours if cv2.contourArea(c) > self.motion_min_area]
                if valid_contours:
                    motion_detected = True

            if motion_detected:
                if current_segment_start == -1:
                    current_segment_start = frame_idx
                last_motion_idx = frame_idx
            else:
                if current_segment_start != -1 and frame_idx - last_motion_idx >= self.motion_absence_close * fps:
                    segments.append((current_segment_start, frame_idx))
                    current_segment_start = -1
                    last_motion_idx = -1

            prev_gray = gray.copy()
            frame_idx += 1

            if progress_callback:
                progress_callback(frame_idx, total_frames, video_path_obj.name, "Detección de movimiento")

        # Capturar el último segmento si terminó abierto
        if current_segment_start != -1:
            segments.append((current_segment_start, frame_idx))

        cap.release()

        if not segments:
            print("[INFO] Sin segmentos de movimiento.")
            return events

        # FASE DE VERIFICACIÓN CON IA
        cap = cv2.VideoCapture(str(video_path))
        confirmed_segments = self._verify_and_refine(cap, segments, fps, duration_sec, progress_callback)
        cap.release()

        # FASE DE EXPORTACIÓN DE CLIPS Y METADATOS
        for seg_start, seg_end in confirmed_segments:
            start_sec = max(0, seg_start / fps - self.margin_seconds)
            end_sec = min(duration_sec, seg_end / fps + self.margin_seconds)
            event = self._create_event(video_path, start_sec, end_sec, fps, video_timestamp)
            if self.save_clips:
                self._extract_clip(video_path, start_sec, end_sec, event)
            events.append(event)

        if self.save_metadata and events:
            self.metadata_store.save_events(events, str(self.output_dir))

        return events

    def _verify_and_refine(self, cap, segments: List[Tuple[int, int]], fps: float, duration: float, progress_callback=None) -> List[Tuple[int, int]]:
        refined = []
        for seg_idx, (seg_start, seg_end) in enumerate(segments):
            cap.set(cv2.CAP_PROP_POS_FRAMES, seg_start)
            person_frames = []

            # Leer frames secuencialmente desde el inicio del segmento
            current_frame = seg_start
            while current_frame <= seg_end:
                ret, frame = cap.read()
                if not ret:
                    break
                if (current_frame - seg_start) % self.ai_skip == 0:
                    roi = self._apply_roi(frame)
                    if self.roi_upsample:
                        roi = cv2.resize(roi, (self.inference_size, self.inference_size))
                    detections = self.detector.detect(roi, conf=0.25)
                    if detections:
                        person_frames.append(current_frame)
                current_frame += 1

                if progress_callback:
                    progress_callback(current_frame, seg_end, f"Verificando seg. {seg_idx+1}/{len(segments)}", f"IA: {len(detections) if 'detections' in locals() else 0} personas")

            if person_frames and len(person_frames) >= self.min_detections:
                refined_start = person_frames[0]
                refined_end = person_frames[-1]
                refined.append((refined_start, refined_end))

        return refined

    def _parse_video_timestamp(self, stem: str) -> Optional[datetime]:
        try:
            parts = stem.split('_')
            if len(parts[0]) == 14:
                return datetime.strptime(parts[0], "%Y%m%d%H%M%S")
        except:
            pass
        return None

    def _create_event(self, video_path: str, start_sec: float, end_sec: float, fps: float, video_dt: Optional[datetime]) -> Dict:
        start_real = video_dt + timedelta(seconds=start_sec) if video_dt else None
        end_real = video_dt + timedelta(seconds=end_sec) if video_dt else None

        return {
            'video_name': Path(video_path).name,
            'start_time': start_sec,
            'end_time': end_sec,
            'date': start_real.strftime('%Y-%m-%d') if start_real else 'N/A',
            'time_start': start_real.strftime('%H:%M:%S') if start_real else 'N/A',
            'time_end': end_real.strftime('%H:%M:%S') if end_real else 'N/A',
            'clip_path': None
        }

    def _extract_clip(self, video_path: str, start_sec: float, end_sec: float, event: Dict) -> bool:
        clips_dir = self.output_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip_name = f"{Path(video_path).stem}_{int(start_sec)}_{int(end_sec)}.mp4"
        clip_path = str(clips_dir / clip_name)

        try:
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-ss", str(start_sec),
                "-i", video_path, "-t", str(end_sec - start_sec),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", clip_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            event['clip_path'] = clip_path
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo extraer clip: {e}")
            return False