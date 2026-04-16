import os, random, csv, glob, subprocess, math, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- MASTER DIRECTORY SETUP ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NR_Master_Repository")
CSV_PATH = os.path.join(OUTPUT_FOLDER, "NR_metadata_Master.csv")

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FONT_DIR = next((d for d in [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
] if os.path.exists(d)), "")
FINAL_CANVAS_WIDTH = 3000 

def get_next_batch_number():
    if not os.path.exists(CSV_PATH): return 1
    try:
        with open(CSV_PATH, 'r', newline='') as f:
            reader = csv.DictReader(f)
            nums = [int(re.search(r"item_(\d+)\.", r['Filename']).group(1)) for r in reader if re.search(r"item_(\d+)\.", r['Filename'])]
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
    # Swapped X for blue heart and updated font to support emoji rendering
    try:
        heart_font = ImageFont.truetype("seguiemj.ttf", 110) 
    except:
        heart_font = get_best_font(130, bold=True)
        
    s_val = "\U0001f499" # Blue Heart Emoji
    bbox = draw.textbbox((0, 0), s_val, font=heart_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_x = px + (cell_size - tw) / 2 - bbox[0]
    draw_y = py + (cell_size - th) / 2 - bbox[1]
    draw.text((draw_x, draw_y), s_val, fill="black", font=heart_font, embedded_color=True)

class SequenceEngine:
    @staticmethod
    def generate(stype, target_val, target_idx, length):
        val_cap = 400 
        for attempt in range(3000):
            seq, desc = [], ""
            if stype == "linear":
                d = random.choice([-12, -7, -5, -3, -2, 2, 3, 4, 5, 7, 11, 13])
                seq = [target_val - (target_idx - i) * d for i in range(length)]
                desc = f"Lin|{d}"
            elif stype == "step_change":
                inc = random.randint(1, 4)
                base_d = random.randint(1, 5)
                temp = [0] * length; temp[target_idx] = target_val
                cd = base_d + (target_idx * inc)
                for i in range(target_idx + 1, length): temp[i] = temp[i-1] + cd; cd += inc
                cd = base_d + (target_idx - 1) * inc
                for i in range(target_idx - 1, -1, -1): temp[i] = temp[i+1] - cd; cd -= inc
                seq, desc = temp, f"Step|{inc}"
            elif stype == "geometric":
                r = random.choice([0.5, 2, 1.5, 3])
                start = target_val / (r**target_idx)
                seq = [int(start * (r**i)) if (start * (r**i)) % 1 == 0 else -1 for i in range(length)]
                desc = f"Geo|{r}"
            elif stype == "fibonacci":
                s = [random.randint(1, 8), random.randint(1, 8)]
                for i in range(12): s.append(s[-1]+s[-2])
                if target_val in s:
                    idx = s.index(target_val)
                    if idx >= target_idx and idx-target_idx+length <= len(s): 
                        seq, desc = s[idx-target_idx:idx-target_idx+length], "Fib|None"
            elif stype == "squares" or stype == "triangular":
                s = [n**2 for n in range(1, 20)] if stype == "squares" else [n*(n+1)//2 for n in range(1, 25)]
                if target_val in s:
                    idx = s.index(target_val)
                    if idx >= target_idx and idx-target_idx+length <= len(s): 
                        seq, desc = s[idx-target_idx:idx-target_idx+length], f"{stype[:3]}|None"
            
            if len(seq) == length and all(0 <= x <= val_cap and x != -1 for x in seq):
                if seq[target_idx] == target_val: return seq, desc
        return None, "None|None"

class ItemGenerator:
    def __init__(self, batch, item_n):
        self.batch, self.item_n = batch, item_n
        self.grid, self.blanks = {}, []

    def build(self):
        pool = ["linear", "geometric", "step_change", "fibonacci", "squares", "triangular"]
        anchor_val = random.randint(2, 30)
        
        h_type, h_len = random.choice(pool), random.randint(5, 6)
        h_idx = random.randint(1, h_len-2)
        h_seq, h_log = SequenceEngine.generate(h_type, anchor_val, h_idx, h_len)
        if not h_seq: return False
        
        v_type, v_len = random.choice(pool), random.randint(5, 6)
        v_idx = random.randint(1, v_len-2)
        v_seq, v_log = SequenceEngine.generate(v_type, anchor_val, v_idx, v_len)
        if not v_seq or v_log == h_log: return False

        self.grid = {}
        h_coords = [(i - h_idx, 0) for i in range(h_len)]
        v_coords = [(0, i - v_idx) for i in range(v_len)]
        for i, v in enumerate(h_seq): self.grid[h_coords[i]] = v
        for i, v in enumerate(v_seq): self.grid[v_coords[i]] = v

        target_axis = random.choice([0, 1])
        t_coords = h_coords if target_axis == 0 else v_coords
        clue_coords = v_coords if target_axis == 0 else h_coords
        
        self.target_pos = random.choice([c for c in t_coords if c != (0,0)])
        self.answer = self.grid[self.target_pos]

        t3_log = "None|None"
        if random.random() > 0.4:
            t3_y_idx = v_idx - 2 if v_idx >= 2 else v_idx + 2
            t3_anchor = v_seq[t3_y_idx]
            t3_type = random.choice(pool)
            t3_seq, t3_log = SequenceEngine.generate(t3_type, t3_anchor, 0, 4)
            if t3_seq:
                for i, v in enumerate(t3_seq): self.grid[(i, t3_y_idx - v_idx)] = v
                self.blanks.append((0, t3_y_idx - v_idx))

        self.blanks.append((0, 0)) 
        
        clue_p = [c for c in clue_coords if c != (0,0) and c != self.target_pos and c not in self.blanks]
        if len(clue_p) >= 3:
            self.blanks.extend(random.sample(clue_p, len(clue_p) - 3))
        else: return False

        t_p = [c for c in t_coords if c != (0,0) and c != self.target_pos and c not in self.blanks]
        if len(t_p) >= 2:
            self.blanks.extend(random.sample(t_p, len(t_p) - 2))
        else: return False

        self.fn = f"NR_item_{self.batch}.{self.item_n:03d}.png"
        self.meta = [self.fn, self.answer, h_log, v_log, t3_log, len(self.blanks), datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        return True

    def render(self):
        cell, lw = 220, 4
        xs, ys = [k[0] for k in self.grid.keys()], [k[1] for k in self.grid.keys()]
        mx, my, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
        gw, gh = (max_x - mx + 1) * cell, (max_y - my + 1) * cell
        img_t = Image.new("RGB", (gw + lw, gh + lw), "white"); draw = ImageDraw.Draw(img_t)
        font = get_best_font(100); line_color = (80, 80, 80)
        
        h_lines = set(); v_lines = set()
        for (x, y) in self.grid.keys():
            px, py = (x - mx) * cell, (y - my) * cell
            h_lines.add((px, px + cell, py)); h_lines.add((px, px + cell, py + cell))
            v_lines.add((py, py + cell, px)); v_lines.add((py, py + cell, px + cell))
        for x1, x2, y in h_lines: draw.line([(x1, y), (x2, y)], fill=line_color, width=lw)
        for y1, y2, x in v_lines: draw.line([(x, y1), (x, y2)], fill=line_color, width=lw)
        
        for (x, y), val in self.grid.items():
            px, py = (x - mx) * cell, (y - my) * cell
            if (x, y) == self.target_pos:
                draw_x_target(draw, px, py, cell)
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
    qty = int(input(f"Qty (default 20): ") or 20)
    res, total_saved = [], 0
    
    while total_saved < qty:
        it = ItemGenerator(bn, total_saved + 1)
        if it.build() and it.render():
            res.append(it.meta)
            total_saved += 1
            print(f"Saved {it.fn} ({total_saved}/{qty})")
    
    if res:
        file_exists = os.path.exists(CSV_PATH) and os.stat(CSV_PATH).st_size > 0
        with open(CSV_PATH, 'a', newline='') as f:
            wr = csv.writer(f)
            if not file_exists:
                wr.writerow(["Filename", "Answer", "Seq_H", "Seq_V", "Seq_T3", "BlanksCount", "Timestamp"])
            wr.writerows(res)
            
    subprocess.Popen(f'explorer "{OUTPUT_FOLDER}"')

if __name__ == "__main__": main()