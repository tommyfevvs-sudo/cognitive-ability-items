import pandas as pd
import numpy as np
import re
import os

def score_logic(seq_val):
    """Assigns points based on sequence logic complexity."""
    if pd.isna(seq_val) or seq_val == 'None|None' or str(seq_val).strip() == '':
        return 0
        
    val = str(seq_val).strip()
    
    # Basic Linear (1 pt)
    if val in ['Lin|2', 'Lin|5', 'Lin|10', 'Lin|-2', 'Lin|-5', 'Lin|-10']:
        return 1
    # Intermediate Linear (2 pts)
    elif val in ['Lin|3', 'Lin|-3', 'Lin|4', 'Lin|-4', 'Lin|20', 'Lin|25', 'Lin|-25', 'Lin|50', 'Lin|-50', 'Lin|30', 'Lin|40']:
        return 2
    # Basic Geometric (5 pts)
    elif val in ['Geo|2', 'Geo|5', 'Geo|10']:
        return 5
    # Recognizable Non-linear (6 pts)
    elif val in ['squ|None', 'tri|None']:
        return 6
    # Complex Geo/Cubes (8 pts)
    elif val in ['Geo|0.5', 'Geo|1.5', 'Geo|3', 'cub|None']:
        return 8
    # Advanced (10 pts)
    elif val in ['Step|1', 'Step|2', 'Step|3', 'Step|4', 'Fib|None']:
        return 10
    # Complex Linear (Catch-all for other 'Lin|' values like 6, 7, 8, 9, 11 etc.)
    elif val.startswith('Lin|'):
        return 4
    else:
        # Default fallback for unrecognized logic
        return 2

def score_blanks(blanks_val):
    """Assigns points based on the number of blanks."""
    if pd.isna(blanks_val):
        return 0
    
    # Extract the first number found in the string
    match = re.search(r'\d+', str(blanks_val))
    if match:
        blanks = int(match.group())
        scores = {1: 1, 2: 2, 3: 3, 4: 5, 5: 7, 6: 9}
        return scores.get(blanks, 9) # Default to 9 if more than 6 blanks
    return 0

def score_congruency(cong_val):
    """Assigns points based on congruency."""
    if pd.isna(cong_val):
        return 0
    val = str(cong_val).strip().lower()
    if val == 'same':
        return 0
    elif val == 'different':
        return 2
    return 0

def score_highest_value(high_val):
    """Assigns points based on the highest number in the grid."""
    if pd.isna(high_val):
        return 0
    val = str(high_val).strip()
    if val == '0-25': return 0.5
    if val == '26-50': return 1
    if val == '50-100': return 1.5
    if val == '100+': return 2
    return 0

def score_longest_sequence(length_val):
    """Assigns points based on longest sequence length."""
    if pd.isna(length_val):
        return 0
    val = str(length_val).strip().lower()
    if '4' in val: return 0.5
    if '5' in val: return 1
    if '6' in val: return 1.5
    return 0

def score_sequence_count(count_val):
    """Assigns 1 point per sequence present in the grid."""
    if pd.isna(count_val):
        return 0
    try:
        return int(count_val)
    except ValueError:
        return 0

def score_max_consecutive_avg(avg_val):
    """
    Assigns points based on the average of consecutive numbers.
    Lower average = higher difficulty (more points).
    """
    if pd.isna(avg_val):
        return 0
    
    try:
        val = float(avg_val)
    except ValueError:
        return 0
        
    # Point matrix: Less average = more points
    if val < 1.2:
        return 5
    elif val < 1.5:
        return 4
    elif val < 2.0:
        return 3
    elif val < 2.5:
        return 1
    else:
        return 0

def assign_difficulty_tier(score):
    """Maps the total numerical score to a readable difficulty tier."""
    if score <= 10: return 'Beginner / Easy'
    elif score <= 16: return 'Intermediate / Moderate'
    elif score <= 23: return 'Advanced / Hard'
    else: return 'Expert / Extreme'

def main():
    # Dynamically find the path to the user's Desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    input_file = os.path.join(desktop_path, "crosswords_data.csv")
    output_file = os.path.join(desktop_path, "crosswords_data_scored.csv")
    
    print(f"Loading data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find '{input_file}'.")
        print("Please ensure the file is named exactly 'crosswords_data.csv' and is saved on your Desktop.")
        return

    # Ensure all expected columns exist, fill missing ones with NaN to avoid KeyError
    expected_columns = ['Seq_H', 'Seq_V', 'Seq_T3', 'Blanks', 'Congruency', 
                        'Sequence Count', 'Highest Value', 'Longest Sequence Length',
                        'max_consecutive_average']
    for col in expected_columns:
        if col not in df.columns:
            df[col] = np.nan

    print("Calculating scores...")
    
    # Calculate individual scores
    df['Score_Seq_H'] = df['Seq_H'].apply(score_logic)
    df['Score_Seq_V'] = df['Seq_V'].apply(score_logic)
    df['Score_Seq_T3'] = df['Seq_T3'].apply(score_logic)
    df['Score_Blanks'] = df['Blanks'].apply(score_blanks)
    df['Score_Congruency'] = df['Congruency'].apply(score_congruency)
    df['Score_Highest_Value'] = df['Highest Value'].apply(score_highest_value)
    df['Score_Longest_Seq'] = df['Longest Sequence Length'].apply(score_longest_sequence)
    df['Score_Sequence_Count'] = df['Sequence Count'].apply(score_sequence_count)
    df['Score_Max_Consec_Avg'] = df['max_consecutive_average'].apply(score_max_consecutive_avg)

    # Calculate Total Score (Added the new metric as an additive difficulty)
    df['Total Score'] = (df['Score_Seq_H'] + 
                         df['Score_Seq_V'] + 
                         df['Score_Seq_T3'] + 
                         df['Score_Blanks'] + 
                         df['Score_Congruency'] + 
                         df['Score_Highest_Value'] + 
                         df['Score_Longest_Seq'] +
                         df['Score_Sequence_Count'] +
                         df['Score_Max_Consec_Avg'])

    # Map to categorical tier
    df['Estimated Difficulty'] = df['Total Score'].apply(assign_difficulty_tier)

    # Optional: Drop the intermediate score columns to keep the output clean
    columns_to_drop = ['Score_Seq_H', 'Score_Seq_V', 'Score_Seq_T3', 'Score_Blanks', 
                       'Score_Congruency', 'Score_Highest_Value', 'Score_Longest_Seq', 
                       'Score_Sequence_Count', 'Score_Max_Consec_Avg']
    df_clean = df.drop(columns=columns_to_drop)

    # Save to a new CSV on the Desktop
    df_clean.to_csv(output_file, index=False)
    print(f"Scoring complete! Output saved to: \n{output_file}")

if __name__ == "__main__":
    main()