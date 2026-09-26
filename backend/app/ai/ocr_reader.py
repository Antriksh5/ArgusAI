"""
ocr_reader.py
-------------
License plate OCR using RapidOCR (ONNX Runtime backend, same model weights
as PaddleOCR but without the paddlepaddle dependency).

The OCR model is loaded once at module-import time so callers can invoke
read_plate() repeatedly without paying the model-load cost on every call.

IMPORTANT NOTES on the current model behaviour:
- rapidocr-onnxruntime ships the Chinese PP-OCRv3 model by default.
- This model was trained primarily on Chinese + digits; it is NOT a dedicated
  Western/Indian-plate model. It can still read digits and some Latin chars
  from Western plates, but confidence scores tend to be low (0.02–0.15).
- We therefore use a much lower text_score threshold (0.02) to capture
  anything the model does read, then apply our own alphanumeric filter.
- For a proper solution, swap in a fine-tuned Latin-plate recognition model.
"""

import re
import cv2
import numpy as np

# ── singleton engine ────────────────────────────────────────────────────────
_ocr_engine = None

# Lowered from the default 0.5 to 0.02 because the Chinese-trained model
# produces low scores on Western/Indian plate characters.  We still apply
# our own alphanumeric filter so noise doesn't propagate to plate_text.
_TEXT_SCORE_THRESHOLD = 0.02


def _get_engine():
    """Return a cached RapidOCR engine, loading it on first call."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise ImportError(
                "rapidocr-onnxruntime is not installed. "
                "Run: pip install rapidocr-onnxruntime"
            ) from exc
        _ocr_engine = RapidOCR(text_score=_TEXT_SCORE_THRESHOLD)
    return _ocr_engine


# ── post-processing ─────────────────────────────────────────────────────────
# Keep only ASCII alphanumeric characters (A-Z, 0-9).
_KEEP_PATTERN = re.compile(r"[^A-Z0-9]")


def _postprocess(text: str) -> str:
    """
    Basic post-processing for a raw OCR string:
    1. Uppercase
    2. Strip leading/trailing whitespace
    3. Remove any character that is not ASCII alphanumeric
    """
    text = text.upper().strip()
    text = _KEEP_PATTERN.sub("", text)
    return text


# ── public API ──────────────────────────────────────────────────────────────

def read_plate(image_path: str) -> dict:
    """
    Run OCR on a single plate-crop image.

    Parameters
    ----------
    image_path : str
        Path to the crop image (JPEG/PNG).

    Returns
    -------
    dict with keys:
        plate_text          str   – cleaned alphanumeric OCR result
                                    (empty string if nothing readable found)
        confidence          float – average confidence of the accepted
                                    text regions (0.0 if nothing found)
        raw_paddleocr_output      – raw result list from RapidOCR for debugging
                                    (None if nothing detected)
    """
    img = cv2.imread(image_path)
    if img is None:
        return {
            "plate_text": "",
            "confidence": 0.0,
            "raw_paddleocr_output": None,
            "error": f"Could not read image: {image_path}",
        }

    # RapidOCR LoadImage accepts BGR numpy arrays directly (it handles
    # the channel order internally).
    h, w = img.shape[:2]

    # Upscale very small crops — recognition degrades badly below ~48 px height.
    # We upscale the BGR image before passing; RapidOCR does its own internal
    # colour handling.
    if h < 64:
        scale = 64 / h
        img = cv2.resize(img, (int(w * scale), 64), interpolation=cv2.INTER_CUBIC)

    engine = _get_engine()

    # RapidOCR returns (result_list, elapse_list) or (None, None).
    # result_list items: [box_points_list, text_str, confidence_str]
    # Note: confidence is stored as a *string* in the output tuple even
    # though it is a float internally before the score filter.
    raw_result, _elapse = engine(img)

    if not raw_result:
        return {
            "plate_text": "",
            "confidence": 0.0,
            "raw_paddleocr_output": None,
        }

    texts = []
    confidences = []
    for item in raw_result:
        # item = [box, text_str, confidence_str]
        _, text, conf_str = item
        try:
            conf = float(conf_str)
        except (ValueError, TypeError):
            conf = 0.0

        cleaned = _postprocess(text)
        if cleaned:                  # only keep non-empty alphanumeric chunks
            texts.append(cleaned)
            confidences.append(conf)

    plate_text = "".join(texts)
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0

    return {
        "plate_text": plate_text,
        "confidence": round(avg_confidence, 4),
        "raw_paddleocr_output": raw_result,
    }


# ── EasyOCR ─────────────────────────────────────────────────────────────────

_easyocr_engine = None

def _get_easyocr_engine():
    global _easyocr_engine
    if _easyocr_engine is None:
        try:
            import easyocr
        except ImportError as exc:
            raise ImportError(
                "easyocr is not installed. Run: pip install easyocr"
            ) from exc
        # configured for English/Latin characters
        _easyocr_engine = easyocr.Reader(['en'])
    return _easyocr_engine

def read_plate_easyocr(image_path: str) -> dict:
    """
    Run OCR on a single plate-crop image using EasyOCR.
    Matches the return signature of read_plate().
    """
    img = cv2.imread(image_path)
    if img is None:
        return {
            "plate_text": "",
            "confidence": 0.0,
            "raw_paddleocr_output": None,
            "error": f"Could not read image: {image_path}",
        }

    # Upscale for EasyOCR as well for fair comparison
    h, w = img.shape[:2]
    if h < 64:
        scale = 64 / h
        img = cv2.resize(img, (int(w * scale), 64), interpolation=cv2.INTER_CUBIC)

    engine = _get_easyocr_engine()
    
    # EasyOCR returns list of (bbox, text, prob)
    # detail=1 is default, returns full details
    raw_result = engine.readtext(img)

    if not raw_result:
        return {
            "plate_text": "",
            "confidence": 0.0,
            "raw_paddleocr_output": None,
        }

    texts = []
    confidences = []
    for item in raw_result:
        box, text, conf = item
        cleaned = _postprocess(text)
        if cleaned:
            texts.append(cleaned)
            confidences.append(float(conf))

    plate_text = "".join(texts)
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0

    return {
        "plate_text": plate_text,
        "confidence": round(avg_confidence, 4),
        "raw_paddleocr_output": raw_result,
    }

