import cv2
import pytesseract
import os
import re
import csv

# Tell Tesseract exactly where its dictionary data is stored
os.environ['TESSDATA_PREFIX'] = '/Users/thomasfeather/miniconda3/share/tessdata/'
pytesseract.pytesseract.tesseract_cmd = r'/Users/thomasfeather/miniconda3/bin/tesseract'

def extract_consecutive_metrics(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h)
        
        if 0.8 <= aspect_ratio <= 1.2 and 30 < w < gray.shape[1] * 0.5 and 30 < h < gray.shape[0] * 0.5: 
            if not any(abs(x - bx) < 10 and abs(y - by) < 10 for bx, by, bw, bh in boxes):
                boxes.append((x, y, w, h))
                
    if not boxes:
        return [], []

    box_data = []
    for (x, y, w, h) in boxes:
        # Extract the original colored box, not just the grayscale one
        roi_color = img[y+5:y+h-5, x+5:x+w-5]
        roi_gray = gray[y+5:y+h-5, x+5:x+w-5]
        
        # 1. Check for Color (Saturation)
        # Convert to HSV to easily look at color intensity
        hsv = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        
        # Count how many pixels are highly colorful (saturation > 50)
        _, sat_thresh = cv2.threshold(saturation, 50, 255, cv2.THRESH_BINARY)
        color_pixel_count = cv2.countNonZero(sat_thresh)
        total_pixels = roi_color.shape[0] * roi_color.shape[1]
        
        # If more than 5% of the box has bright color, it's an emoji/symbol
        if color_pixel_count > (total_pixels * 0.05):
            is_number = False
        else:
            # 2. If it's just black and white, pass it to Tesseract
            text = pytesseract.image_to_string(roi_gray, config='--psm 8').strip()
            is_number = bool(re.match(r'^\d+$', text))
            
        box_data.append({"x": x, "y": y, "is_number": is_number})

    tolerance = 15 
    rows = {}
    cols = {}
    
    for box in box_data:
        matched_row = next((r for r in rows if abs(r - box['y']) < tolerance), None)
        if matched_row is not None:
            rows[matched_row].append(box)
        else:
            rows[box['y']] = [box]
            
        matched_col = next((c for c in cols if abs(c - box['x']) < tolerance), None)
        if matched_col is not None:
            cols[matched_col].append(box)
        else:
            cols[box['x']] = [box]

    for r in rows:
        rows[r] = sorted(rows[r], key=lambda b: b['x'])
    for c in cols:
        cols[c] = sorted(cols[c], key=lambda b: b['y'])

    def get_max_consecutive(sequence):
        max_streak = 0
        current_streak = 0
        for item in sequence:
            if item['is_number']:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0 
        return max_streak

    h_streaks = [get_max_consecutive(rows[r]) for r in rows if len(rows[r]) > 1]
    v_streaks = [get_max_consecutive(cols[c]) for c in cols if len(cols[c]) > 1]

    return h_streaks, v_streaks

# --- Processing the folder and saving to CSV ---
folder_path = "/Users/thomasfeather/Desktop/sequences_crosswords_collated" 
output_csv = "/Users/thomasfeather/Desktop/sequence_metrics.csv"

with open(output_csv, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Filename", "Horizontal", "Vertical", "Third"])

    for filename in os.listdir(folder_path):
        if filename.endswith(".png"):
            full_path = os.path.join(folder_path, filename)
            
            h_streaks, v_streaks = extract_consecutive_metrics(full_path)
            
            horiz_val = h_streaks[0] if len(h_streaks) > 0 else 0
            vert_val = v_streaks[0] if len(v_streaks) > 0 else 0
            
            third_val = 0
            if len(h_streaks) > 1:
                third_val = h_streaks[1]
            elif len(v_streaks) > 1:
                third_val = v_streaks[1]
                
            writer.writerow([filename, horiz_val, vert_val, third_val])
            print(f"Processed: {filename}")

print(f"All done! Results saved to {output_csv}")