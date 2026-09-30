"""
run_ocr_v2_comparison.py
------------------------
Compare RapidOCR and Tesseract on plate crops.

Usage:
    python backend/scripts/run_ocr_v2_comparison.py --crops-dir <path> [--use-easyocr]

Notes:
    EasyOCR uses a full CRAFT + CRNN neural network (PyTorch) and takes 5–30s
    per crop on CPU. It is disabled by default. Pass --use-easyocr if you
    really want to run it on a small sample.
"""

import os
import json
import glob
import sys
import argparse
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.ai.ocr_reader import read_plate
import pytesseract
import cv2

OUTPUT_FILE = "data/detections/ocr_results_v2_comparison.json"

def read_plate_tesseract(image_path: str) -> dict:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"plate_text": "", "confidence": 0.0, "error": "unreadable"}
        # Preprocessing to improve Tesseract
        img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        text = text.strip()
        # Tesseract doesn't give a simple document confidence out of the box in this mode easily, so we fake 1.0 if found
        conf = 1.0 if text else 0.0
        return {"plate_text": text, "confidence": conf}
    except Exception as e:
        return {"plate_text": "", "confidence": 0.0, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Compare OCR engines on plate crops")
    parser.add_argument("--crops-dir", required=True, help="Directory containing crop images")
    parser.add_argument("--use-easyocr", action="store_true", help="Include EasyOCR (very slow on CPU!)")
    args = parser.parse_args()

    crops_dir = args.crops_dir
    if not os.path.isdir(crops_dir):
        print(f"Error: Crops directory '{crops_dir}' does not exist.")
        sys.exit(1)

    crops = sorted(glob.glob(os.path.join(crops_dir, "*.jpg")) + glob.glob(os.path.join(crops_dir, "*.png")))

    if not crops:
        print(f"No crops found in {crops_dir}")
        sys.exit(1)

    print(f"Found {len(crops)} crops. Running RapidOCR + Tesseract...")
    if args.use_easyocr:
        print("  ⚠️  EasyOCR is enabled. This will be very slow on CPU.\n")

    results = []
    t_start = time.time()

    for i, crop_path in enumerate(crops):
        filename = os.path.basename(crop_path)

        # --- RapidOCR ---
        res_rapid = read_plate(crop_path)

        # --- Tesseract ---
        res_tess = read_plate_tesseract(crop_path)

        # --- EasyOCR (optional) ---
        if args.use_easyocr:
            from app.ai.ocr_reader import read_plate_easyocr
            res_easy = read_plate_easyocr(crop_path)
        else:
            res_easy = {"plate_text": "skipped", "confidence": -1.0}

        results.append({
            "crop_filename": filename,
            "rapidocr_text": res_rapid["plate_text"],
            "rapidocr_confidence": res_rapid["confidence"],
            "tesseract_text": res_tess["plate_text"],
            "easyocr_text": res_easy["plate_text"],
            "easyocr_confidence": res_easy["confidence"],
        })

        if (i + 1) % 10 == 0 or (i + 1) == len(crops):
            elapsed = time.time() - t_start
            print(f"  Processed {i+1}/{len(crops)}  "
                  f"[{elapsed:.1f}s elapsed]  "
                  f"last: {filename} → rapid='{res_rapid['plate_text']}' tess='{res_tess['plate_text']}'")

            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    total = len(results)
    rapid_hits = sum(1 for r in results if r["rapidocr_text"] not in ("", "skipped"))
    tess_hits = sum(1 for r in results if r["tesseract_text"] not in ("", "skipped"))

    print(f"\n{'='*55}")
    print(f"  OCR COMPARISON REPORT  ({total} crops)")
    print(f"{'='*55}")
    print(f"  RapidOCR  non-empty reads : {rapid_hits:>3}  ({100*rapid_hits/total:.1f}%)")
    print(f"  Tesseract non-empty reads : {tess_hits:>3}  ({100*tess_hits/total:.1f}%)")
    if args.use_easyocr:
        easy_hits = sum(1 for r in results if r["easyocr_text"] not in ("", "skipped"))
        print(f"  EasyOCR   non-empty reads : {easy_hits:>3}  ({100*easy_hits/total:.1f}%)")
    print(f"  Results saved to: {OUTPUT_FILE}")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
