import os
import io
import base64
import random
import csv
import math
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# --- CONFIGURATION ---
# Shifted right (520) and down (500) to center the sequence in the panel
BOX_BOUNDS = {
    'input':  [500, 500, 1170, 780],  
    'output': [2440, 500, 3110, 780] 
}
batch_sets = []

def setup_environment():
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop, 'NR_number_machines')
    csv_path = os.path.join(folder_path, 'metadata.csv')
    if not os.path.exists(folder_path): os.makedirs(folder_path)
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Metadata now includes logic_type and sequence_data
            writer.writerow(['item_id', 'batch', 'tier', 'logic_type', 'rule_desc', 'num_pairs', 'inputs', 'outputs', 'target_pair', 'answer', 'sequence_data', 'difficulty_score', 'date'])
    return folder_path, csv_path

def get_next_batch_number(csv_path):
    try:
        with open(csv_path, 'r') as f:
            reader = list(csv.reader(f))
            if len(reader) <= 1: return 1
            return int(reader[-1][1]) + 1
    except: return 1

def find_font(size):
    # This is the exact path to your specific font file
    font_path = "/Users/thomasfeather/Library/Fonts/Copy of Proxima Soft.otf"
    
    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        # This will tell you exactly why it failed (e.g., file not found)
        print(f"Error loading font: {e}")
        return ImageFont.load_default() 

def calculate_difficulty(logic_type, tier, pairs):
    """Calculates a cognitive load score based on rule and visual complexity."""
    score = 0
    
    # 1. Rule Complexity
    rule_weights = {
        'simple': 1,
        'medium': 2,
        'multi_step': 4,
        'powers_pure': 5,
        'powers_offset': 6,
        'inc_multi': 7,
        'diff_pattern': 7,
        'conditional': 8
    }
    score += rule_weights.get(logic_type, 1)
    
    # 2. Visual Tier Complexity (Encoding/Search Load)
    tier_weights = {0: 0, 1: 1, 2: 3, 3: 5}
    score += tier_weights.get(tier, 0)
    
    # 3. Cognitive Load Modifiers
    
    if any(p['out'] > 99 or p['in'] > 99 for p in pairs): 
        score += 1 # 3-digit processing
    
    return score

# --- MATH ENGINE ---
def generate_math_problem():
    # Define the pool of logic types to choose from randomly
    rule_pool = ['simple'] * 6 + ['medium','powers_pure'] * 4 + ['multi_step', 'powers_offset'] * 3 + ['inc_multi', 'diff_pattern', 'conditional'] * 2
    chosen_cat = random.choice(rule_pool)
    pairs = []
    used_inputs = set()
    
    # --- PAIR COUNT LOGIC ---
    if chosen_cat == 'conditional':
        num_pairs = 5
    elif chosen_cat in ['inc_multi', 'diff_pattern']:
        num_pairs = 4
    else:
        num_pairs = random.choice([3, 4])
    
    # --- 1. POSITIONAL LOGIC TYPES (Random Inputs, Ordered Rule Application) ---
    
    if chosen_cat == 'inc_multi':
        m = random.randint(2, 3) 
        inc_start = random.randint(1, 5) 
        rule_desc = f"x{m} + inc({inc_start}) by position"
        allowed = list(range(2, 20))
        # Inputs are random, but rule applies in sequence along the diagonal positions
        for i in range(num_pairs):
            val = random.choice([x for x in allowed if x not in used_inputs])
            used_inputs.add(val)
            res = (val * m) + (inc_start + i)
            pairs.append({'in': val, 'out': res})

    elif chosen_cat == 'diff_pattern':
        step = random.randint(2, 6) 
        is_type_a = random.random() > 0.5 
        rule_desc = f"Pattern Diff {'A' if is_type_a else 'B'} by position"
        allowed = list(range(5, 50))
        # Inputs are random, but rule applies in sequence along the diagonal positions
        for i in range(num_pairs):
            val = random.choice([x for x in allowed if x not in used_inputs])
            used_inputs.add(val)
            added_val = (i + 1) * step if is_type_a else step + (i * 2)
            pairs.append({'in': val, 'out': val + added_val})

    elif chosen_cat == 'conditional':
        n1 = random.randint(1, 5)
        n2 = random.randint(1, 5)
        while n1 == n2:
            n2 = random.randint(1, 5)
        op = random.choice(['+', '-'])
        rule_desc = f"Even{op}{n1}, Odd{op}{n2}"
        
        # Force a 3/2 or 2/3 split of evens/odds
        is_even_heavy = random.random() > 0.5
        count_evens = 3 if is_even_heavy else 2
        count_odds = 2 if is_even_heavy else 3
        
        pool_evens = [x for x in range(10, 40) if x % 2 == 0]
        pool_odds = [x for x in range(10, 40) if x % 2 != 0]
        
        input_list = random.sample(pool_evens, count_evens) + random.sample(pool_odds, count_odds)
        random.shuffle(input_list)
        
        for val in input_list:
            res = (val + n1 if val % 2 == 0 else val + n2) if op == '+' else (val - n1 if val % 2 == 0 else val - n2)
            pairs.append({'in': val, 'out': res})

    # --- 2. NUMERICAL REASONING TYPES (Original Random Input Logic) ---

    elif chosen_cat == 'simple':
        n = random.randint(2, 25) 
        op = random.choice(['+', '-'])
        func = lambda x, i=0, n=n, op=op: x + n if op == '+' else x - n
        rule_desc = f"{op}{n}"
        allowed = list(range(26, 80)) if op == '-' else list(range(1, 60))
        
    elif chosen_cat == 'medium':
        n = random.randint(2, 12) 
        op = random.choice(['*', '/'])
        if op == '*': 
            func = lambda x, i=0, n=n: x * n
            rule_desc = f"x{n}"
            allowed = list(range(2, 30))
        else: 
            func = lambda x, i=0, n=n: x // n
            rule_desc = f"/{n}"
            allowed = [x * n for x in range(1, 20)]
            
    elif chosen_cat == 'powers_pure':
        if random.random() > 0.5:
            func = lambda x, i=0: x**2
            rule_desc = "Square"
            allowed = list(range(2, 16))
        else:
            func = lambda x, i=0: x**3
            rule_desc = "Cube"
            allowed = [2, 3, 4, 5, 10]

    elif chosen_cat == 'powers_offset':
        offset = random.choice([-2, -1, 1, 2])
        if random.random() > 0.5:
            func = lambda x, i=0, o=offset: (x**2) + o
            rule_desc = f"Square {'+' if offset > 0 else ''}{offset}"
            allowed = list(range(2, 16))
        else:
            func = lambda x, i=0, o=offset: (x**3) + o
            rule_desc = f"Cube {'+' if offset > 0 else ''}{offset}"
            allowed = [1, 2, 3, 4, 5, 10]
            
    elif chosen_cat == 'multi_step':
        m = random.randint(2, 5) 
        c = random.randint(1, 12) 
        op = random.choice(['+', '-'])
        if op == '+':
            func = lambda x, i=0, m=m, c=c: (x * m) + c
            rule_desc = f"x{m} + {c}"
        else:
            func = lambda x, i=0, m=m, c=c: (x * m) - c
            rule_desc = f"x{m} - {c}"
        allowed = list(range(5, 30))

    else: 
        func = lambda x, i=0: x + 1
        rule_desc = "Default+1"
        allowed = None

    # --- 3. EXECUTION AND VALIDATION (For Non-Sequence/Positional Rules) ---
    if not pairs:
        attempts = 0
        while len(pairs) < num_pairs and attempts < 1000:
            attempts += 1
            val = random.choice(allowed) if allowed else random.randint(1, 50)
            if val in used_inputs: continue

            try:
                current_idx = len(pairs) 
                res = func(val, current_idx)
                
                # Ensure output is positive, unique, and fits display bounds
                if res <= 0 or val == res or res > 999: continue
                pairs.append({'in': val, 'out': res})
                used_inputs.add(val)
            except: continue

    # Recursion safety if a valid set couldn't be found
    if len(pairs) < num_pairs: return generate_math_problem()
    
    current_set = tuple(sorted([p['in'] for p in pairs]))
    if current_set in batch_sets: return generate_math_problem()
    batch_sets.append(current_set)

    t_idx = random.randint(0, len(pairs)-1)
    t_side = 'in' if random.random() > 0.5 else 'out'
    
    return pairs, rule_desc, t_idx, t_side, chosen_cat

# --- IMPROVED POSITIONING ENGINE ---
def get_random_coords(num_items, bounds):
    """Generates high-variance random non-overlapping coordinates."""
    placed = []
    coords = []
    bw = bounds[2] - bounds[0]
    bh = bounds[3] - bounds[1]
    
    item_w, item_h = 140, 90 
    buffer = 35 # Minimum physical pixel gap between numbers
    
    for _ in range(num_items):
        success = False
        # High attempt count to ensure the space is explored randomly
        for _ in range(1000): 
            rx = random.randint(15, bw - item_w - 15)
            ry = random.randint(15, bh - item_h - 15)
            
            cand = [rx, ry, rx + item_w, ry + item_h]
            
            overlap = False
            for p in placed:
                # Check for intersection with added buffer
                if not (cand[2] + buffer < p[0] or 
                        cand[0] - buffer > p[2] or 
                        cand[3] + buffer < p[1] or 
                        cand[1] - buffer > p[3]):
                    overlap = True
                    break
            
            if not overlap:
                placed.append(cand)
                coords.append((rx, ry))
                success = True
                break
        
        if not success: return None
            
    # CRITICAL: Shuffle the coordinates so they aren't plotted 
    # in the order they were generated (which feels like a pattern)
    random.shuffle(coords)
    return coords

# --- RENDERER ---
def create_item(item_idx, batch_num, folder_path, csv_path, base64_data):
    # Base tier selection
    tier = random.choices([1, 2, 3], weights=[15, 15, 70])[0]
    
    while True:
        pairs, rule_desc, t_idx, t_side, logic_type = generate_math_problem()
        
        # Determine effective tier based on logic type
        if logic_type in ['inc_multi', 'diff_pattern']:
            # Positional rules always diagonal (Tier 0)
            effective_tier = 0
        elif logic_type == 'conditional':
            # Conditional restricted to Tier 0 or Tier 1
            effective_tier = random.choices([0, 1], weights=[30, 70])[0]
        else:
            effective_tier = tier

        try:
            base_img = Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGBA")
        except:
            return
            
        draw = ImageDraw.Draw(base_img)
        
        # DYNAMIC FONT SIZE: 80 for 5 items (Conditional), 95 for 4 items, 110 for others
        if len(pairs) >= 5:
            font_size = 80
        elif effective_tier == 0 or len(pairs) == 4:
            font_size = 95
        else:
            font_size = 110
        font = find_font(font_size)

        # 1. Setup Positions
        if effective_tier == 0:
            # DIAGONAL LAYOUT
            in_pos = []
            bw, bh = BOX_BOUNDS['input'][2] - BOX_BOUNDS['input'][0], BOX_BOUNDS['input'][3] - BOX_BOUNDS['input'][1]
            pad_x_start, pad_x_end, pad_y = 50, 70, 50
            
            # 50/50 Chance for Downward vs Upward diagonal
            is_upward = random.random() > 0.5
            
            step_x = (bw - (pad_x_start + pad_x_end)) // (len(pairs) - 1)
            step_y = (bh - (2 * pad_y)) // (len(pairs) - 1)
            
            for i in range(len(pairs)):
                curr_x = pad_x_start + (i * step_x)
                # If upward, start from the bottom (bh - pad_y) and move up
                if is_upward:
                    curr_y = (bh - pad_y) - (i * step_y)
                else:
                    curr_y = pad_y + (i * step_y)
                in_pos.append((curr_x, curr_y))
                
            out_pos, out_indices = in_pos, list(range(len(pairs)))
        else:
            # Standard Positioning logic
            in_pos = get_random_coords(len(pairs), BOX_BOUNDS['input'])
            if in_pos is None: continue
            
            if effective_tier == 1:
                out_pos, out_indices = in_pos, list(range(len(pairs)))
            elif effective_tier == 2:
                out_pos = get_random_coords(len(pairs), BOX_BOUNDS['output'])
                out_indices = list(range(len(pairs))) 
            else: # Tier 3
                out_pos = get_random_coords(len(pairs), BOX_BOUNDS['output'])
                out_indices = list(range(len(pairs)))
                random.shuffle(out_indices)

        if out_pos is None: continue

        # Render Inputs
        for i in range(len(pairs)):
            txt = "?" if (i == t_idx and t_side == 'in') else str(pairs[i]['in'])
            draw.text((BOX_BOUNDS['input'][0] + in_pos[i][0], BOX_BOUNDS['input'][1] + in_pos[i][1]), 
                      txt, fill=(30,30,30), font=font)

        # Render Outputs
        for i in range(len(pairs)):
            idx = out_indices[i]
            txt = "?" if (idx == t_idx and t_side == 'out') else str(pairs[idx]['out'])
            draw.text((BOX_BOUNDS['output'][0] + out_pos[i][0], BOX_BOUNDS['output'][1] + out_pos[i][1]), 
                      txt, fill=(30,30,30), font=font)

        # Calculate Cognitive Difficulty
        diff_score = calculate_difficulty(logic_type, effective_tier, pairs)

        # Item saving logic...
        item_id = f"item_{batch_num}.{str(item_idx).zfill(3)}_nm"
        base_img.save(os.path.join(folder_path, f"{item_id}.png"), "PNG")
        with open(csv_path, 'a', newline='') as f:
            seq_sum = " -> ".join([str(p['out']) for p in pairs])
            csv.writer(f).writerow([item_id, batch_num, effective_tier, logic_type, rule_desc, len(pairs), [p['in'] for p in pairs], [p['out'] for p in pairs], f"{t_side}_{t_idx}", pairs[t_idx][t_side], seq_sum, diff_score, datetime.now().strftime("%Y-%m-%d %H:%M")])
        break

def main():
    folder, csv_p = setup_environment()
    batch = get_next_batch_number(csv_p)
    string_file = os.path.join(os.path.expanduser('~'), 'Desktop', 'NR_NM_template.txt')
    
    if not os.path.exists(string_file): 
        print(f"Error: {string_file} not found on Desktop.")
        return
        
    with open(string_file, 'r') as f: 
        base64_data = f.read().strip()

    # Prompt user for quantity
    try:
        count_input = input("How many puzzles would you like to generate? ")
        count = int(count_input) if count_input.strip() else 20
    except ValueError:
        print("Invalid input. Generating 20 puzzles by default.")
        count = 20

    print(f"Generating Batch {batch} ({count} Items)...")
    for i in range(1, count + 1):
        create_item(i, batch, folder, csv_p, base64_data)
        print(f" - Saved {i}/{count}")

if __name__ == "__main__":
    main()