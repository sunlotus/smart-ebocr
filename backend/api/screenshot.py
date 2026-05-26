# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import os
import tempfile
import time
from flask import Blueprint, Response, request, jsonify, current_app, g

from backend.services.ocr_service import OcrService
from backend.services.data_service import DataService
from backend.config import IMAGE_EXTENSIONS
from backend.api.decorators import require_login_or_default, get_current_user_or_default
from backend.models.family_member import FamilyMember
from backend.utils.logger import get_logger, log_exception

bp = Blueprint('screenshot', __name__)
ocr_service = OcrService()
logger = get_logger(__name__)


def _safe_path(requested_path):
    """Validate that a path is within the allowed upload directory."""
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    resolved = os.path.abspath(requested_path)
    if not resolved.startswith(upload_folder):
        return None
    return resolved


def _get_user_context():
    """获取当前用户上下文（user_id, family_member_id）"""
    user = g.current_user
    member_id = request.args.get('family_member_id', type=int)
    if not member_id:
        data = request.get_json(silent=True) or {}
        member_id = data.get('family_member_id')
        if not member_id:
            member_id = request.form.get('family_member_id', type=int)

    if member_id and user.plan_name in ['supporter', 'premium', 'super']:
        member = FamilyMember.query.filter_by(id=member_id, parent_user_id=user.id).first()
        if member:
            return {'user_id': user.id, 'family_member_id': member_id}

    return {'user_id': user.id, 'family_member_id': None}


@bp.route('/upload', methods=['POST'])
@require_login_or_default
def upload():
    """Upload screenshot and run OCR."""
    if 'file' not in request.files:
        logger.warning("Upload attempt without file")
        return jsonify({'error': '未提供文件'}), 400
    file = request.files['file']
    if file.filename == '':
        logger.warning("Upload attempt with empty filename")
        return jsonify({'error': '未选择文件'}), 400

    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)

    logger.info(f"Screenshot upload: {file.filename}, year={year}, month={month}")

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    file.save(filepath)

    try:
        if year and month:
            result = ocr_service.process_and_build_records(filepath, year, month)
        else:
            result = ocr_service.process_screenshot(filepath)

        if 'error' in result:
            logger.error(f"OCR failed for {file.filename}: {result['error']}")
            return jsonify(result), 422

        logger.info(f"OCR successful for {file.filename}: {len(result.get('daily_records', []))} records")
        return jsonify(result)
    except Exception as e:
        log_exception(logger, e, {'file': file.filename, 'year': year, 'month': month})
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@bp.route('/confirm', methods=['POST'])
@require_login_or_default
def confirm_ocr():
    """Confirm and save OCR results to database."""
    data = request.get_json()
    if not data or 'records' not in data:
        logger.warning("Confirm OCR attempt without records")
        return jsonify({'error': 'records 数组必填'}), 400

    record_count = len(data['records'])
    conflict_mode = data.get('conflict_mode', 'overwrite')
    ctx = _get_user_context()

    logger.info(f"Confirming OCR: saving {record_count} records, conflict_mode={conflict_mode}, user_id={ctx['user_id']}, member_id={ctx['family_member_id']}")

    result = DataService.batch_upsert(
        data['records'],
        conflict_mode=conflict_mode,
        user_id=ctx['user_id'],
        family_member_id=ctx['family_member_id'],
    )
    logger.info(f"OCR confirmation complete: saved={result['saved']}, skipped={result['skipped']}")
    return jsonify(result)


@bp.route('/scan-dir', methods=['GET'])
@require_login_or_default
def scan_dir():
    """List directories containing images under the upload folder."""
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])

    subdir = request.args.get('base_dir', '')
    if subdir:
        scan_root = _safe_path(os.path.join(upload_folder, subdir))
        if not scan_root:
            return jsonify({'error': '无效的目录路径'}), 400
    else:
        scan_root = upload_folder

    if not os.path.isdir(scan_root):
        return jsonify({'directories': []})

    directories = []
    for dirpath, dirnames, filenames in os.walk(scan_root):
        image_count = sum(
            1 for f in filenames
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        )
        if image_count > 0:
            rel_path = os.path.relpath(dirpath, upload_folder)
            if rel_path == '.':
                rel_path = ''
            directories.append({
                'path': rel_path,
                'file_count': image_count,
            })

    directories.sort(key=lambda d: d['path'])
    return jsonify({'directories': directories})


@bp.route('/batch', methods=['POST'])
@require_login_or_default
def batch_process():
    """Start async batch OCR job. Returns job_id immediately.

    JSON body: { directory, year?, month?, family_member_id? }
    """
    data = request.get_json()
    if not data or not data.get('directory'):
        logger.warning("Batch process attempt without directory")
        return jsonify({'error': 'directory 参数必填'}), 400

    directory = data['directory']
    year = data.get('year')
    month = data.get('month')

    logger.info(f"Starting batch OCR: directory={directory}, year={year}, month={month}")

    if os.path.isabs(directory):
        safe = _safe_path(directory)
    else:
        upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        safe = _safe_path(os.path.join(upload_folder, directory))

    if not safe:
        logger.warning(f"Batch process: unsafe directory path: {directory}")
        return jsonify({'error': '目录路径不在允许范围内'}), 400
    if not os.path.isdir(safe):
        logger.warning(f"Batch process: directory not found: {directory}")
        return jsonify({'error': f'目录不存在: {directory}'}), 404

    result = ocr_service.start_batch_job(safe, year, month)

    if 'error' in result:
        logger.error(f"Batch OCR start failed: {result['error']}")
        return jsonify(result), 422

    logger.info(f"Batch OCR started: job_id={result['job_id']}")
    return jsonify(result)


@bp.route('/batch/<job_id>/stream')
def batch_stream(job_id):
    """SSE endpoint: stream batch job progress in real-time."""
    job = ocr_service.get_job_status(job_id)
    if job.get('status') == 'not_found':
        return jsonify({'error': '任务不存在'}), 404

    def generate():
        last_processed = -1
        start_time = time.time()
        timeout = 600  # 10 minutes max
        while True:
            if time.time() - start_time > timeout:
                yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
                break

            job = ocr_service.get_job_status(job_id)
            if 'error' in job:
                yield f"data: {json.dumps(job)}\n\n"
                break

            # Only emit when progress changes
            if job['processed'] != last_processed or job['status'] == 'completed':
                last_processed = job['processed']
                yield f"data: {json.dumps(job)}\n\n"

                if job['status'] == 'completed':
                    break

            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@bp.route('/batch-upload', methods=['POST'])
@require_login_or_default
def batch_upload():
    """Upload multiple files and process them with OCR."""
    files = request.files.getlist('files')
    if not files:
        logger.warning("Batch upload attempt without files")
        return jsonify({'error': '未提供文件'}), 400

    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)

    file_count = len([f for f in files if f.filename])
    logger.info(f"Batch upload: {file_count} files, year={year}, month={month}")

    with tempfile.TemporaryDirectory() as tmpdir:
        for f in files:
            if f.filename:
                filepath = os.path.join(tmpdir, f.filename)
                f.save(filepath)

        result = ocr_service.process_directory(tmpdir, year, month)

    if 'error' in result:
        logger.error(f"Batch upload OCR failed: {result['error']}")
        return jsonify(result), 422

    logger.info(f"Batch upload complete: {len(result.get('daily_records', []))} records")
    return jsonify(result)
