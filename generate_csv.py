import json
import csv

with open('data/detections/aggregated_plates.json') as f:
    data = json.load(f)

with open('data/ground_truth.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['video', 'frame', 'true_text'])
    
    count = 0
    for item in data:
        # take up to 15 raw readings from each track to simulate frames
        for raw in item.get('all_raw_readings', [])[:30]:
            if count >= 30:
                break
            # just use the aggregated plate text as the "true" text for this mock
            # normally a human would type this
            writer.writerow(['sample.mp4', raw['frame_number'], item['final_plate_text']])
            count += 1
