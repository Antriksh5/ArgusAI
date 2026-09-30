"""
run_ocr_on_crops.py
-------------------
Batch OCR runner for plate crops.

Usage:
    python backend/scripts/run_ocr_on_crops.py --crops-dir <path> [--output-json <path>]

Loops over every image in crops_dir, runs read_plate() on each, and writes
all results to output_json as a JSON array.

Each entry in the output array:
    {
        "crop_filename": str,
        "camera_id":     str,    # parsed from filename  (e.g. "cam_bus_01")
        "frame_number":  int,    # parsed from filename  (e.g. 194)
        "plate_text":    str,    # cleaned OCR text (empty string if none)
        "confidence":    float   # average OCR confidence (0.0 if none)
    }
"""

import os
import sys
import json
import re
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.ai.ocr_reader import read_plate

# Expected pattern: <camera_id>_<frame_number>_<det_index>.jpg
_FILENAME_RE = re.compile(r"^(.+?)_(\d+)_(\d+)\.(jpg|png|jpeg)$", re.IGNORECASE)

def parse_filename(filename: str) -> tuple[str, int]:
    m = _FILENAME_RE.match(filename)
    if m:
        return m.group(1), int(m.group(2))
    return "unknown", -1

def main():
    parser = argparse.ArgumentParser(description="Run OCR on a directory of crops")
    parser.add_argument("--crops-dir", required=True, help="Directory containing plate crop images")
    parser.add_argument("--output-json", default="data/detections/ocr_results.json", help="Output JSON file path")
    args = parser.parse_args()

    crops_dir = args.crops_dir
    output_json = args.output_json

    if not os.path.isdir(crops_dir):
        print(f"Error: Crops directory '{crops_dir}' does not exist.")
        sys.exit(1)

    supported_exts = {".jpg", ".jpeg", ".png"}
    image_files = sorted(
        f for f in os.listdir(crops_dir)
        if os.path.splitext(f)[1].lower() in supported_exts
    )

    if not image_files:
        print(f"[OCR] No images found in {crops_dir}. Exiting.")
        return

    print(f"[OCR] Processing {len(image_files)} crops in '{crops_dir}'...")

    results = []
    non_empty = 0
    confidences_all = []

    for idx, fname in enumerate(image_files, 1):
        image_path = os.path.join(crops_dir, fname)
        camera_id, frame_number = parse_filename(fname)

        ocr_out = read_plate(image_path)

        entry = {
            "crop_filename": fname,
            "camera_id":     camera_id,
            "frame_number":  frame_number,
            "plate_text":    ocr_out["plate_text"],
            "confidence":    ocr_out["confidence"],
        }
        results.append(entry)

        if ocr_out["plate_text"]:
            non_empty += 1
        if ocr_out["confidence"] > 0:
            confidences_all.append(ocr_out["confidence"])

        if idx % 10 == 0 or idx == len(image_files):
            print(f"  [{idx}/{len(image_files)}] last: {fname} → "
                  f"'{ocr_out['plate_text']}' (conf={ocr_out['confidence']:.3f})")

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    total = len(results)
    conf_min  = round(min(confidences_all), 4) if confidences_all else 0.0
    conf_max  = round(max(confidences_all), 4) if confidences_all else 0.0
    conf_avg  = round(sum(confidences_all) / len(confidences_all), 4) if confidences_all else 0.0

    print("\n" + "=" * 60)
    print("  OCR BATCH REPORT")
    print("=" * 60)
    print(f"  Total crops processed :  {total}")
    print(f"  Non-empty plate_text  :  {non_empty}  ({100*non_empty/total:.1f}%)")
    print(f"  Confidence distribution:")
    print(f"    min  = {conf_min}\n    max  = {conf_max}\n    avg  = {conf_avg}\n")

    print(f"  Full results written to: {output_json}")
    print("=" * 60)

if __name__ == "__main__":
    main()
