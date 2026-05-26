# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""OCR service for extracting electricity data from screenshots."""

import os
import time
import uuid
import threading
from backend.utils.parsers import parse_screenshot_data
from backend.utils.logger import get_logger, get_ocr_logger, log_exception

logger = get_logger(__name__)
ocr_logger = get_ocr_logger()


class OcrService:
    """Handles screenshot OCR processing pipeline.

    Supports three backends (tried in order):
    - RapidOCR (ONNX) - best Chinese recognition, lightweight
    - Tesseract (via pytesseract) - fallback
    - PaddleOCR - optional, alternative
    """

    def __init__(self):
        self._paddle_ocr = None
        self._rapid_ocr = None
        self._jobs = {}  # job_id -> job dict
        self._jobs_lock = threading.Lock()

    def _get_text_blocks_rapid(self, image_path):
        """Extract text blocks using RapidOCR (ONNX). Best Chinese recognition."""
        if self._rapid_ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid_ocr = RapidOCR()

        result, _ = self._rapid_ocr(image_path)
        if not result:
            return []

        blocks = []
        for item in result:
            bbox, text, conf = item
            x = int(bbox[0][0])
            y = int(bbox[0][1])
            w = int(bbox[1][0] - bbox[0][0])
            h = int(bbox[2][1] - bbox[0][1])
            blocks.append({
                'text': text,
                'x': x, 'y': y, 'w': w, 'h': h,
                'conf': conf,
            })
        return blocks

    def _get_text_blocks_tesseract(self, image_path):
        """Extract text blocks using Tesseract OCR."""
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)

        blocks = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text:
                blocks.append({
                    'text': text,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i],
                    'conf': data['conf'][i],
                })
        return blocks

    def _get_text_blocks_paddle(self, image_path):
        """Extract text blocks using PaddleOCR."""
        if self._paddle_ocr is None:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True, lang='ch', show_log=False,
            )

        result = self._paddle_ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return []

        blocks = []
        for line in result[0]:
            bbox = line[0]
            text = line[1][0]
            confidence = line[1][1]
            # Convert bbox to x, y, w, h format
            x = int(bbox[0][0])
            y = int(bbox[0][1])
            w = int(bbox[1][0] - bbox[0][0])
            h = int(bbox[2][1] - bbox[0][1])
            blocks.append({
                'text': text,
                'x': x, 'y': y, 'w': w, 'h': h,
                'conf': confidence,
            })
        return blocks

    def process_screenshot(self, image_path, year=None, month=None):
        """Process a screenshot and extract electricity data."""
        logger.debug(f"Processing screenshot: {image_path}, year={year}, month={month}")
        ocr_logger.info(f"===== 开始 OCR 处理: {os.path.basename(image_path)}, year={year}, month={month} =====")

        text_blocks = None
        backend = None

        # 1. Try RapidOCR (best Chinese recognition)
        try:
            text_blocks = self._get_text_blocks_rapid(image_path)
            backend = 'rapidocr'
            ocr_logger.info(f"OCR 引擎: RapidOCR, 提取到 {len(text_blocks)} 个 text block")
            logger.debug(f"RapidOCR extracted {len(text_blocks)} text blocks")
        except ImportError:
            ocr_logger.info("RapidOCR 不可用, 尝试 Tesseract")
            logger.debug("RapidOCR not available, trying Tesseract")
        except Exception as e:
            ocr_logger.warning(f"RapidOCR 处理失败: {type(e).__name__}: {e}")
            log_exception(logger, e, {'image': image_path, 'backend': 'rapidocr'})

        # 2. Fallback to PaddleOCR
        if not text_blocks:
            try:
                text_blocks = self._get_text_blocks_paddle(image_path)
                backend = 'paddleocr'
                ocr_logger.info(f"OCR 引擎: PaddleOCR, 提取到 {len(text_blocks)} 个 text block")
                logger.debug(f"PaddleOCR extracted {len(text_blocks)} text blocks")
            except ImportError:
                ocr_logger.info("PaddleOCR 不可用, 尝试 Tesseract")
                logger.debug("PaddleOCR not available, trying Tesseract")
            except Exception as e:
                ocr_logger.warning(f"PaddleOCR 处理失败: {type(e).__name__}: {e}")
                log_exception(logger, e, {'image': image_path, 'backend': 'paddleocr'})

        # 3. Fallback to Tesseract
        if not text_blocks:
            try:
                text_blocks = self._get_text_blocks_tesseract(image_path)
                backend = 'tesseract'
                ocr_logger.info(f"OCR 引擎: Tesseract, 提取到 {len(text_blocks)} 个 text block")
                logger.debug(f"Tesseract OCR extracted {len(text_blocks)} text blocks")
            except ImportError:
                ocr_logger.error("无可用 OCR 引擎 (rapidocr/paddleocr/pytesseract 均未安装)")
                logger.error("No OCR engine available")
                return {
                    'error': '未安装 OCR 引擎。请安装 rapidocr_onnxruntime、paddleocr 或 pytesseract',
                    'hint': 'manual_fallback',
                }
            except Exception as e:
                ocr_logger.error(f"Tesseract 处理失败: {type(e).__name__}: {e}")
                log_exception(logger, e, {'image': image_path, 'backend': 'tesseract'})
                return {'error': f'OCR 处理失败: {str(e)}'}

        if not text_blocks:
            ocr_logger.warning(f"OCR 未识别到任何文本: {image_path}")
            logger.warning(f"OCR found no text blocks in {image_path}")
            return {'error': 'OCR 未识别到任何文本'}

        # Log text block details
        self._log_text_blocks(text_blocks, backend)

        # Use new parser: parse detailed data table only
        parsed = parse_screenshot_data(text_blocks, year or 2026, month or 1)

        records_count = len(parsed.get('daily_records', []))
        warnings_count = len(parsed.get('warnings', []))
        ocr_logger.info(f"===== OCR 完成 ({backend}): {records_count} 条记录, {warnings_count} 个警告 =====")
        logger.info(f"OCR complete ({backend}): {records_count} records, {warnings_count} warnings")

        return {
            'success': True,
            'backend': backend,
            'raw_blocks': text_blocks,
            'parsed': parsed,
            'block_count': len(text_blocks),
        }

    def _log_text_blocks(self, text_blocks, backend):
        """Log detailed text block information for debugging."""
        total = len(text_blocks)
        confidences = [b.get('conf', 0) for b in text_blocks if isinstance(b.get('conf'), (int, float))]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        low_conf = sum(1 for c in confidences if c < 50)

        ocr_logger.info(
            f"Text blocks 汇总: 总数={total}, 平均置信度={avg_conf:.1f}, "
            f"低置信度(<50)={low_conf}"
        )

        # Log first 30 blocks as sample
        sample = text_blocks[:30]
        for i, block in enumerate(sample):
            text = block.get('text', '')
            conf = block.get('conf', '-')
            ocr_logger.debug(f"  block[{i}]: conf={conf} text='{text}'")

        if total > 30:
            ocr_logger.debug(f"  ... 省略剩余 {total - 30} 个 block")

    def process_and_build_records(self, image_path, year, month):
        """Full pipeline: OCR + parse detail table."""
        result = self.process_screenshot(image_path, year, month)

        if 'error' in result:
            return result

        parsed = result['parsed']
        daily_records = parsed.get('daily_records', [])

        logger.info(f"Built {len(daily_records)} records from {image_path}")

        return {
            'success': True,
            'backend': result.get('backend', 'unknown'),
            'records': daily_records,
            'days_extracted': len(daily_records),
            'warnings': parsed.get('warnings', []),
            'raw_blocks': result['raw_blocks'],
            'block_count': result['block_count'],
        }

    def process_directory(self, directory_path, year=None, month=None):
        """Batch process all images in a directory.

        Args:
            directory_path: Path to directory containing images.
            year: Year context for date parsing.
            month: Month context for date parsing.

        Returns:
            dict with total_files, success_count, fail_count, results, all_records.
        """
        from backend.config import IMAGE_EXTENSIONS

        logger.info(f"Processing directory: {directory_path}, year={year}, month={month}")

        if not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return {'error': f'目录不存在: {directory_path}'}

        image_files = sorted([
            f for f in os.listdir(directory_path)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        ])

        logger.info(f"Found {len(image_files)} image files in directory")

        if not image_files:
            return {
                'total_files': 0,
                'success_count': 0,
                'fail_count': 0,
                'results': [],
                'all_records': [],
            }

        results = []
        all_records = []
        success_count = 0
        fail_count = 0

        for filename in image_files:
            filepath = os.path.join(directory_path, filename)
            result = self.process_and_build_records(filepath, year, month)

            if 'error' in result:
                logger.error(f"Failed to process {filename}: {result['error']}")
                results.append({
                    'filename': filename,
                    'status': 'error',
                    'error': result['error'],
                })
                fail_count += 1
            else:
                records = result.get('records', [])
                results.append({
                    'filename': filename,
                    'status': 'success',
                    'records': records,
                    'days_extracted': len(records),
                    'warnings': result.get('warnings', []),
                })
                all_records.extend(records)
                success_count += 1

        logger.info(f"Directory processing complete: {success_count} success, {fail_count} failed, {len(all_records)} total records")

        return {
            'total_files': len(image_files),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
            'all_records': all_records,
        }

    # --- Async batch job methods ---

    def start_batch_job(self, directory_path, year=None, month=None):
        """Start an async batch job. Returns job_id immediately."""
        from backend.config import IMAGE_EXTENSIONS

        logger.info(f"Starting batch job: directory={directory_path}, year={year}, month={month}")

        if not os.path.isdir(directory_path):
            logger.error(f"Batch job: directory not found: {directory_path}")
            return {'error': f'目录不存在: {directory_path}'}

        image_files = sorted([
            f for f in os.listdir(directory_path)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        ])

        job_id = str(uuid.uuid4())
        with self._jobs_lock:
            self._jobs[job_id] = {
                'job_id': job_id,
                'status': 'processing',
                'total': len(image_files),
                'processed': 0,
                'current_file': '',
                'success_count': 0,
                'fail_count': 0,
                'results': [],
                'all_records': [],
            }

        if not image_files:
            logger.warning(f"Batch job {job_id}: no image files found in directory")
            with self._jobs_lock:
                self._jobs[job_id]['status'] = 'completed'
            return {'job_id': job_id, 'total': 0}

        logger.info(f"Batch job {job_id} started: {len(image_files)} files to process")

        t = threading.Thread(
            target=self._run_batch,
            args=(job_id, directory_path, image_files, year, month),
            daemon=True,
        )
        t.start()

        return {'job_id': job_id, 'total': len(image_files)}

    def _run_batch(self, job_id, directory_path, image_files, year, month):
        """Background worker: process images and update job state."""
        with self._jobs_lock:
            job = self._jobs[job_id]

        logger.info(f"Batch job {job_id}: worker started, processing {len(image_files)} files")
        ocr_logger.info(f"批量任务 {job_id[:8]} 开始: {len(image_files)} 个文件")
        batch_start = time.time()

        for filename in image_files:
            if job['status'] != 'processing':
                logger.info(f"Batch job {job_id}: cancelled at {job['processed']}/{job['total']}")
                break  # cancelled

            job['current_file'] = filename
            filepath = os.path.join(directory_path, filename)
            file_start = time.time()

            ocr_logger.info(f"[{job_id[:8]}] 处理文件 ({job['processed']+1}/{job['total']}): {filename}")

            result = self.process_and_build_records(filepath, year, month)

            elapsed = time.time() - file_start
            ocr_logger.info(f"[{job_id[:8]}] {filename} 完成, 耗时 {elapsed:.1f}s")

            if 'error' in result:
                logger.error(f"Batch job {job_id}: failed to process {filename}: {result['error']}")
                job['results'].append({
                    'filename': filename,
                    'status': 'error',
                    'error': result['error'],
                })
                job['fail_count'] += 1
            else:
                records = result.get('records', [])
                file_result = {
                    'filename': filename,
                    'status': 'success',
                    'records': records,
                    'days_extracted': len(records),
                    'warnings': result.get('warnings', []),
                }
                # Attach raw OCR texts for debugging when no records found
                if not records:
                    raw_texts = [b['text'] for b in result.get('raw_blocks', [])[:30]]
                    file_result['raw_texts'] = raw_texts
                    logger.warning(f"Batch job {job_id}: {filename} extracted 0 records, raw texts attached")
                job['results'].append(file_result)
                job['all_records'].extend(records)
                job['success_count'] += 1

            job['processed'] += 1
            logger.debug(f"Batch job {job_id}: progress {job['processed']}/{job['total']}")

        job['status'] = 'completed'
        job['current_file'] = ''

        batch_elapsed = time.time() - batch_start
        ocr_logger.info(
            f"批量任务 {job_id[:8]} 完成: {job['success_count']} 成功, "
            f"{job['fail_count']} 失败, {len(job['all_records'])} 条记录, "
            f"总耗时 {batch_elapsed:.1f}s"
        )
        logger.info(f"Batch job {job_id} completed: {job['success_count']} success, {job['fail_count']} failed, {len(job['all_records'])} total records")

    def get_job_status(self, job_id):
        """Return current job state snapshot."""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return {'error': '任务不存在', 'status': 'not_found'}
            return dict(job)