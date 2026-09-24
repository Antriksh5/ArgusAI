import os
import json
import sys

# Add backend to sys.path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.vehicle_detector import detect_vehicles

def main():
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = "data/videos/bus_video.mp4"
        
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found.")
        sys.exit(1)

    camera_id = "cam_bus_01"
    
    print(f"Running vehicle detection on {video_path}...")
    detections = detect_vehicles(video_path, camera_id)
    
    output_file = "data/detections/vehicles_sample.json"
    with open(output_file, 'w') as f:
        json.dump(detections, f, indent=2)
        
    print(f"Detection complete. Found {len(detections)} vehicle detection events across all frames.")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
