"""Preserved deepfake analysis pipeline wrapper.

The original working `app.py` was backed up before refactoring. This module
loads that original code and delegates the heavy detection work to its original
functions. The Flask routes are not reused; only the pipeline helpers are.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import contextlib
import csv
import io
import math
import os
from typing import Optional

import cv2
import numpy as np
import torch

_BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_BACKUP_PATH = os.path.join(_BASE_DIR, "backups", "app.py.bak")
_pipeline = None


def _configure_detection_thresholds(module):
    """Apply production thresholds without changing the original pipeline code.

    Previous full-video sliding-window thresholds were 0.30/0.35. That could
    mark real videos fake too easily. The project requirement now is: in any
    one-second window, at least half the frames must be FAKE before the video
    is considered manipulated.
    """
    module.LOW_FPS_THRESHOLD = 0.50
    module.HIGH_FPS_THRESHOLD = 0.50
    module.EARLY_STOP_WEIGHTED_RATIO = 0.50
    module.WEIGHT_SUSPICIOUS = 0.0
    module.FINAL_FAKE_SCORE_THRESHOLD = 999.0
    module.SUSPICIOUS_RATIO_FAKE_THRESHOLD = 999.0


def _read_prediction_rows(output_subdir):
    csv_path = os.path.join(output_subdir, "frame_predictions.csv")
    if not os.path.exists(csv_path):
        return []
    rows = []
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                frame = int(row.get("frame", ""))
            except ValueError:
                continue
            rows.append({"frame": frame, "label": (row.get("label") or "").upper()})
    return rows


def _fps_for_video(video_path):
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        return max(1, int(round(fps)))
    finally:
        cap.release()


def _apply_per_second_fake_policy(result, video_path, output_subdir, mode):
    """Final decision rule requested by the user.

    A video is FAKE only if at least one one-second bucket has FAKE frames
    >= 50% of FPS. Example: 30fps needs 15+ FAKE frames in that second.
    Scattered fake frames across the full video no longer make the whole video
    fake.
    """
    rows = _read_prediction_rows(output_subdir)
    fps = _fps_for_video(video_path)
    min_fake_per_second = int(math.ceil(fps * 0.50))
    per_second = {}
    for row in rows:
        sec = row["frame"] // fps
        bucket = per_second.setdefault(sec, {"fake": 0, "total": 0})
        if row["label"] != "SKIP":
            bucket["total"] += 1
        if row["label"] == "FAKE":
            bucket["fake"] += 1

    max_fake = max((bucket["fake"] for bucket in per_second.values()), default=0)
    fake_seconds = [
        {"second": sec, "fake_frames": bucket["fake"], "threshold": min_fake_per_second}
        for sec, bucket in sorted(per_second.items())
        if bucket["fake"] >= min_fake_per_second
    ]

    result["per_second_policy"] = {
        "fps": fps,
        "threshold_percent": 50,
        "min_fake_frames_per_second": min_fake_per_second,
        "max_fake_frames_in_any_second": max_fake,
        "fake_seconds": fake_seconds,
    }

    if fake_seconds:
        result["final_decision"] = "FAKE"
        policy_text = (
            f"Per-second rule: FAKE because second {fake_seconds[0]['second']} has "
            f"{fake_seconds[0]['fake_frames']}/{fps} fake frames "
            f"(threshold {min_fake_per_second})."
        )
    else:
        result["final_decision"] = "REAL"
        result["early_stop_triggered"] = False
        result["early_stop_frame_idx"] = None
        if mode == "full":
            result["segment_info"] = []
            result["segment_file_names"] = []
            result["manipulated_merged_name"] = None
        policy_text = (
            f"Per-second rule: REAL because max fake frames in any 1-second window "
            f"is {max_fake}/{fps}, below threshold {min_fake_per_second}."
        )

    result["summary_text"] = f"{policy_text} {result.get('summary_text', '')}".strip()
    return result


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    loader = importlib.machinery.SourceFileLoader("_deepfake_defender_original_pipeline", _BACKUP_PATH)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        loader.exec_module(module)
    module.BASE_DIR = _BASE_DIR
    module.UPLOAD_DIR = os.path.join(_BASE_DIR, "uploads")
    module.OUTPUT_DIR = os.path.join(_BASE_DIR, "outputs")
    module.MODEL = None
    _configure_detection_thresholds(module)
    _pipeline = module
    return module


def _progress(progress_cb, stage, percent, message):
    if progress_cb:
        try:
            progress_cb(stage, percent, message)
        except Exception:
            pass


def analyze_video(video_path, output_subdir, progress_cb=None):
    p = _load_pipeline()
    _progress(progress_cb, "frame_extraction", 10, "Reading video frames")
    _progress(progress_cb, "face_detection", 25, "Detecting faces")
    _progress(progress_cb, "model_inference", 45, "Running ConvNeXt inference")
    result = p.analyze_video(video_path, output_subdir)
    result = _apply_per_second_fake_policy(result, video_path, output_subdir, mode="early")
    _progress(progress_cb, "output_generation", 92, "Writing CSV and thumbnails")
    _progress(progress_cb, "completed", 100, "Analysis complete")
    return result


def analyze_video_full(video_path, output_subdir, progress_cb=None):
    p = _load_pipeline()
    _progress(progress_cb, "frame_extraction", 10, "Reading video frames")
    _progress(progress_cb, "face_detection", 25, "Detecting faces")
    _progress(progress_cb, "model_inference", 45, "Running ConvNeXt inference")
    result = p.analyze_video_full(video_path, output_subdir)
    result = _apply_per_second_fake_policy(result, video_path, output_subdir, mode="full")
    _progress(progress_cb, "segment_detection", 82, "Detecting manipulated segments")
    _progress(progress_cb, "output_generation", 92, "Writing CSV, thumbnails and clips")
    _progress(progress_cb, "completed", 100, "Analysis complete")
    return result


def analyze_single_frame(file_bytes: bytes):
    p = _load_pipeline()
    if p.MODEL is None:
        p.MODEL = p.load_model()
    file_arr = np.frombuffer(file_bytes, np.uint8)
    img_bgr = cv2.imdecode(file_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"error": "Invalid image file"}
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    mtcnn = p.get_mtcnn()
    faces, face_probs = mtcnn.detect(img_rgb, landmarks=False)
    if faces is None or len(faces) == 0:
        return {"label": "NO FACE", "conf_fake": 0.0, "conf_real": 0.0, "face_detected": False}
    x1, y1, x2, y2 = [int(c) for c in faces[0]]
    x1 = max(0, x1 - 10); y1 = max(0, y1 - 10)
    x2 = min(img_rgb.shape[1], x2 + 10); y2 = min(img_rgb.shape[0], y2 + 10)
    face_crop = img_rgb[y1:y2, x1:x2]
    if face_crop.size == 0:
        return {"label": "NO FACE", "conf_fake": 0.0, "conf_real": 0.0, "face_detected": False}
    transformed = p.transform(image=face_crop)
    input_tensor = transformed["image"].unsqueeze(0).to(p.DEVICE)
    with torch.no_grad():
        logits = p.MODEL(input_tensor)
        probs = torch.softmax(logits, dim=1)
        conf_fake = float(probs[0, p.FAKE_CLASS_IDX].cpu())
        conf_real = float(probs[0, p.REAL_CLASS_IDX].cpu())
    label = "FAKE" if conf_fake > conf_real else "REAL"
    face_prob = float(face_probs[0]) if face_probs is not None and len(face_probs) > 0 else 0.99
    return {
        "label": label,
        "conf_fake": round(conf_fake, 4),
        "conf_real": round(conf_real, 4),
        "face_detected": True,
        "face_prob": round(face_prob, 4),
    }
