import os
import json
import glob
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.ai.ocr_reader import read_plate, read_plate_easyocr

def main():
    plates_dir = "data/detections/plates"
    v2_crops = glob.glob(os.path.join(plates_dir, "v2_*.jpg"))
    
    if not v2_crops:
        print(f"No v2_ crops found in {plates_dir}")
        sys.exit(1)
        
    print(f"Found {len(v2_crops)} v2 crops. Running both OCR engines...")
    
    results = []
    
    for i, crop_path in enumerate(v2_crops):
        filename = os.path.basename(crop_path)
        
        # RapidOCR
        res_rapid = read_plate(crop_path)
        
        # EasyOCR
        res_easy = read_plate_easyocr(crop_path)
        
        results.append({
            "crop_filename": filename,
            "rapidocr_text": res_rapid["plate_text"],
            "rapidocr_confidence": res_rapid["confidence"],
            "easyocr_text": res_easy["plate_text"],
            "easyocr_confidence": res_easy["confidence"]
        })
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(v2_crops)}")
            
    output_file = "data/detections/ocr_results_v2_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Comparison complete. Saved to {output_file}")

if __name__ == "__main__":
    main()
