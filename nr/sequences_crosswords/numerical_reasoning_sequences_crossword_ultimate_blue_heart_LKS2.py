import os, random, csv, glob, subprocess, math, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- MASTER DIRECTORY SETUP ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NR_crosswords_lower_KS2")
CSV_PATH = os.path.join(OUTPUT_FOLDER, "NR_crosswords_lower_KS2.csv")

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FONT_DIR = next((d for d in [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
] if os.path.exists(d)), "")
FINAL_CANVAS_WIDTH = 3000 

STEP_DECKS = {}
DIR_DECKS = {}

def get_next_batch_number():
    if not os.path.exists(CSV_PATH): return 1
    try:
        with open(CSV_PATH, 'r', newline='') as f:
            reader = csv.DictReader(f)
            # This looks for the number between the second underscore and the period
            nums = [int(re.search(r"_(\d+)\.", r['Filename']).group(1)) for r in reader if re.search(r"_(\d+)\.", r['Filename'])]
            return max(nums) + 1 if nums else 1
    except: return 1

def get_best_font(size, bold=False):
    font_dirs = [
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts",
        "/System/Library/Fonts",
    ]
    weight = "Bold" if bold else ""
    search_pattern = f"*[Pp]roxima*[Ss]oft*{weight}*.[ot]tf"
    for font_dir in font_dirs:
        files = glob.glob(os.path.join(font_dir, "**", search_pattern), recursive=True)
        if not bold:
            files = [f for f in files if not any(x in os.path.basename(f).lower()
                     for x in ['bold', 'italic', 'semibold', 'light', 'black'])]
        if files:
            try: return ImageFont.truetype(files[0], size)
            except: pass
    return ImageFont.load_default()

def draw_x_target(draw, px, py, cell_size):
    try:
        heart_font = ImageFont.truetype("seguiemj.ttf", 110) 
    except:
        heart_font = get_best_font(130, bold=True)
        
    s_val = "\U0001f499" 
    bbox = draw.textbbox((0, 0), s_val, font=heart_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_x = px + (cell_size - tw) / 2 - bbox[0]
    draw_y = py + (cell_size - th) / 2 - bbox[1]
    draw.text((draw_x, draw_y), s_val, fill="black", font=heart_font, embedded_color=True)
class SequenceEngine:
    @staticmethod
    def get_params(level, is_primary):
        # returns: (steps_list, mode, force_up_only)
        # mode 0: multiples within tables (1-12x)
        # mode 1: multiples outside tables (>12x)
        # mode 2: start < 5x step
        # mode 3: start < 100
        
        if level == 1: return [2, 5, 10], 0, True
        if level == 2: return [2, 5, 10], 1, True
        if level == 3: return [2, 5, 10], 2, True
        if level == 4: return [2, 5, 10], 3, True
        if level == 5:
            return ([3, 4, 8], 0, True) if is_primary else ([2, 5, 10], 0, True)
        if level == 6:
            return ([3, 4, 8], 1, True) if is_primary else ([2, 5, 10], 0, True)
        if level == 7: return [3, 4, 8], 0, True
        if level == 8: return [3, 4, 8], 3, True
        if level == 9: return list(range(2, 13)), 0, True
        if level == 10: return list(range(2, 13)), 3, True
        if level == 11:
            return ([25, 50], 0, True) if is_primary else (list(range(2, 13)), 3, True)
        
        return [2], 0, False

    @staticmethod
    def generate(level, target_val, target_idx, length, is_primary, prev_step=None, prev_dir=None):
        steps_list, mode, force_up = SequenceEngine.get_params(level, is_primary)
        
        # --- DIRECTION VARIETY ADJUSTMENT ---
        # Instead of strictly forcing Up, we allow Down 50% of the time even if force_up is True
        if force_up:
            directions = [1, -1] if random.random() < 0.5 else [1]
        else:
            directions = [1, -1]
        
        configs = []
        for s in steps_list:
            for d in directions:
                configs.append((s, d))
        
        random.shuffle(configs)

        # --- VARIETY FIX ---
        # If we are generating the second sequence (prev_step is known), 
        # we filter out the previous step to force a different mathematical logic.
        if prev_step is not None:
            filtered = [c for c in configs if c[0] != prev_step]
            if filtered: # Only use filtered if it doesn't leave us with zero options
                configs = filtered
        # -------------------

        for d_base, direction in configs:
            d = d_base * direction
            
            for attempt in range(500):
                if mode == 0:
                    # Widened range (1 to 20) to ensure different steps can actually "hit" the target_val
                    start_mult = random.randint(1, 20 - length) if direction == 1 else random.randint(length, 20)
                    start = start_mult * d_base
                elif mode == 1:
                    # Multiples but outside 12x tables (starts at 13x and up)
                    # We cap it at 30x to keep numbers reasonable (< 300)
                    start_mult = random.randint(13, 30)
                    start = start_mult * d_base
                    if direction == -1: start += (length * d_base)
                elif mode == 2:
                    # Start < 5x step
                    start = random.randint(1, (5 * d_base) - 1)
                    if direction == -1: start += (length * d_base)
                else: 
                    # Start < 100
                    start = random.randint(1, 99)
                    if direction == -1 and start < (length * d_base): start += (length * d_base)
                
                seq = [start + (i * d) for i in range(length)]
                
                # If this sequence must pass through a specific intersection value
                if target_val is not None:
                    # Calculate exactly where the sequence must start to hit the target_val
                    start = target_val - (target_idx * d)
                    seq = [start + (i * d) for i in range(length)]
                
                # --- Validation Checks ---
                if any(x < 1 for x in seq): continue
                
                if mode == 0:
                    # Rule L1, L5, L7, L9: Must be multiples AND within 12x table limit
                    if any(x % d_base != 0 for x in seq): continue
                    if any(x > 12 * d_base for x in seq): continue
                
                if mode == 1:
                    # Rule L2, L6: Must be multiples but strictly "outside" the standard table
                    if any(x % d_base != 0 for x in seq): continue
                
                if mode == 2:
                    # Rule L3: Lowest number must be less than 5x step
                    if min(seq) >= (5 * d_base): continue

                if any(x > 1000 for x in seq): continue # Safety cap
                
                dir_str = "Asc" if direction == 1 else "Desc"
                return seq, d_base, direction, f"Lvl{level}|Step{d_base}|{dir_str}"
        
        return None, None, None, "None"

class ItemGenerator:
    def __init__(self, batch, item_n, level):
        self.batch, self.item_n = batch, item_n
        self.level = level
        self.grid, self.blanks = {}, []

    def build(self):
        # Updated randint range to include 4
        h_len, v_len = random.randint(4, 6), random.randint(4, 6)
        h_idx, v_idx = random.randint(1, h_len-2), random.randint(1, v_len-2)
        
        # Generate H seq (Primary)
        h_seq, h_step, h_dir, h_log = SequenceEngine.generate(self.level, None, h_idx, h_len, True)
        if not h_seq: return False
        
        # Generate V seq (Target) - Pass H parameters to force variety
        v_seq, v_step, v_dir, v_log = SequenceEngine.generate(self.level, h_seq[h_idx], v_idx, v_len, False, prev_step=h_step, prev_dir=h_dir)
        if not v_seq: return False

        self.grid = {}
        h_coords = [(i - h_idx, 0) for i in range(h_len)]
        v_coords = [(0, i - v_idx) for i in range(v_len)]
        for i, v in enumerate(h_seq): self.grid[h_coords[i]] = v
        for i, v in enumerate(v_seq): self.grid[v_coords[i]] = v

        self.target_pos = random.choice([c for c in v_coords if c != (0,0)])
        self.answer = self.grid[self.target_pos]

        h_windows = [h_coords[i:i+3] for i in range(len(h_coords)-2) if (0,0) not in h_coords[i:i+3]]
        if not h_windows: return False
        visible_clues = list(random.choice(h_windows))
        
        if random.random() < 0.3:
            rem_h = [c for c in h_coords if c not in visible_clues and c != (0,0)]
            if rem_h: visible_clues.append(random.choice(rem_h))

        v_pool = [c for c in v_coords if c != (0,0) and c != self.target_pos]
        if len(v_pool) < 2: return False
        visible_clues.extend(random.sample(v_pool, 2))

        self.blanks = [(0,0), self.target_pos]
        for coord in self.grid.keys():
            if coord not in visible_clues and coord not in self.blanks:
                self.blanks.append(coord)

        self.fn = f"NR_Lvl{self.level}_{self.batch}.{self.item_n:03d}.png"
        self.meta = [self.fn, self.answer, h_log, v_log, self.level, len(self.blanks), datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        return True

    def render(self):
        cell, lw = 220, 4
        xs, ys = [k[0] for k in self.grid.keys()], [k[1] for k in self.grid.keys()]
        mx, my, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
        gw, gh = (max_x - mx + 1) * cell, (max_y - my + 1) * cell
        img_t = Image.new("RGB", (gw + lw, gh + lw), "white"); draw = ImageDraw.Draw(img_t)
        font = get_best_font(100); line_color = (80, 80, 80)
        
        h_lines, v_lines = set(), set()
        for (x, y) in self.grid.keys():
            px, py = (x - mx) * cell, (y - my) * cell
            h_lines.add((px, px + cell, py)); h_lines.add((px, px + cell, py + cell))
            v_lines.add((py, py + cell, px)); v_lines.add((py, py + cell, px + cell))
        for x1, x2, y in h_lines: draw.line([(x1, y), (x2, y)], fill=line_color, width=lw)
        for y1, y2, x in v_lines: draw.line([(x, y1), (x, y2)], fill=line_color, width=lw)
        
        for (x, y), val in self.grid.items():
            px, py = (x - mx) * cell, (y - my) * cell
            if (x, y) == self.target_pos: draw_x_target(draw, px, py, cell)
            elif (x, y) not in self.blanks:
                s = str(val); bbox = draw.textbbox((0, 0), s, font=font)
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                tx, ty = px + (cell - w) / 2 - bbox[0], py + (cell - h) / 2 - bbox[1] - (lw // 2)
                draw.text((tx, ty), s, fill="black", font=font)

        img_f = Image.new("RGB", (FINAL_CANVAS_WIDTH, gh + lw), "white")
        img_f.paste(img_t, ((FINAL_CANVAS_WIDTH - gw)//2, 0))
        img_f.save(os.path.join(OUTPUT_FOLDER, self.fn)); return True

def main():
    bn = get_next_batch_number(); print(f"Batch: {bn}")
    lvl_in = input("Difficulty Level (1-11 or 'random'): ").strip().lower()
    try: qty = int(input("Qty: ") or 20)
    except: qty = 20
        
    items = []
    while len(items) < qty:
        cur_lvl = random.randint(1, 11) if lvl_in == 'random' else (int(lvl_in) if lvl_in.isdigit() else 1)
        it = ItemGenerator(bn, 0, cur_lvl) 
        if it.build():
            items.append(it)
            print(f"Prepared {len(items)}/{qty} (Level {cur_lvl})")

    items.sort(key=lambda x: x.level)
    res_meta = []
    for i, it in enumerate(items):
        it.item_n = i + 1
        it.fn = f"NR_Lvl{it.level}_{it.batch}.{it.item_n:03d}.png"
        it.meta[0] = it.fn
        if it.render():
            res_meta.append(it.meta)
            print(f"Saved {it.fn}")

    if res_meta:
        file_exists = os.path.exists(CSV_PATH) and os.stat(CSV_PATH).st_size > 0
        with open(CSV_PATH, 'a', newline='') as f:
            wr = csv.writer(f)
            if not file_exists:
                wr.writerow(["Filename", "Answer", "Seq_H", "Seq_V", "Difficulty", "BlanksCount", "Timestamp"])
            wr.writerows(res_meta)
    subprocess.Popen(f'explorer "{OUTPUT_FOLDER}"')

if __name__ == "__main__":
    main()