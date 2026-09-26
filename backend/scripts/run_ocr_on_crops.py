"""
run_ocr_on_crops.py
-------------------
Batch OCR runner for plate crops.

Usage:
    python backend/scripts/run_ocr_on_crops.py [crops_dir] [output_json]

Defaults:
    crops_dir   = data/detections/plates/
    output_json = data/detections/ocr_results.json

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

# Allow running from project root or from the scripts/ dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.ocr_reader import read_plate

# ─── filename parsing ──────────────────────────────────────────────────────────
# Expected pattern: <camera_id>_<frame_number>_<det_index>.jpg
# e.g.  cam_bus_01_194_0.jpg  →  camera_id="cam_bus_01", frame=194
_FILENAME_RE = re.compile(r"^(.+?)_(\d+)_(\d+)\.(jpg|png|jpeg)$", re.IGNORECASE)


def parse_filename(filename: str) -> tuple[str, int]:
    """Return (camera_id, frame_number) parsed from crop filename, or ('unknown', -1)."""
    m = _FILENAME_RE.match(filename)
    if m:
        return m.group(1), int(m.group(2))
    return "unknown", -1


def main(crops_dir: str = "data/detections/plates",
         output_json: str = "data/detections/ocr_results.json") -> None:

    # ── gather image files ─────────────────────────────────────────────────────
    supported_exts = {".jpg", ".jpeg", ".png"}
    image_files = sorted(
        f for f in os.listdir(crops_dir)
        if os.path.splitext(f)[1].lower() in supported_exts
    )

    if not image_files:
        print(f"[OCR] No images found in {crops_dir}. Exiting.")
        return

    print(f"[OCR] Processing {len(image_files)} crops in '{crops_dir}'...")

    # ── run OCR ───────────────────────────────────────────────────────────────
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

        # Progress tick every 10 crops
        if idx % 10 == 0 or idx == len(image_files):
            print(f"  [{idx}/{len(image_files)}] last: {fname} → "
                  f"'{ocr_out['plate_text']}' (conf={ocr_out['confidence']:.3f})")

    # ── write JSON ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    # ── stats report ─────────────────────────────────────────────────────────
    total = len(results)
    conf_min  = round(min(confidences_all), 4) if confidences_all else 0.0
    conf_max  = round(max(confidences_all), 4) if confidences_all else 0.0
    conf_avg  = round(sum(confidences_all) / len(confidences_all), 4) if confidences_all else 0.0

    print()
    print("=" * 60)
    print("  OCR BATCH REPORT")
    print("=" * 60)
    print(f"  Total crops processed :  {total}")
    print(f"  Non-empty plate_text  :  {non_empty}  ({100*non_empty/total:.1f}%)")
    print(f"  Confidence distribution:")
    print(f"    min  = {conf_min}")
    print(f"    max  = {conf_max}")
    print(f"    avg  = {conf_avg}")
    print()

    print("  5 example results:")
    print(f"  {'Filename':<35} {'plate_text':<20} {'conf':>6}")
    print("  " + "-" * 65)
    # Pick 5 entries that have non-empty text first, then pad with empties
    non_empty_entries = [r for r in results if r["plate_text"]]
    sample = non_empty_entries[:5]
    if len(sample) < 5:
        sample += [r for r in results if not r["plate_text"]][:5 - len(sample)]
    for r in sample:
        print(f"  {r['crop_filename']:<35} {r['plate_text']:<20} {r['confidence']:>6.3f}")

    print()
    print(f"  Full results written to: {output_json}")
    print("=" * 60)


if __name__ == "__main__":
    crops_dir   = sys.argv[1] if len(sys.argv) > 1 else "data/detections/plates"
    output_json = sys.argv[2] if len(sys.argv) > 2 else "data/detections/ocr_results.json"
    main(crops_dir, output_json)
