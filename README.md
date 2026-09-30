Project: ArgusAI — AI-Powered Mobile Urban Intelligence Platform

This repository contains a working prototype for ArgusAI. 

## Structure
- `/backend`: FastAPI backend and AI perception pipeline
- `/frontend`: React + MapLibre GIS dashboard
- `/ml`: Model training and dataset management
- `/data`: Sample test data (videos, watchlists)

## Models & Accuracy
- **Plate Recognition:** Uses PaddleOCR models via RapidOCR
- **Hazard Detection:** Pretrained pothole YOLOv8 model (fine-tuning planned)

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

## Running the Project

To run the full ArgusAI stack locally, you need two terminal windows (one for the backend API, one for the React frontend).

### 1. Run the AI Pipeline (Optional)
If you want to re-process the videos and load new data into the database:
```bash
cd /home/antriksh/Desktop/Argus
source venv/bin/activate
python run_full_pipeline.py
```

### 2. Start the Backend API (FastAPI)
In your first terminal, start the Python server:
```bash
cd /home/antriksh/Desktop/Argus
source venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```
*The API will be available at http://localhost:8000*

### 3. Start the Frontend Dashboard (React/Vite)
In a second terminal, start the React application. (Ensure you have Node.js v20+ loaded, e.g., via NVM):
```bash
cd /home/antriksh/Desktop/Argus
source ~/.nvm/nvm.sh
cd frontend
npm run dev -- --host
```
*The dashboard will be available at http://localhost:5173*
