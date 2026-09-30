import os
import json
import sys

# Add backend to sys.path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.plate_detector import detect_plates

def main():
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = "data/videos/sample.mp4"
        
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found.")
        sys.exit(1)

    camera_id = "cam_bus_01"
    
    print(f"Running plate detection on {video_path}...")
    detections, plate_dir = detect_plates(video_path, camera_id)
    
    output_file = "data/detections/plates_sample_v2.json"
    with open(output_file, 'w') as f:
        json.dump(detections, f, indent=2)
        
    print(f"Detection complete. Found {len(detections)} plate detection events.")
    print(f"Results JSON saved to: {output_file}")
    print(f"Plate crops saved to: {plate_dir}/")

if __name__ == "__main__":
    main()
