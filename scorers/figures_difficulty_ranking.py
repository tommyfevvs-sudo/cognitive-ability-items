import pandas as pd
import numpy as np
import os

def rank_nvr_figures(csv_path):
    """
    Ranks generated figure matrix items into 9 difficulty groups 
    based on calibrated IRT weights.
    """
    if not os.path.exists(csv_path):
        print(f"Error: Could not find the file at {csv_path}")
        return
    
    # Load the metadata
    df = pd.read_csv(csv_path)

    # --- CALIBRATED WEIGHTS ---
    W_BLOCKS = 0.35      # Per block added
    W_ROTATION = 0.85    # Penalty for mental rotation
    W_LAYERS = 0.45      # Complexity of 3D depth
    W_GRID = 0.30        # Added difficulty for 4x4x4 vs 3x3x3

    # --- 1. FEATURE CONVERSION ---
    # Map 'Yes'/'No' to numbers
    df['rot_val'] = df['Is_Rotated'].map({'Yes': 1, 'No': 0})
    
    # Map Layers (Handles Single, Multi, or Triple)
    layer_map = {'Single Layer': 1, 'Multi-Layer': 2, 'Triple Layer': 3}
    df['layer_val'] = df['Layers'].map(layer_map).fillna(1)
    
    # Handle Grid_Size (Default to 0 jump if column is missing)
    if 'Grid_Size' in df.columns:
        df['grid_val'] = df['Grid_Size'] - 3
    else:
        df['grid_val'] = 0

    # --- 2. CALCULATE RAW DIFFICULTY (predicted_b) ---
    df['predicted_b'] = (
        (df['Block_Count'] * W_BLOCKS) + 
        (df['rot_val'] * W_ROTATION) + 
        (df['layer_val'] * W_LAYERS) +
        (df['grid_val'] * W_GRID)
    )

    # --- 3. STANDARDIZATION ---
    # Centers the scores so the Mean is 0 and Standard Deviation is 1
    # This makes them comparable to IRT 'b' parameters.
    if len(df) > 1:
        df['predicted_b'] = (df['predicted_b'] - df['predicted_b'].mean()) / df['predicted_b'].std()

    # --- 4. CREATE 9 GROUPS (STANINES) ---
    # We use rank(method='first') to resolve ties and ensure 
    # exactly equal numbers of items in each of the 9 groups.
    df['temp_rank'] = df['predicted_b'].rank(method='first')
    df['Difficulty_Group'] = pd.qcut(df['temp_rank'], 9, labels=range(1, 10))

    # --- 5. CLEANUP & SAVE ---
    # Drop temp columns and sort by difficulty
    df = df.drop(columns=['temp_rank', 'rot_val', 'layer_val', 'grid_val'])
    df = df.sort_values('predicted_b').reset_index(drop=True)
    
    # Generate output name: e.g., metadata_Ranked.csv
    output_filename = csv_path.replace('.csv', '_Ranked.csv')
    df.to_csv(output_filename, index=False)
    
    print("-" * 45)
    print(f"RANKING SUCCESSFUL")
    print(f"Total Items: {len(df)}")
    print(f"Items per Group: {len(df)//9}")
    print(f"Output File: {output_filename}")
    print("-" * 45)
    
    # Preview top and bottom items
    print("\nEasiest Items (Group 1):")
    print(df[['Item_Name', 'predicted_b']].head(3))
    print("\nHardest Items (Group 9):")
    print(df[['Item_Name', 'predicted_b']].tail(3))

# --- EXECUTION ---
if __name__ == "__main__":
    # Path to your metadata file
    user_path = "/Users/thomasfeather/Unnamed_Assessment_Item_Creation/figures_1_metadata.csv"
    
    rank_nvr_figures(user_path)
