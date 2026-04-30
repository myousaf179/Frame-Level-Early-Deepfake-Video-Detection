"""Analysis routes.

The legacy endpoints `/analyze` and `/analyze_full` are preserved as synchronous
POST endpoints with the same response keys as the original app.

New optional endpoints `/api/analyze/jobs` and `/api/analyze/jobs/<id>/events`
provide live processing-stage updates without changing the legacy contract.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid

import cv2
from flask import Blueprint, Response, current_app, has_request_context, jsonify, request, send_from_directory, stream_with_context
from werkzeug.utils import secure_filename

from ..services import analysis_service, job_service, user_service
from ..utils.decorators import current_user
from ..utils.helpers import get_client_ip, json_err
from ..utils.validators import is_allowed_filename
from ..extensions import db
from ..models import User

analyze_bp = Blueprint("analyze", __name__)


def _validate_and_save_upload():
    if "video" not in request.files:
        return None, None, None, ("No video file part", 400)
    file = request.files["video"]
    if file.filename == "":
        return None, None, None, ("No selected file", 400)
    allowed = current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    if not is_allowed_filename(file.filename, allowed):
        return None, None, None, ("File extension not allowed", 400)

    filename = secure_filename(file.filename)
    upload_id = uuid.uuid4().hex
    upload_subdir = os.path.join(current_app.config["UPLOAD_DIR"], upload_id)
    os.makedirs(upload_subdir, exist_ok=True)
    upload_path = os.path.join(upload_subdir, filename)
    file.save(upload_path)
    return filename, upload_subdir, upload_path, None


def _video_duration(path: str) -> float:
    try:
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        cap.release()
        if fps <= 0:
            return 0.0
        return float(frames / fps)
    except Exception:
        return 0.0


def _enforce_usage_gate(client_ip: str):
    # Guest analysis is unlimited. Login/signup remains optional for history,
    # profile and admin features, but uploads are never blocked by IP count.
    return None


def _run_analysis(
    *,
    mode: str,
    filename: str,
    upload_subdir: str,
    upload_path: str,
    client_ip: str,
    user_id=None,
    progress_cb=None,
) -> dict:
    run_id = uuid.uuid4().hex
    run_output_dir = os.path.join(current_app.config["OUTPUT_DIR"], run_id)
    os.makedirs(run_output_dir, exist_ok=True)

    started = time.time()
    try:
        if mode == "full":
            result = analysis_service.analyze_video_full(upload_path, run_output_dir, progress_cb=progress_cb)
        else:
            result = analysis_service.analyze_video(upload_path, run_output_dir, progress_cb=progress_cb)
    except Exception:
        shutil.rmtree(upload_subdir, ignore_errors=True)
        shutil.rmtree(run_output_dir, ignore_errors=True)
        raise

    duration = _video_duration(upload_path)
    elapsed = time.time() - started

    # Backward-compatible URL enrichment
    result["run_id"] = run_id
    result["csv_url"] = f"/outputs/{run_id}/{result['csv_filename']}"
    if mode == "full":
        result["segment_urls"] = [
            f"/outputs/{run_id}/{name}" for name in result.get("segment_file_names", [])
        ]
        result["manipulated_merged_url"] = (
            f"/outputs/{run_id}/{result['manipulated_merged_name']}"
            if result.get("manipulated_merged_name")
            else None
        )
        result["thumbnail_urls"] = result.get("thumbnail_urls", [])
        result["segments_csv_url"] = (
            f"/outputs/{run_id}/{result['seg_csv_name']}" if result.get("seg_csv_name") else None
        )
    else:
        result["suspicious_urls"] = [
            f"/outputs/{run_id}/{p}" for p in result.get("suspicious_files", [])
        ]

    user = db.session.get(User, user_id) if user_id else (current_user() if has_request_context() else None)
    if user is None:
        count = user_service.increment_guest_usage(client_ip)
        result["guest_usage"] = {
            "used": count,
            "remaining": "unlimited",
            "client_ip": client_ip,
        }

    user_service.record_analysis(
        user_id=user.id if user else None,
        file_name=filename,
        mode=mode,
        result_label=result.get("final_decision", "UNKNOWN"),
        fake_count=result.get("fake_count", 0),
        real_count=result.get("real_count", 0),
        suspicious_count=result.get("suspicious_count", 0),
        confidence=result.get("final_score", result.get("fake_ratio", 0.0)),
        processing_time=elapsed,
        video_duration=duration,
        client_ip=client_ip,
        run_id=run_id,
    )
    return result


@analyze_bp.route("/analyze_frame", methods=["POST"])
def analyze_frame_route():
    if "frame" not in request.files:
        return jsonify({"error": "No frame file provided"}), 400
    file = request.files["frame"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    try:
        result = analysis_service.analyze_single_frame(file.read())
        if result.get("error"):
            return jsonify({"error": result["error"]}), 400
        return jsonify(result)
    except Exception as e:  # noqa: BLE001 - preserve legacy route shape
        return jsonify({"error": f"Frame analysis failed: {str(e)}"}), 500


@analyze_bp.route("/analyze", methods=["POST"])
def analyze_route():
    client_ip = get_client_ip(request)
    blocked = _enforce_usage_gate(client_ip)
    if blocked:
        return blocked

    filename, upload_subdir, upload_path, err = _validate_and_save_upload()
    if err:
        msg, status = err
        return jsonify({"error": msg}), status
    try:
        user = current_user()
        result = _run_analysis(
            mode="early",
            filename=filename,
            upload_subdir=upload_subdir,
            upload_path=upload_path,
            client_ip=client_ip,
            user_id=user.id if user else None,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Error during analysis: {str(e)}"}), 500


@analyze_bp.route("/analyze_full", methods=["POST"])
def analyze_full_route():
    client_ip = get_client_ip(request)
    blocked = _enforce_usage_gate(client_ip)
    if blocked:
        return blocked

    filename, upload_subdir, upload_path, err = _validate_and_save_upload()
    if err:
        msg, status = err
        return jsonify({"error": msg}), status
    try:
        user = current_user()
        result = _run_analysis(
            mode="full",
            filename=filename,
            upload_subdir=upload_subdir,
            upload_path=upload_path,
            client_ip=client_ip,
            user_id=user.id if user else None,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Error during full analysis: {str(e)}"}), 500


@analyze_bp.route("/api/analyze/jobs", methods=["POST"])
def start_analysis_job():
    client_ip = get_client_ip(request)
    blocked = _enforce_usage_gate(client_ip)
    if blocked:
        return blocked

    mode = (request.form.get("mode") or "early").lower()
    if mode not in {"early", "full"}:
        return json_err("Invalid analysis mode.", 400)
    filename, upload_subdir, upload_path, err = _validate_and_save_upload()
    if err:
        msg, status = err
        return json_err(msg, status)

    job = job_service.create_job(mode)
    app = current_app._get_current_object()
    user = current_user()
    user_id = user.id if user else None

    def _runner():
        def _progress(stage, percent, message):
            job_service.update_job(job.id, stage=stage, percent=percent, message=message)

        return _run_analysis(
            mode=mode,
            filename=filename,
            upload_subdir=upload_subdir,
            upload_path=upload_path,
            client_ip=client_ip,
            user_id=user_id,
            progress_cb=_progress,
        )

    job_service.start_background_job(app, job.id, _runner)
    job_service.cleanup_old_jobs()
    return jsonify({"ok": True, "job_id": job.id, "mode": mode}), 202


@analyze_bp.route("/api/analyze/jobs/<job_id>", methods=["GET"])
def get_analysis_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        return json_err("Job not found.", 404)
    return jsonify(
        {
            "ok": True,
            "job": {
                "id": job.id,
                "mode": job.mode,
                "status": job.status,
                "stage": job.stage,
                "percent": job.percent,
                "message": job.message,
                "result": job.result,
                "error": job.error,
            },
        }
    )


@analyze_bp.route("/api/analyze/jobs/<job_id>/events", methods=["GET"])
def analysis_job_events(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        return json_err("Job not found.", 404)

    def _stream():
        initial = {
            "type": "progress",
            "job_id": job.id,
            "status": job.status,
            "stage": job.stage,
            "percent": job.percent,
            "message": job.message,
        }
        yield f"data: {json.dumps(initial)}\n\n"
        while True:
            try:
                event = job.events.get(timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in {"result", "error"}:
                    break
            except Exception:
                yield "event: ping\ndata: {}\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@analyze_bp.route("/outputs/<run_id>/<path:filename>")
def serve_output(run_id, filename):
    run_dir = os.path.abspath(os.path.join(current_app.config["OUTPUT_DIR"], run_id))
    output_root = os.path.abspath(current_app.config["OUTPUT_DIR"])
    if not run_dir.startswith(output_root):
        return ("Forbidden", 403)
    fullpath = os.path.join(run_dir, filename)
    if not os.path.exists(fullpath):
        return ("Not found", 404)
    return send_from_directory(run_dir, filename, as_attachment=False)
