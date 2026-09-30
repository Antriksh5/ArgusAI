import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.plate_aggregator import aggregate_plate_reads
import json

def main():
    video_path = "data/videos/sample.mp4"
    camera_id = "cam_bus_01"

    aggregated_results, all_track_ids = aggregate_plate_reads(video_path, camera_id)

    print("\n" + "="*60)
    print("EVALUATION REPORT")
    print("="*60)
    
    print(f"Out of {len(all_track_ids)} distinct vehicle tracks found, "
          f"{len(aggregated_results)} had at least one non-empty plate reading.")

    print("\nChecking for tracks with 3+ readings that disagree:")
    found_disagreements = False
    
    for res in aggregated_results:
        readings = res["all_raw_readings"]
        if len(readings) >= 3:
            texts = [r["plate_text"] for r in readings]
            unique_texts = set(texts)
            if len(unique_texts) > 1:
                found_disagreements = True
                print(f"\n[Track ID {res['track_id']}] has {len(readings)} readings that disagree:")
                print(f"  Final selected text: '{res['final_plate_text']}' (conf={res['final_confidence']:.4f})")
                for r in readings:
                    selected = (r["plate_text"] == res["final_plate_text"] and 
                                round(r["confidence"], 4) == res["final_confidence"])
                    marker = " <== SELECTED" if selected else ""
                    print(f"  - Frame {r['frame_number']:3d}: '{r['plate_text']:15s}' (conf={r['confidence']:.4f}){marker}")
                    
    if not found_disagreements:
        print("No tracks found with 3+ readings that disagreed!")
        
if __name__ == "__main__":
    main()
