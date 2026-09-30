import os
from ultralytics import YOLO
import cv2
import urllib.request

img_path = "pothole_test.jpg"

print("Downloading model...")
try:
    model = YOLO("hf://Samdutse/pothole-yolov8")
except Exception as e:
    print(f"hf:// failed: {e}. Downloading manually.")
    model_url = "https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt"
    urllib.request.urlretrieve(model_url, "ml/weights/pothole_model.pt")
    model = YOLO("ml/weights/pothole_model.pt")

print("Running inference...")
results = model(img_path)

res_img = results[0].plot()
cv2.imwrite("pothole_result.jpg", res_img)
print(f"Found {len(results[0].boxes)} boxes.")
