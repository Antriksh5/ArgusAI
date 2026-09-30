import cv2
import sys

def extract_frame(video_path, frame_idx, out_path):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(out_path, frame)
        print(f"Saved frame {frame_idx} to {out_path}")
    else:
        print(f"Failed to read frame {frame_idx} from {video_path}")
    cap.release()

if __name__ == "__main__":
    extract_frame("data/videos/sample.mp4", 47, "data/frames/sample_47.jpg")
    extract_frame("data/videos/bus_video.mp4", 47, "data/frames/bus_video_47.jpg")
