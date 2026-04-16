import csv
import os

def calculate_difficulty(row):
    try:
        num_shapes = int(row.get("Num Shapes", 3))
        style = row.get("Style", "").strip().lower()
        shape_mode = row.get("Shape Mode", "").strip().lower()
        img_orient = row.get("Image Orientation", "").strip().lower()
        opt_orient = row.get("Option Orientation", "").strip().lower()
        
        # Check for animation, default to "no" if the column is missing
        animated_str = row.get("Animated", "no").strip().lower()
        is_animated = animated_str in ['yes', 'true', '1', 'y']
        
        score = 0
        
        # 1. Visual Clutter (Max +4)
        score += max(0, num_shapes - 3)
        
        # 2. Gestalt Interference (Max +3)
        if style == "outlines":
            score += 3
        # color and monochrome both add +0
            
        # 3. Target-Distractor Similarity (Max +2)
        if shape_mode != "all":
            score += 2
            
        # 4. Mental Rotation (Max +3)
        if img_orient != opt_orient:
            score += 3
        elif img_orient in ["random", "directional"]:
            score += 1
            
        # 5. Dynamic Motion Tracking (Max +1.5)
        if is_animated:
            score += 1.5
            
        # Normalize from 0-13.5 range to a 1.0 - 10.0 scale
        max_possible_score = 13.5
        normalized_score = 1 + ((score / max_possible_score) * 9)
        
        return round(normalized_score, 1)
        
    except Exception as e:
        print(f"Error processing row: {e}")
        return None

def score_csv(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Ensure 'Animated' is in the fieldnames for the output, along with the Score
        fieldnames = list(reader.fieldnames)
        if "Animated" not in fieldnames:
            fieldnames.append("Animated")
        fieldnames.append("Difficulty Score (1-10)")
        
        rows_to_write = []
        for row in reader:
            row["Difficulty Score (1-10)"] = calculate_difficulty(row)
            
            # If the column was missing from input, populate it with the default "No"
            if "Animated" not in row:
                row["Animated"] = "No"
                
            rows_to_write.append(row)

    with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)
        
    print(f"Successfully scored {len(rows_to_write)} items.")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    # Explicitly point to the Mac Desktop
    desktop_dir = os.path.expanduser("~/Desktop")
    
    input_filename = os.path.join(desktop_dir, "layering_score_input.csv")
    output_filename = os.path.join(desktop_dir, "layering_scored_output.csv")
    
    score_csv(input_filename, output_filename)