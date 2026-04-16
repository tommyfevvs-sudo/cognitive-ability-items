import random
import os
import math
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

# --- Configuration ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_Easy_Tiled_Production")

MAC_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental"
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

class NVREasyGenerator:
    def __init__(self):
        # I. FEATURE DECKS
        self.all_shapes = ['circle', 'square', 'pentagon', 'triangle', 'hexagon', 'arrow', 'star', 'cross_shape']
        self.rotatable_shapes = ['triangle', 'arrow', 'pentagon', 'star']
        
        self.shading_categories = {
            'arrows': ['up', 'down', 'left', 'right'],
            'lines': ['vertical', 'diagonal_tl_br', 'diagonal_tr_bl'],
            'grids': ['standard_large', 'standard_small', 'tilted_diamond'],
            'wavy': ['wavy_v', 'wavy_h', 'wavy_d'],
            'mini_tri': ['tri_up', 'tri_down', 'tri_left', 'tri_right'],
            'tiling': ['brickwork', 'basketweave', 'hexagonal_honeycomb']
        }
        
        self.outlines = [1.5, 2.5, 4.0]
        self.sf = 4 
        self.cell_size_hd = 200 * self.sf
        self.spacing_hd = 35 * self.sf
        self.strip_w_hd = (self.cell_size_hd * 4) + (self.spacing_hd * 3) + (150 * self.sf)
        self.strip_h_hd = self.cell_size_hd + (400 * self.sf) 
        self.small_r_hd = 22 * self.sf  
        self.large_r_hd = 65 * self.sf  

        # II. FONT LOADER (Strict Regular Targeting)
        self.font_hd = None
        font_found = False
        
        print("Searching for Proxima Soft Regular...")
        for d in MAC_FONT_DIRS:
            if not os.path.exists(d): continue
            
            for f in os.listdir(d):
                l_f = f.lower()
                
                # 1. Must contain 'proxima' and 'soft'
                if "proxima" in l_f and "soft" in l_f:
                    
                    # 2. STRICT NEGATIVE FILTER:
                    # We exclude 'it' (italic), 'light', 'bold', 'semibold', 'medium'
                    # and check common abbreviations like 'lt' or 'bi'
                    forbidden = ['italic', ' it.', ' it ', 'light', ' lt', 'bold', 'semibold', 'medium', ' thin']
                    if any(bad in l_f for bad in forbidden):
                        continue
                        
                    # 3. Double check for the 'it' suffix in filenames like 'ProximaSoft-It.otf'
                    if l_f.endswith('it.otf') or l_f.endswith('it.ttf'):
                        continue

                    try:
                        font_path = os.path.join(d, f)
                        self.font_hd = ImageFont.truetype(font_path, 32 * self.sf)
                        print(f"SUCCESS: Loaded Proxima Soft Regular: {f}")
                        font_found = True
                        break
                    except: continue
            if font_found: break

        if not font_found:
            print("Proxima Soft Regular not found. Fallback to Arial.")
            try: self.font_hd = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 32 * self.sf)
            except: self.font_hd = ImageFont.load_default()

    def get_shape_coords_hd(self, shape_type, cx, cy, r, rotation=0):
        pts = []
        if shape_type == 'circle': return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == 'square':
            adj = r * 0.85
            pts = [(cx - adj, cy - adj), (cx + adj, cy - adj), (cx + adj, cy + adj), (cx - adj, cy + adj)]
        elif shape_type == 'triangle':
            h = r * 1.7 * 0.85
            offset = h / 6 
            pts = [(cx, cy - (h * 2/3) + offset), (cx + r, cy + (h * 1/3) + offset), (cx - r, cy + (h * 1/3) + offset)]
        elif shape_type == 'arrow':
            pts = [(cx, cy - r), (cx + r*0.8, cy), (cx, cy + r), (cx - r*0.8, cy)]
        elif shape_type == 'star':
            for i in range(10):
                ang = math.radians(-90 + i * 36); curr_r = r if i % 2 == 0 else r * 0.45
                pts.append((cx + curr_r * math.cos(ang), cy + curr_r * math.sin(ang)))
        elif shape_type == 'cross_shape':
            w = r * 0.35
            pts = [(cx-w, cy-r), (cx+w, cy-r), (cx+w, cy-w), (cx+r, cy-w), (cx+r, cy+w), (cx+w, cy+w), (cx+w, cy+r), (cx-w, cy+r), (cx-w, cy+w), (cx-r, cy+w), (cx-r, cy-w), (cx-w, cy-w)]
        elif shape_type == 'pentagon':
            for ang in [-90, -18, 54, 126, 198]: pts.append((cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))))
        elif shape_type == 'hexagon':
            for i in range(6): pts.append((cx + r * math.cos(math.radians(-90 + i*60)), cy + r * math.sin(math.radians(-90 + i*60))))
        
        if rotation != 0 and shape_type != 'circle':
            rad = math.radians(float(rotation))
            rotated_pts = []
            for px, py in pts:
                nx = cx + (px - cx) * math.cos(rad) - (py - cy) * math.sin(rad)
                ny = cy + (px - cx) * math.sin(rad) + (py - cy) * math.cos(rad)
                rotated_pts.append((nx, ny))
            return rotated_pts
        return pts

    def draw_pattern_hd(self, draw, fill_data, size):
        sf = self.sf
        category, variant = fill_data
        
        if category == 'tiling':
            if variant == 'brickwork':
                bw, bh = 24*sf, 12*sf
                for y in range(0, size + bh, bh):
                    offset = (bw // 2) if (y // bh) % 2 == 0 else 0
                    draw.line([(0, y), (size, y)], fill="black", width=1*sf)
                    for x in range(-bw, size + bw, bw):
                        draw.line([(x + offset, y), (x + offset, y + bh)], fill="black", width=1*sf)
            elif variant == 'basketweave':
                bs = 20 * sf
                for x in range(0, size, bs):
                    for y in range(0, size, bs):
                        if (x // bs + y // bs) % 2 == 0:
                            for i in range(2, bs, 6*sf):
                                draw.line([(x + 2*sf, y + i), (x + bs - 2*sf, y + i)], fill="black", width=1*sf)
                        else:
                            for i in range(2, bs, 6*sf):
                                draw.line([(x + i, y + 2*sf), (x + i, y + bs - 2*sf)], fill="black", width=1*sf)
                        draw.rectangle([x, y, x + bs, y + bs], outline="black", width=1*sf)
            elif variant == 'hexagonal_honeycomb':
                h_r = 10*sf
                h_w = math.sqrt(3) * h_r
                h_h = 2 * h_r
                for row in range(-1, (size // int(h_h * 0.75)) + 2):
                    for col in range(-1, (size // int(h_w)) + 2):
                        cx = col * h_w + (h_w/2 if row % 2 else 0)
                        cy = row * h_h * 0.75
                        pts = []
                        for i in range(6):
                            ang = math.radians(30 + i * 60)
                            pts.append((cx + h_r * math.cos(ang), cy + h_r * math.sin(ang)))
                        draw.polygon(pts, outline="black", fill=None, width=1*sf)
        elif category == 'arrows':
            for ax in range(0, size, 26*sf):
                for ay in range(0, size, 26*sf):
                    if variant == 'up': h, s, l, r_h = (ax, ay-6*sf), (ax, ay+6*sf), (ax-4*sf, ay-2*sf), (ax+4*sf, ay-2*sf)
                    elif variant == 'down': h, s, l, r_h = (ax, ay+6*sf), (ax, ay-6*sf), (ax-4*sf, ay+2*sf), (ax+4*sf, ay+2*sf)
                    elif variant == 'left': h, s, l, r_h = (ax-6*sf, ay), (ax+6*sf, ay), (ax-2*sf, ay-4*sf), (ax-2*sf, ay+4*sf)
                    else: h, s, l, r_h = (ax+6*sf, ay), (ax-6*sf, ay), (ax+2*sf, ay-4*sf), (ax+2*sf, ay+4*sf)
                    draw.line([s, h], fill="black", width=2*sf); draw.line([l, h], fill="black", width=2*sf); draw.line([r_h, h], fill="black", width=2*sf)
        elif category == 'wavy':
            for i in range(-size, size*2, 15*sf):
                pts = []
                for j in range(0, size+10, 4*sf):
                    off = math.sin(j*0.05)*(5*sf)
                    if variant == 'wavy_v': pts.append((i+off, j))
                    elif variant == 'wavy_h': pts.append((j, i+off))
                    else: pts.append((i+j+off, j))
                if len(pts) > 1: draw.line(pts, fill="black", width=1*sf)
        elif category == 'mini_tri':
            ts, gp = 6*sf, 22*sf
            for tx in range(0, size, gp):
                for ty in range(0, size, gp):
                    if variant == 'tri_up': tri = [(tx, ty-ts), (tx+ts, ty+ts), (tx-ts, ty+ts)]
                    elif variant == 'tri_down': tri = [(tx, ty+ts), (tx+ts, ty-ts), (tx-ts, ty-ts)]
                    elif variant == 'tri_left': tri = [(tx-ts, ty), (tx+ts, ty-ts), (tx+ts, ty+ts)]
                    else: tri = [(tx+ts, ty), (tx-ts, ty-ts), (tx-ts, ty+ts)]
                    draw.polygon(tri, fill="black")
        elif category == 'lines':
            for li in range(-size, size*2, 14*sf):
                if variant == 'vertical': draw.line([(li, 0), (li, size)], fill="black", width=1*sf)
                elif variant == 'diagonal_tl_br': draw.line([(li, 0), (li+size, size)], fill="black", width=1*sf)
                else: draw.line([(li, 0), (li-size, size)], fill="black", width=1*sf)
        elif category == 'grids':
            if variant == 'tilted_diamond':
                gs = 16*sf
                for gi in range(-size, size*2, gs):
                    draw.line([(gi, 0), (gi-size, size)], fill="black", width=1*sf)
                    draw.line([(gi-size, 0), (gi, size)], fill="black", width=1*sf)
            else:
                gs = 22*sf if 'large' in variant else 10*sf
                for gx in range(0, size+10*sf, gs): draw.line([(gx, 0), (gx, size)], fill="black", width=1*sf)
                for gy in range(0, size+10*sf, gs): draw.line([(0, gy), (size, gy)], fill="black", width=1*sf)

    def _draw_masked_obj(self, canvas, shape, pattern, cx, cy, r, rotation=0, outline_w=2.5):
        size = int(r * 3.0) 
        buf = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        mask = Image.new('L', (size, size), 0)
        self.draw_pattern_hd(ImageDraw.Draw(buf), pattern, size)
        loc_pts = self.get_shape_coords_hd(shape, size // 2, size // 2, r, rotation)
        glob_pts = self.get_shape_coords_hd(shape, cx, cy, r, rotation)
        draw = ImageDraw.Draw(canvas)
        weight_hd = int(outline_w * self.sf)

        if shape == 'circle':
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight_hd)
        else:
            closed_glob = glob_pts + [glob_pts[0], glob_pts[1]]
            draw.line(closed_glob, fill="black", width=weight_hd * 2, joint="curve")
            draw.polygon(glob_pts, fill="black")
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)

    def get_full_pool(self, var_name, forced_shape=None):
        if 'sh' in var_name: 
            return [forced_shape] if forced_shape else self.all_shapes
        
        if 'or' in var_name:
            # Determine which row we are looking at to find the shape
            row_prefix = var_name[:2]
            # We need to know the shape to decide the valid rotations
            # This looks at the fixed_vals or the forced_shape logic
            target_shape = forced_shape
            
            # Rotation Logic based on Shape Geometry
            if target_shape in ['triangle', 'arrow']:
                # 8-point compass for highly directional shapes
                return [0, 45, 90, 135, 180, 225, 270, 315]
            elif target_shape in ['pentagon', 'star']:
                # Standard cardinal rotations for 5-pointed shapes
                return [0, 90, 180, 270]
            else:
                # Fallback for other shapes
                return [0, 90, 180, 270]
                
        if 'ol' in var_name: return self.outlines
        if 'pt' in var_name:
            pool = []
            for c, vs in self.shading_categories.items():
                if 'r1' in var_name and c in ['arrows', 'mini_tri']: continue
                for v in vs: pool.append((c, v))
            return pool
        return []

    def generate_puzzle_set(self, set_id):
        all_vars = ['r1_sh', 'r1_pt', 'r1_or', 'r1_ol', 'r2_sh', 'r2_pt', 'r2_or', 'r2_ol']
        v1_name, v2_name = random.sample(all_vars, 2)
        
        f1_shape = random.choice(self.rotatable_shapes) if 'or' in v1_name else None
        f2_shape = random.choice(self.rotatable_shapes) if 'or' in v2_name else None

        p1 = self.get_full_pool(v1_name, f1_shape)
        p2 = self.get_full_pool(v2_name, f2_shape)
        
        val_pool_1 = random.sample(p1, 2)
        val_pool_2 = random.sample(p2, 2)
        
        mapping = {
            'A': val_pool_1[0], 'B': val_pool_1[1],
            'X': val_pool_2[0], 'Y': val_pool_2[1]
        }

        # --- FIX 1: Update Mapping string to show the forced shape context ---
        mapping_str = f"A={mapping['A']}; B={mapping['B']}; X={mapping['X']}; Y={mapping['Y']}"
        if f1_shape: mapping_str += f" (V1 Shape Forced: {f1_shape})"
        if f2_shape: mapping_str += f" (V2 Shape Forced: {f2_shape})"

        s1 = random.choice(['A', 'B'])
        s2 = random.choice(['X', 'Y'])
        
        clue_codes = list(set([s1 + 'X', s1 + 'Y', 'A' + s2, 'B' + s2]))
        while len(clue_codes) < 4:
            extra = random.choice(['A','B']) + random.choice(['X','Y'])
            if extra not in clue_codes: clue_codes.append(extra)
        
        random.shuffle(clue_codes)
        target_code = random.choice(['AX', 'AY', 'BX', 'BY'])

        # Nested function stays mostly the same, but ensure it uses the outer scope variables
        def make_state_with_protection(code_str, existing_data):
            attempts = 0
            while attempts < 1000:
                state = {}
                # PRE-FILL Forced Shapes to ensure they don't get randomized later
                if 'or' in v1_name: state[f"{v1_name[:2]}_sh"] = f1_shape
                if 'or' in v2_name: state[f"{v2_name[:2]}_sh"] = f2_shape

                for v in all_vars:
                    if v == v1_name:
                        state[v] = mapping[code_str[0]]
                    elif v == v2_name:
                        state[v] = mapping[code_str[1]]
                    else:
                        if v not in state:
                            state[v] = random.choice(self.get_full_pool(v))
                
                collision = False
                for other_code, other_state in existing_data:
                    shared_letters = sum(1 for i in range(2) if code_str[i] == other_code[i])
                    shared_vars = sum(1 for v in all_vars if state[v] == other_state[v])
                    if shared_vars != shared_letters:
                        collision = True
                        break
                
                if not collision: return state
                attempts += 1
            return state

        final_clue_data = []
        for code in clue_codes:
            st = make_state_with_protection(code, final_clue_data)
            final_clue_data.append((code, st))
            
        # --- FIX 2: Generate target state specifically checking against final_clue_data ---
        target_state = make_state_with_protection(target_code, final_clue_data)

        # 5. RENDERING
        strip = Image.new('RGB', (self.strip_w_hd, self.strip_h_hd), 'white')
        for i, (code, state) in enumerate(final_clue_data):
            bx_cx = 125 * self.sf + i*(self.cell_size_hd+self.spacing_hd)+self.cell_size_hd//2
            self.render_box_static(strip, bx_cx, self.cell_size_hd//2+100*self.sf, code, state, False)
        
        target_img = Image.new('RGB', (self.cell_size_hd+200*self.sf, self.strip_h_hd), 'white')
        self.render_box_static(target_img, target_img.width//2, self.cell_size_hd//2+100*self.sf, target_code, target_state, True)

        # --- CROPPING & FINALIZING (Keep your existing logic here) ---
        strip_diff = ImageOps.invert(strip.convert("RGB")).getbbox()
        strip_final = strip.crop((max(0, strip_diff[0]-10), max(0, strip_diff[1]-10), min(strip.width, strip_diff[2]+10), min(strip.height, strip_diff[3]+10)))
        target_diff = ImageOps.invert(target_img.convert("RGB")).getbbox()
        target_cropped = target_img.crop(target_diff)
        canvas_target = Image.new('RGB', (strip_final.width, strip_final.height), 'white')
        canvas_target.paste(target_cropped, ((canvas_target.width - target_cropped.width) // 2, (canvas_target.height - target_cropped.height) // 2))

        def resize_out(img): return img.resize((img.width // self.sf, img.height // self.sf), Image.Resampling.LANCZOS)

        return {
            "Set_ID": set_id,
            "Answer": target_code,
            "Variable_1": v1_name,
            "Variable_2": v2_name,
            "Mappings": mapping_str, # Updated string
            "Final_Images": (resize_out(strip_final), resize_out(canvas_target))
        }

    def render_box_static(self, canvas, cx, cy, code, p, is_target):
        for i in range(3):
            self._draw_masked_obj(canvas, p['r1_sh'], p['r1_pt'], cx + (i-1)*55*self.sf, cy-85*self.sf, self.small_r_hd, p['r1_or'], p['r1_ol'])
        self._draw_masked_obj(canvas, p['r2_sh'], p['r2_pt'], cx, cy+25*self.sf, self.large_r_hd, p['r2_or'], p['r2_ol'])
        txt = "??" if is_target else code
        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
        draw.text((cx - (bbox[2]-bbox[0])//2, cy + 25*self.sf + self.large_r_hd + 25*self.sf), txt, font=self.font_hd, fill="black")

if __name__ == "__main__":
    gen = NVREasyGenerator()
    how_many_input = input("How many easy sets? ")
    how_many = int(how_many_input) if how_many_input else 1
    manifest = []
    for idx in range(1, how_many + 1):
        data = gen.generate_puzzle_set(idx)
        set_dir = os.path.join(OUTPUT_FOLDER, f"EasySet_{idx}")
        os.makedirs(set_dir, exist_ok=True)
        strip_img, target_img = data.pop("Final_Images")
        strip_img.save(os.path.join(set_dir, "Clues.png"))
        target_img.save(os.path.join(set_dir, "Target.png"))
        manifest.append(data)
        print(f"Set {idx} created.")
    if manifest:
        with open(os.path.join(OUTPUT_FOLDER, "manifest.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=manifest[0].keys())
            writer.writeheader(); writer.writerows(manifest)