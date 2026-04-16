import os, random, csv, glob, subprocess, math, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- MASTER DIRECTORY SETUP ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NR_crosswords_Upper_KS2_V2")
CSV_PATH = os.path.join(OUTPUT_FOLDER, "NR_crosswords_metadata.csv")

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
            nums = [int(re.search(r"_B(\d+)_", r['Filename']).group(1)) for r in reader if "_B" in r['Filename']]
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
    try: heart_font = ImageFont.truetype("seguiemj.ttf", 110) 
    except: heart_font = get_best_font(130, bold=True)
    s_val = "\U0001f499" # Blue Heart
    bbox = draw.textbbox((0, 0), s_val, font=heart_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((px + (cell_size - tw) / 2 - bbox[0], py + (cell_size - th) / 2 - bbox[1]), s_val, fill="black", font=heart_font, embedded_color=True)

class SequenceEngine:
    @staticmethod
    def generate(rule_id, target_val=None, target_idx=None, length=5):
        for _ in range(2000):
            seq, desc = [], ""
            if rule_id == "GEO2":
                start = random.randint(1, 9); seq = [start * (2**i) for i in range(length)]
                if any(v > 200 for v in seq): continue
                desc = "Geo|Double|Start<10"
            elif rule_id == "GEO0.5":
                start = random.choice([x for x in range(2, 101, 2)]); seq = [int(start * (0.5**i)) for i in range(length)]
                if any((start * (0.5**i)) % 1 != 0 or (start * (0.5**i)) < 1 for i in range(length)): continue
                desc = "Geo|Halve|EvenStart"
            elif rule_id == "LIN_BIG_MULT":
                step = random.choice([20, 30, 40]); start = random.randint(1, 10) * 10
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|Start10s"
            elif rule_id == "LIN_BIG_ANY":
                step = random.choice([20, 30, 40]); start = random.randint(1, 100)
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|AnyStart"
            elif rule_id == "LIN_OFF_2_5_10":
                step = random.choice([2, 5, 10]); start = random.choice([x for x in range(1, 100) if x % step != 0])
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|OffGrid"
            elif rule_id == "LIN_OFF_3_4_8":
                step = random.choice([3, 4, 8]); start = random.choice([x for x in range(1, 100) if x % step != 0])
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|OffGrid"
            elif rule_id == "LIN_OFF_6_12":
                step = random.choice([6, 7, 9, 11, 12]); start = random.choice([x for x in range(1, 100) if x % step != 0])
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|OffGrid"
            elif rule_id == "LIN_OFF_25_50":
                step = random.choice([25, 50]); start = random.choice([x for x in range(1, 100) if x % step != 0])
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|OffGrid"
            elif rule_id == "LIN_12_19":
                step = random.randint(12, 19); start = random.randint(1, 100)
                dir = random.choice([1, -1]); seq = [start + (i * step * dir) for i in range(length)]
                desc = f"Lin|{step}|Y6"
            elif rule_id == "CUBE":
                roots = list(range(1, 6)); s_idx = random.randint(0, len(roots)-length) if len(roots) >= length else 0
                seq = [roots[i+s_idx]**3 for i in range(min(length, len(roots)))]
                if random.random() > 0.5: seq.reverse()
                desc = "Cub|1-5th"
            elif rule_id == "SQUARE":
                roots = list(range(2, 13)); s_idx = random.randint(0, len(roots)-length) if len(roots) >= length else 0
                seq = [roots[i+s_idx]**2 for i in range(min(length, len(roots)))]
                seq = [v for v in seq if v <= 144]
                if len(seq) < length: continue
                if random.random() > 0.5: seq.reverse()
                desc = "Squ|2-12th"

            if target_val is not None:
                if any(x in desc for x in ["Geo", "Cub", "Squ"]):
                    if target_val not in seq: continue
                    if seq.index(target_val) != target_idx: continue 
                else:
                    diff = target_val - seq[target_idx]
                    seq = [x + diff for x in seq]

            if any(val < 1 or val > 500 for val in seq): continue
            if len(seq) < length: continue
            return seq, desc
        return None, None

class ItemGenerator:
    def __init__(self, batch, item_n, level):
        self.batch, self.item_n, self.level = batch, item_n, level
        self.grid, self.blanks, self.target_pos = {}, [], (0,0)
        self.h_log, self.v_log, self.answer, self.diff_label = "", "", 0, ""

    def build(self):
        pool_A = ["GEO2", "GEO0.5", "LIN_BIG_MULT", "LIN_BIG_ANY"]
        pool_B = ["LIN_OFF_2_5_10", "LIN_OFF_3_4_8", "LIN_OFF_6_12", "LIN_OFF_25_50"]
        pool_C = ["LIN_12_19", "CUBE", "SQUARE"]

        if 1 <= self.level <= 3: 
            r1, r2 = random.choice(pool_A), random.choice(pool_B)
            self.diff_label = "Diff5_Lvl1-3"
        elif 4 <= self.level <= 6: 
            r1, r2 = random.sample(pool_A, 2)
            self.diff_label = "Diff5_Lvl4-6"
        elif 7 <= self.level <= 9: 
            r1, r2 = random.choice(pool_C), random.choice(pool_B)
            self.diff_label = "Diff6_Lvl7-9"
        else: 
            r1, r2 = random.choice(pool_C), random.choice(pool_A)
            self.diff_label = "Diff6_Lvl10-11"

        for _ in range(50):
            primary_is_h = random.choice([True, False])
            p_len, t_len = random.randint(4, 6), random.randint(4, 6)
            p_inter, t_inter = random.randint(0, p_len-1), random.randint(0, t_len-1)

            p_seq, p_desc = SequenceEngine.generate(r1, length=p_len)
            if not p_seq: continue
            t_seq, t_desc = SequenceEngine.generate(r2, target_val=p_seq[p_inter], target_idx=t_inter, length=t_len)
            if not t_seq or p_desc == t_desc: continue 

            self.grid = {}
            if primary_is_h:
                for i, val in enumerate(p_seq): self.grid[(i - p_inter, 0)] = val
                for i, val in enumerate(t_seq): self.grid[(0, i - t_inter)] = val
                self.h_log, self.v_log = p_desc, t_desc
                p_c = [(i - p_inter, 0) for i in range(p_len) if (i - p_inter, 0) != (0,0)]
                t_c = [(0, i - t_inter) for i in range(t_len) if (0, i - t_inter) != (0,0)]
            else:
                for i, val in enumerate(p_seq): self.grid[(0, i - p_inter)] = val
                for i, val in enumerate(t_seq): self.grid[(i - t_inter, 0)] = val
                self.v_log, self.h_log = p_desc, t_desc
                p_c = [(0, i - p_inter) for i in range(p_len) if (0, i - p_inter) != (0,0)]
                t_c = [(i - t_inter, 0) for i in range(t_len) if (i - t_inter, 0) != (0,0)]

            self.target_pos = random.choice(t_c)
            self.answer = self.grid[self.target_pos]
            p_c.sort(key=lambda x: x[0] if primary_is_h else x[1])
            visible = p_c[random.randint(0, len(p_c)-3) :][:3]
            t_c_clean = [c for c in t_c if c != self.target_pos]
            t_c_clean.sort(key=lambda x: x[1] if primary_is_h else x[0])
            visible.extend(t_c_clean[random.randint(0, len(t_c_clean)-2) :][:2])
            self.blanks = [c for c in self.grid.keys() if c not in visible]
            return True
        return False

    def render(self):
        cell, lw = 220, 4
        xs, ys = [k[0] for k in self.grid.keys()], [k[1] for k in self.grid.keys()]
        min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
        gw, gh = (max_x - min_x + 1) * cell, (max_y - min_y + 1) * cell
        img_temp = Image.new("RGB", (gw + lw, gh + lw), "white")
        draw = ImageDraw.Draw(img_temp)
        font_main = get_best_font(100)
        for (x, y) in self.grid.keys():
            px, py = (x - min_x) * cell, (y - min_y) * cell
            draw.rectangle([px, py, px+cell, py+cell], outline=(80,80,80), width=lw)
        for (x, y), val in self.grid.items():
            px, py = (x - min_x) * cell, (y - min_y) * cell
            if (x, y) == self.target_pos: draw_x_target(draw, px, py, cell)
            elif (x, y) not in self.blanks:
                txt = str(val); bbox = draw.textbbox((0, 0), txt, font=font_main)
                draw.text((px + (cell-(bbox[2]-bbox[0]))/2 - bbox[0], py + (cell-(bbox[3]-bbox[1]))/2 - bbox[1]), txt, fill="black", font=font_main)
        fn = f"NR_UKS2_B{self.batch}_Lvl{self.level}_{self.item_n:03d}.png"
        img_final = Image.new("RGB", (FINAL_CANVAS_WIDTH, max(gh + 200, 1000)), "white")
        img_final.paste(img_temp, ((FINAL_CANVAS_WIDTH - gw)//2, 100))
        img_final.save(os.path.join(OUTPUT_FOLDER, fn))
        self.fn = fn
        return True

def main():
    batch_num = get_next_batch_number()
    print(f"--- UKS2 Reasoning Builder (Batch {batch_num}) ---")
    lvl_in = input("Level (1-11 or 'all'): ").strip().lower()
    qty = int(input("Quantity per level? (default 5): ") or 5)
    lvls = range(1, 12) if lvl_in == 'all' else [int(lvl_in)]
    meta = []
    for l in lvls:
        c = 0
        while c < qty:
            item = ItemGenerator(batch_num, c + 1, l)
            if item.build() and item.render():
                meta.append([item.fn, item.answer, item.v_log, item.h_log, item.level, item.diff_label])
                c += 1; print(f"Saved Lvl {l}: {item.fn}")
    with open(CSV_PATH, 'a', newline='') as f:
        wr = csv.writer(f); wr.writerow(["Filename", "Answer", "V_Log", "H_Log", "Level", "Difficulty"]) if f.tell() == 0 else None
        wr.writerows(meta)
    subprocess.Popen(f'explorer "{OUTPUT_FOLDER}"')

if __name__ == "__main__":
    main()