import json
import sys

def main():
    json_path = "data/detections/ocr_results_v2_comparison.json"
    try:
        with open(json_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"{json_path} not found")
        sys.exit(1)
        
    total_crops = len(data)
    rapidocr_non_empty = 0
    easyocr_non_empty = 0
    
    for item in data:
        if item.get("rapidocr_text", "") != "":
            rapidocr_non_empty += 1
        if item.get("easyocr_text", "") != "":
            easyocr_non_empty += 1
            
    print(f"Total crops: {total_crops}")
    print(f"RapidOCR non-empty reads: {rapidocr_non_empty} ({(rapidocr_non_empty/total_crops)*100 if total_crops else 0:.1f}%)")
    print(f"EasyOCR non-empty reads: {easyocr_non_empty} ({(easyocr_non_empty/total_crops)*100 if total_crops else 0:.1f}%)")
    
if __name__ == "__main__":
    main()
