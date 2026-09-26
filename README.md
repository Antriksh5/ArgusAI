Project: ArgusAI — AI-Powered Mobile Urban Intelligence Platform

This repository contains a working prototype for ArgusAI. 

## Structure
- `/backend`: FastAPI backend and AI perception pipeline
- `/frontend`: React + MapLibre GIS dashboard
- `/ml`: Model training and dataset management
- `/data`: Sample test data (videos, watchlists)

## Getting Started
To test the AI perception pipeline locally, you can run the provided scripts in the `backend/scripts` folder. Make sure you have the required dependencies installed (e.g., using a virtual environment and `requirements.txt`).
**1. Run License Plate Detection**
Extracts license plates from the sample video and saves the cropped images.
```bash
python backend/scripts/run_plate_detection.py
```
*(Optionally provide a path to a specific video as an argument)*
**2. Run OCR engines**
Compares RapidOCR and EasyOCR performance on the extracted license plates.
```bash
python backend/scripts/run_ocr_v2_comparison.py
```
## Output & Checking Work
The scripts process video and image data, outputting results primarily into the `data/detections/` directory:
- **Cropped Images:** The plate detection script saves individual image crops of detected license plates in `data/detections/plates/`.
- **JSON Results:** Detection and OCR results are saved as JSON files for easy inspection. For example:
  - `data/detections/plates_sample_v2.json` contains detection metadata.
  - `data/detections/ocr_results_v2_comparison.json` contains side-by-side OCR confidence scores and text.
You can view these JSON files to verify if the detection and text recognition pipelines are working correctly.
