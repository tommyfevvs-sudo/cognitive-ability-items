import pandas as pd
import os

def calculate_difficulty(input_csv, output_csv):
    # 1. Load the dataset
    df = pd.read_csv(input_csv)
    
    # 2. Score Is_Rotated (No = 1, Yes = 2)
    if 'Is_Rotated' in df.columns:
        rotation_score = df['Is_Rotated'].map({'No': 1, 'Yes': 2}).fillna(1)
    else:
        rotation_score = 1
        
    # 3. Score Layers (Single Layer = 1, Multi-Layer = 3)
    if 'Layers' in df.columns:
        layer_score = df['Layers'].map({'Single Layer': 1, 'Multi-Layer': 3}).fillna(1)
    else:
        layer_score = 1
        
    # 4. Score Block_Count (1 point for every 2 blocks)
    if 'Block_Count' in df.columns:
        block_score = df['Block_Count'] / 2
    else:
        block_score = 0
        
    # 5. Score Is_Spinning (No = 1, Yes = 3)
    if 'Is_Spinning' in df.columns:
        spinning_score = df['Is_Spinning'].map({'No': 1, 'Yes': 3}).fillna(1)
    else:
        spinning_score = 1
        
    # 6. Score Cube_Size (3x3x3 = 1, 4x4x4 = 2)
    if 'Cube_Size' in df.columns:
        cube_score = df['Cube_Size'].map({'3x3x3': 1, '4x4x4': 2}).fillna(1)
    else:
        cube_score = 1
    
    # 7. Add them all together for the final Expected Difficulty
    df['Expected_Difficulty'] = (
        rotation_score + 
        layer_score + 
        block_score + 
        spinning_score + 
        cube_score
    )
    
    # 8. Save the new dataframe to a CSV
    df.to_csv(output_csv, index=False)
    print(f"Success! Scored data saved to:\n{output_csv}")

if __name__ == "__main__":
    # Automatically find the path to the user's Desktop
    desktop_path = os.path.expanduser("~/Desktop")
    
    # Define input and output file paths
    input_file = os.path.join(desktop_path, 'figures_metadata.csv')
    output_file = os.path.join(desktop_path, 'figures_metadata_scored.csv')
    
    # Check if the input file actually exists before trying to run
    if not os.path.exists(input_file):
        print(f"Error: Could not find the file at {input_file}")
        print("Please ensure the file is named exactly 'figures_metadata.csv' and is located on your Desktop.")
    else:
        # Run the function
        calculate_difficulty(input_file, output_file)
