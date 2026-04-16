import random
import os
import math
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Configuration ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_codes_c")

MAC_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental"
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

class NVRGenerator:
    def __init__(self):
        # I. FEATURE DECKS (16 Variables: 4 per Quadrant)
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

        # II. DIMENSIONS
        self.sf = 4 
        self.cell_size_hd = 180 * self.sf   # Shrunk from 220 to wrap tightly around the smaller shapes
        self.spacing_hd = 80 * self.sf      # Increased slightly to ensure massive gaps between clues
        self.strip_w_hd = (self.cell_size_hd * 4) + (self.spacing_hd * 3) + (120 * self.sf)
        self.strip_h_hd = self.cell_size_hd + (100 * self.sf) 

        # Radius and offsets for the 2x2 grid
        self.mid_r_hd = 35 * self.sf        # Shrunk from 45. This makes the shapes noticeably smaller.
        self.q_offset = 45 * self.sf        # Pulled in from 58. Shapes are now tightly clustered.

        # III. FONT LOADER
        self.font_hd = None
        font_found = False
        
        print("Searching for Proxima Soft Regular...")
        for d in MAC_FONT_DIRS:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                l_f = f.lower()
                if "proxima" in l_f and "soft" in l_f:
                    forbidden = ['italic', ' it.', ' it ', 'light', ' lt', 'bold', 'semibold', 'medium', ' thin']
                    if any(bad in l_f for bad in forbidden): continue
                    if l_f.endswith('it.otf') or l_f.endswith('it.ttf'): continue
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
        if shape_type == 'circle': 
            return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == 'square':
            adj = r * 0.85
            pts = [(cx-adj, cy-adj), (cx+adj, cy-adj), (cx+adj, cy+adj), (cx-adj, cy+adj)]
        elif shape_type == 'triangle':
            for i in range(3):
                ang = math.radians(-90 + i * 120)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        elif shape_type == 'arrow':
            pts = [(cx + 1.25*r, cy), (cx - 0.75*r, cy - r), (cx - 0.15*r, cy), (cx - 0.75*r, cy + r)]
        elif shape_type == 'star':
            for i in range(10):
                ang = math.radians(-90 + i * 36)
                curr_r = r if i % 2 == 0 else r * 0.45
                pts.append((cx + curr_r * math.cos(ang), cy + curr_r * math.sin(ang)))
        elif shape_type == 'cross_shape':
            w = r * 0.35
            pts = [(cx-w, cy-r), (cx+w, cy-r), (cx+w, cy-w), (cx+r, cy-w), (cx+r, cy+w), (cx+w, cy+w), (cx+w, cy+r), (cx-w, cy+r), (cx-w, cy+w), (cx-r, cy+w), (cx-r, cy-w), (cx-w, cy-w)]
        elif shape_type == 'pentagon':
            for i in range(5):
                ang = math.radians(-90 + i * 72)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        elif shape_type == 'hexagon':
            for i in range(6): 
                pts.append((cx + r * math.cos(math.radians(-90 + i*60)), cy + r * math.sin(math.radians(-90 + i*60))))

        if rotation != 0:
            rad = math.radians(rotation)
            rotated_pts = []
            for px, py in pts:
                dx, dy = px - cx, py - cy
                nx = cx + dx * math.cos(rad) - dy * math.sin(rad)
                ny = cy + dx * math.sin(rad) + dy * math.cos(rad)
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
                        draw.line([(x + offset, y), (x + offset, y + bh)], fill="black", width=2*sf)
            elif variant == 'basketweave':
                bs = 20 * sf
                for x in range(0, size, bs):
                    for y in range(0, size, bs):
                        if (x // bs + y // bs) % 2 == 0:
                            for i in range(2, bs, 6*sf): draw.line([(x + 2*sf, y + i), (x + bs - 2*sf, y + i)], fill="black", width=2*sf)
                        else:
                            for i in range(2, bs, 6*sf): draw.line([(x + i, y + 2*sf), (x + i, y + bs - 2*sf)], fill="black", width=2*sf)
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
                if len(pts) > 1: draw.line(pts, fill="black", width=2*sf)
                    
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
                if variant == 'vertical': draw.line([(li, 0), (li, size)], fill="black", width=2*sf)
                elif variant == 'diagonal_tl_br': draw.line([(li, 0), (li+size, size)], fill="black", width=2*sf)
                else: draw.line([(li, 0), (li-size, size)], fill="black", width=2*sf)
                    
        elif category == 'grids':
            if variant == 'tilted_diamond':
                gs = 16*sf
                for gi in range(-size, size*2, gs):
                    draw.line([(gi, 0), (gi-size, size)], fill="black", width=2*sf)
                    draw.line([(gi-size, 0), (gi, size)], fill="black", width=2*sf)
            else:
                gs = 22*sf if 'large' in variant else 10*sf
                for gx in range(0, size+10*sf, gs): draw.line([(gx, 0), (gx, size)], fill="black", width=2*sf)
                for gy in range(0, size+10*sf, gs): draw.line([(0, gy), (size, gy)], fill="black", width=2*sf)

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

    def generate_puzzle_set(self, version):
        all_vars = [f"{q}_{f}" for q in ['q1', 'q2', 'q3', 'q4'] for f in ['sh', 'pt', 'or', 'sp']]
        
        # 0-14 = 2 Coded Vars | 15-28 = 3 Coded Vars
        v_map = {}
        for i in range(15): v_map[i] = (2, i)
        for i in range(14): v_map[15+i] = (3, i)
        
        num_coded, num_noise = v_map[version]
        
        shuffled = random.sample(all_vars, len(all_vars))

        coded_vars = []
        active_sh = set()
        active_or = set()
        active_sp = set()

        # Variable conflict prevention
        for v in shuffled:
            if len(coded_vars) >= num_coded: break
            row = v[:2]
            if 'sh' in v and (row in active_or or row in active_sp): continue
            if 'or' in v and (row in active_sh or row in active_sp): continue
            if 'sp' in v and (row in active_sh or row in active_or): continue
            
            coded_vars.append(v)
            if 'sh' in v: active_sh.add(row)
            if 'or' in v: active_or.add(row)
            if 'sp' in v: active_sp.add(row)
        
        remaining = [v for v in shuffled if v not in coded_vars]
        noise_vars = []
        for v in remaining:
            if len(noise_vars) >= num_noise: break
            row = v[:2]
            if 'sh' in v and (row in active_or or row in active_sp): continue
            if 'or' in v and (row in active_sh or row in active_sp): continue
            if 'sp' in v and (row in active_sh or row in active_or): continue
                
            noise_vars.append(v)
            if 'sh' in v: active_sh.add(row)
            if 'or' in v: active_or.add(row)
            if 'sp' in v: active_sp.add(row)

        fixed_vars = [v for v in all_vars if v not in coded_vars and v not in noise_vars]

        def get_rand_v(v):
            row_p = v[:2]
            if 'sh' in v:
                if f"{row_p}_or" in coded_vars or f"{row_p}_or" in noise_vars or f"{row_p}_sp" in coded_vars or f"{row_p}_sp" in noise_vars:
                    return random.choice(self.rotatable_shapes)
                return random.choice(self.all_shapes)
            if 'pt' in v: 
                cat = random.choice(list(self.shading_categories.keys()))
                return (cat, random.choice(self.shading_categories[cat]))
            if 'or' in v: return random.choice([0, 90, 180, 270])
            if 'sp' in v: return random.choice(['cw', 'acw', 'none'])

        master_valid = False
        while not master_valid:
            label_sets = [['A','B','C'], ['X','Y','Z'], ['1','2','3']][:num_coded]
            trans, mapping_str = {}, []

            fixed_vals = {}
            for v in fixed_vars:
                row_p = v[:2]
                if 'sh' in v and (f"{row_p}_or" in coded_vars or f"{row_p}_or" in noise_vars or f"{row_p}_sp" in coded_vars or f"{row_p}_sp" in noise_vars):
                    fixed_vals[v] = random.choice(self.rotatable_shapes)
                elif 'sp' in v:
                    fixed_vals[v] = 'none' 
                else:
                    fixed_vals[v] = get_rand_v(v)

            for i, var in enumerate(coded_vars):
                row_p = var[:2]
                if 'sh' in var: 
                    pool = self.rotatable_shapes if (f"{row_p}_or" in coded_vars or f"{row_p}_or" in noise_vars or f"{row_p}_sp" in coded_vars or f"{row_p}_sp" in noise_vars) else self.all_shapes
                elif 'pt' in var: 
                    pool = []
                    for c, vs in self.shading_categories.items():
                        for v_shade in vs: pool.append((c, v_shade))
                elif 'or' in var: 
                    f_shape = fixed_vals.get(f"{row_p}_sh") if f"{row_p}_sh" in fixed_vars else 'triangle'
                    pool = [0, 45, 90, 135, 180, 225, 270, 315] if f_shape in ['triangle', 'arrow'] else [0, 90, 180, 270]
                elif 'sp' in var:
                    pool = ['cw', 'acw', 'none']
                
                states = random.sample(pool, 3)
                for label, state in zip(label_sets[i], states): 
                    trans[label] = state
                    mapping_str.append(f"{label}={state}")

            solvable = False
            attempts = 0
            while not solvable and attempts < 1000:
                attempts += 1
                target_code = "".join(random.choice(ls) for ls in label_sets)
                clue_codes = [("".join(random.choice(ls) for ls in label_sets)) for _ in range(4)]
                
                # Ensure each position has enough variety to deduce a rule
                pos_valid = True
                for i in range(num_coded):
                    if len(set(c[i] for c in clue_codes)) < 2:
                        pos_valid = False; break
                
                # Ensure Target characters exist in the clues
                if not pos_valid or not all(any(code[i] == target_code[i] for code in clue_codes) for i in range(num_coded)):
                    continue

                clue_noises = [{v: get_rand_v(v) for v in noise_vars} for _ in range(4)]
                target_noise = {v: get_rand_v(v) for v in noise_vars}
                
                # Build Full States
                target_state = fixed_vals.copy()
                target_state.update(target_noise)
                for i, char in enumerate(target_code): 
                    target_state[coded_vars[i]] = trans[char]
                
                clue_states_list = []
                for c_idx in range(4):
                    s = fixed_vals.copy()
                    s.update(clue_noises[c_idx])
                    for i, char in enumerate(clue_codes[c_idx]): 
                        s[coded_vars[i]] = trans[char]
                    clue_states_list.append(s)

                # Check for Spoiled or Duplicate Clues
                if any(s == target_state for s in clue_states_list):
                    continue
                if len(set(frozenset(d.items()) for d in clue_states_list)) < 4:
                    continue

                # --- RIGOROUS SOLVABILITY CHECK ---
                is_ambiguous = False
                for i in range(num_coded):
                    predicted_chars = set()
                    
                    # Test ALL 16 variables to see if they form an accidental valid rule
                    for v in all_vars:
                        mapping = {}
                        valid_rule = True
                        for j in range(4):
                            state = clue_states_list[j][v]
                            char = clue_codes[j][i]
                            if state in mapping and mapping[state] != char:
                                valid_rule = False # Contradiction found, not a valid rule
                                break
                            mapping[state] = char
                        
                        if valid_rule:
                            # Rule works for the clues! What does it predict for the target?
                            t_state = target_state[v]
                            if t_state in mapping:
                                predicted_chars.add(mapping[t_state])
                    
                    # If multiple rules point to DIFFERENT characters, the puzzle is ambiguous
                    if len(predicted_chars) > 1:
                        is_ambiguous = True
                        break
                
                if not is_ambiguous:
                    # The puzzle is mathematically verified to be unambiguously solvable!
                    solvable = True
                    master_valid = True

        # V. RENDER & ANIMATION
        num_frames = 60
        raw_frames = []

        def render_box(canvas, cx, cy, code, noise_p, is_target, current_frame):
            p = fixed_vals.copy()
            p.update(noise_p)
            for i, char in enumerate(code): p[coded_vars[i]] = trans[char]
            
            q_centers = {
                'q1': (cx - self.q_offset, cy - self.q_offset),
                'q2': (cx + self.q_offset, cy - self.q_offset),
                'q3': (cx - self.q_offset, cy + self.q_offset),
                'q4': (cx + self.q_offset, cy + self.q_offset)
            }

            for q in ['q1', 'q2', 'q3', 'q4']:
                sp_val = p.get(f'{q}_sp', 'none')
                if sp_val == 'cw': rot_offset = (360 / num_frames) * current_frame
                elif sp_val == 'acw': rot_offset = -(360 / num_frames) * current_frame
                else: rot_offset = 0
                
                final_rot = p.get(f'{q}_or', 0) + rot_offset
                
                self._draw_masked_obj(
                    canvas, 
                    shape=p[f'{q}_sh'], 
                    pattern=p[f'{q}_pt'], 
                    cx=q_centers[q][0], 
                    cy=q_centers[q][1], 
                    r=self.mid_r_hd, 
                    rotation=final_rot, 
                    outline_w=2.5 
                )

            txt = "?" * len(code) if is_target else code
            draw = ImageDraw.Draw(canvas)
            bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
            
            max_sweep = int(self.mid_r_hd * 1.25)
            text_y = cy + self.q_offset + max_sweep + 20 * self.sf 
            draw.text((cx - (bbox[2]-bbox[0])//2, text_y), txt, font=self.font_hd, fill="black")

        for frame in range(num_frames):
            strip = Image.new('RGB', (self.strip_w_hd, self.strip_h_hd), 'white')
            target_img = Image.new('RGB', (self.cell_size_hd+150*self.sf, self.strip_h_hd), 'white')
            
            for i, code in enumerate(clue_codes):
                bx_cx = 100 * self.sf + i*(self.cell_size_hd+self.spacing_hd)+self.cell_size_hd//2
                render_box(strip, bx_cx, self.cell_size_hd//2+40*self.sf, code, clue_noises[i], False, frame)
            
            render_box(target_img, target_img.width//2, self.cell_size_hd//2+40*self.sf, target_code, target_noise, True, frame)
            raw_frames.append((strip, target_img))

        min_x_s, min_y_s, max_x_s, max_y_s = self.strip_w_hd, self.strip_h_hd, 0, 0
        min_x_t, min_y_t, max_x_t, max_y_t = target_img.width, target_img.height, 0, 0

        for s_img, t_img in raw_frames:
            sd = ImageOps.invert(s_img.convert("RGB")).getbbox()
            td = ImageOps.invert(t_img.convert("RGB")).getbbox()
            if sd:
                min_x_s, min_y_s = min(min_x_s, sd[0]), min(min_y_s, sd[1])
                max_x_s, max_y_s = max(max_x_s, sd[2]), max(max_y_s, sd[3])
            if td:
                min_x_t, min_y_t = min(min_x_t, td[0]), min(min_y_t, td[1])
                max_x_t, max_y_t = max(max_x_t, td[2]), max(max_y_t, td[3])

        crop_box_strip = (max(0, min_x_s-10), max(0, min_y_s-10), min(self.strip_w_hd, max_x_s+10), min(self.strip_h_hd, max_y_s+10))
        crop_box_target = (min_x_t, min_y_t, max_x_t, max_y_t)

        strip_final_frames = []
        target_final_frames = []

        for s_img, t_img in raw_frames:
            strip_cropped = s_img.crop(crop_box_strip)
            target_cropped = t_img.crop(crop_box_target)
            
            canvas_target = Image.new('RGB', (strip_cropped.width, strip_cropped.height), 'white')
            paste_x = (canvas_target.width - target_cropped.width) // 2
            paste_y = (canvas_target.height - target_cropped.height) // 2
            canvas_target.paste(target_cropped, (paste_x, paste_y))
            
            strip_final_frames.append(strip_cropped)
            target_final_frames.append(canvas_target)

        weights = {'or': 5, 'sp': 5, 'sh': 2, 'pt': 2}
        signal_score = sum((weights[v[3:]]) for v in coded_vars)
        noise_score = sum((weights[v[3:]]) for v in noise_vars)
        total_difficulty = signal_score + (noise_score * 0.5)

        return {
            "Difficulty_Score": round(total_difficulty, 2),
            "Version": version, 
            "Answer": target_code, 
            "Signal": "|".join(coded_vars), 
            "Noise": "|".join(noise_vars), 
            "Fixed": "|".join(fixed_vars), 
            "Mappings": "; ".join(mapping_str),
            "Images": (strip_final_frames, target_final_frames)
        }

if __name__ == "__main__":
    import gc  # Used to force the Mac to clear memory

    gen = NVRGenerator()
    how_many_input = input("How many? ")
    how_many = int(how_many_input) if how_many_input else 1
    
    print("\nRandom, or Specific (0-28)")
    mode = input("Choice: ").lower() or "random"

    results = []
    
    # --- PHASE 1: GENERATE AND SAVE TEMPORARILY ---
    for i in range(how_many):
        print(f"Generating puzzle {i+1}/{how_many}...")
        v = random.randint(0, 28) if mode == "random" else int(mode)
        data = gen.generate_puzzle_set(v)
        
        # Extract images IMMEDIATELY so we don't store them in the 'results' list
        strip_gifs, target_gifs = data.pop("Images")
        
        # Create a TEMPORARY folder to dump the images onto the hard drive
        temp_dir_name = f"temp_set_{i}"
        temp_dir = os.path.join(OUTPUT_FOLDER, temp_dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        clues_path = os.path.join(temp_dir, "Clues.gif")
        target_path = os.path.join(temp_dir, "Target.gif")

        # Resize and save
        c_frames = [f.resize((f.width // gen.sf, f.height // gen.sf), Image.Resampling.LANCZOS) for f in strip_gifs]
        t_frames = [f.resize((f.width // gen.sf, f.height // gen.sf), Image.Resampling.LANCZOS) for f in target_gifs]

        c_frames[0].save(clues_path, save_all=True, append_images=c_frames[1:], duration=30, loop=0)
        t_frames[0].save(target_path, save_all=True, append_images=t_frames[1:], duration=30, loop=0)
        
        # Keep track of where we saved this specific puzzle's temporary folder
        data["_temp_dir"] = temp_dir
        results.append(data)
        
        # TRASH THE IMAGES FROM RAM to prevent the "Killed" error
        del strip_gifs, target_gifs, c_frames, t_frames
        gc.collect()

    # --- PHASE 2: SORT METADATA AND RENAME FOLDERS ---
    print("\nSorting by difficulty and finalizing folders...")
    
    # Sort the lightweight text data (RAM is safe because images are on the hard drive)
    results.sort(key=lambda x: x["Difficulty_Score"])
    
    manifest = []
    for idx, data in enumerate(results, 1):
        # Retrieve the temporary folder path
        temp_dir = data.pop("_temp_dir")
        
        # Define the final sorted folder name
        final_dir_name = f"Set_{idx}_V{data['Version']}"
        final_dir = os.path.join(OUTPUT_FOLDER, final_dir_name)
        
        # Rename the folder on the desktop
        os.rename(temp_dir, final_dir)
        
        # Prepare data for the manifest
        row = {"Set_ID": idx}
        row.update(data)
        manifest.append(row)
    
    # --- PHASE 3: WRITE MANIFEST ---
    if manifest:
        with open(os.path.join(OUTPUT_FOLDER, "manifest.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=manifest[0].keys())
            writer.writeheader()
            writer.writerows(manifest)

    print(f"\nProduction Complete. Output in {OUTPUT_FOLDER}")