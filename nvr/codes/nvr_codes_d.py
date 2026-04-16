import random
import os
import math
import csv
import gc
import itertools
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Configuration ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_codes_d")

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
        # FEATURE DECKS (9 potential variables: shape, pattern, orientation, spin for 2 layers + scale for front)
        self.all_shapes = ['circle', 'square', 'pentagon', 'triangle', 'hexagon', 'arrow', 'star', 'cross_shape']
        self.rotatable_shapes = ['triangle', 'arrow', 'pentagon', 'star']
        
        # Added 'solid' category with white, grey, and black
        self.shading_categories = {
            'solid': ['white', 'grey', 'black'],
            'arrows': ['up', 'down', 'left', 'right'],
            'lines': ['vertical', 'diagonal_tl_br', 'diagonal_tr_bl'],
            'grids': ['standard_large', 'standard_small', 'tilted_diamond'],
            'wavy': ['wavy_v', 'wavy_h', 'wavy_d'],
            'mini_tri': ['tri_up', 'tri_down', 'tri_left', 'tri_right'],
            'tiling': ['brickwork', 'basketweave', 'hexagonal_honeycomb']
        }
        
        self.sf = 4 
        self.cell_size_hd = 220 * self.sf
        self.spacing_hd = 45 * self.sf
        self.strip_w_hd = (self.cell_size_hd * 4) + (self.spacing_hd * 3) + (150 * self.sf)
        self.strip_h_hd = self.cell_size_hd + (250 * self.sf) 

        self.back_r_hd = 85 * self.sf   
        self.fixed_outline_w = 2.5      

        # STRICT FONT LOADER
        self.font_hd = None
        font_found = False
        print("Searching for strictly Proxima Soft Regular...")
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
                        print(f"SUCCESS: Loaded {f}")
                        font_found = True
                        break
                    except: continue
            if font_found: break

        if not font_found:
            print("Proxima Soft Regular not found. Fallback to default.")
            self.font_hd = ImageFont.load_default()

    def get_shape_coords_hd(self, shape_type, cx, cy, r, rotation=0):
        pts = []
        if shape_type == 'circle': return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == 'square':
            adj = r * 0.85
            pts = [(cx-adj, cy-adj), (cx+adj, cy-adj), (cx+adj, cy+adj), (cx-adj, cy+adj)]
        elif shape_type == 'triangle':
            for i in range(3):
                ang = math.radians(-90 + i * 120)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        elif shape_type == 'arrow':
            pts = [(cx + r, cy), (cx - r, cy - r), (cx - 0.4*r, cy), (cx - r, cy + r)]
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

        if rotation != 0 and shape_type != 'circle':
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
        
        # New Solid Colors Logic
        if category == 'solid':
            color_map = {
                'white': (255, 255, 255, 255), 
                'grey': (160, 160, 160, 255), 
                'black': (0, 0, 0, 255)
            }
            draw.rectangle([0, 0, size, size], fill=color_map[variant])
            
        elif category == 'tiling':
            if variant == 'brickwork':
                bw, bh = 24*sf, 12*sf
                for y in range(0, size + bh, bh):
                    offset = (bw // 2) if (y // bh) % 2 == 0 else 0
                    draw.line([(0, y), (size, y)], fill="black", width=1*sf)
                    for x in range(-bw, size + bw, bw): draw.line([(x + offset, y), (x + offset, y + bh)], fill="black", width=2*sf)
            elif variant == 'basketweave':
                bs = 20 * sf
                for x in range(0, size, bs):
                    for y in range(0, size, bs):
                        if (x // bs + y // bs) % 2 == 0:
                            for i in range(2, bs, 6*sf): draw.line([(x + 2*sf, y + i), (x + bs - 2*sf, y + i)], fill="black", width=2*sf)
                        else:
                            for i in range(2, bs, 6*sf): draw.line([(x + i, y + 2*sf), (x + i, y + bs - 2*sf)], fill="black", width=2*sf)
            elif variant == 'hexagonal_honeycomb':
                h_r = 10*sf
                h_w, h_h = math.sqrt(3) * h_r, 2 * h_r
                for row in range(-1, (size // int(h_h * 0.75)) + 2):
                    for col in range(-1, (size // int(h_w)) + 2):
                        cx, cy = col * h_w + (h_w/2 if row % 2 else 0), row * h_h * 0.75
                        pts = [(cx + h_r * math.cos(math.radians(30 + i * 60)), cy + h_r * math.sin(math.radians(30 + i * 60))) for i in range(6)]
                        draw.polygon(pts, outline="black", width=1*sf)
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
            gs = 16*sf if variant == 'tilted_diamond' else (22*sf if 'large' in variant else 10*sf)
            if variant == 'tilted_diamond':
                for gi in range(-size, size*2, gs):
                    draw.line([(gi, 0), (gi-size, size)], fill="black", width=2*sf)
                    draw.line([(gi-size, 0), (gi, size)], fill="black", width=2*sf)
            else:
                for gx in range(0, size+10*sf, gs): draw.line([(gx, 0), (gx, size)], fill="black", width=2*sf)
                for gy in range(0, size+10*sf, gs): draw.line([(0, gy), (size, gy)], fill="black", width=2*sf)

    def _draw_masked_obj(self, canvas, shape, pattern, cx, cy, r, rotation=0):
        size = int(r * 3.5) # Generous buffer to prevent clipping internal patterns
        buf = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        mask = Image.new('L', (size, size), 0)
        self.draw_pattern_hd(ImageDraw.Draw(buf), pattern, size)
        
        loc_pts = self.get_shape_coords_hd(shape, size // 2, size // 2, r, rotation)
        glob_pts = self.get_shape_coords_hd(shape, cx, cy, r, rotation)
        draw = ImageDraw.Draw(canvas)
        weight_hd = int(self.fixed_outline_w * self.sf)

        if shape == 'circle':
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight_hd)
        else:
            draw.polygon(glob_pts, fill="white") 
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)
            closed_glob = glob_pts + [glob_pts[0]]
            draw.line(closed_glob, fill="black", width=weight_hd, joint="curve")

    def generate_puzzle_set(self, version):
        all_vars = ['f_sh', 'f_pt', 'f_or', 'f_sp', 'f_sc', 'b_sh', 'b_pt', 'b_or', 'b_sp']
        v_map = {
            1:(2,0), 2:(2,1), 3:(2,2), 4:(2,3), 5:(2,4), 6:(2,5), 7:(2,6),
            8:(3,0), 9:(3,1), 10:(3,2), 11:(3,3), 12:(3,4), 13:(3,5)
        }
        num_coded, num_noise = v_map[version]
        
        # --- FIX 1: Relief Valve ---
        # If the script tries 50 times and fails, the requested version is mathematically 
        # impossible with our strict constraints. It will sacrifice 1 noise variable to proceed.
        valid_vars = False
        attempts = 0
        while not valid_vars:
            attempts += 1
            if attempts > 50:
                num_noise = max(0, num_noise - 1)
                attempts = 0
                
            shuffled = random.sample(all_vars, len(all_vars))
            coded_vars = shuffled[:num_coded]
            noise_vars = shuffled[num_coded:num_coded+num_noise]
            active_vars = coded_vars + noise_vars

            if 'f_sc' in coded_vars and 'f_sh' in active_vars:
                continue
                
            # Global mutual exclusion for Orientation and Spin (Fixes Issue 3)
            if any('or' in v for v in active_vars) and any('sp' in v for v in active_vars):
                continue
                
            # Orientation requires fixed shape for that layer (Fixes Issue 4)
            if ('f_or' in active_vars and 'f_sh' in active_vars) or \
               ('b_or' in active_vars and 'b_sh' in active_vars):
                continue
                
            valid_vars = True
            
        fixed_vars = [v for v in all_vars if v not in active_vars]

        def get_rand_v(v):
            if 'sh' in v: return random.choice(self.rotatable_shapes if (v[0]+'_or' in active_vars or v[0]+'_sp' in active_vars) else self.all_shapes)
            if 'pt' in v:
                cat = random.choice(list(self.shading_categories.keys()))
                return (cat, random.choice(self.shading_categories[cat]))
            if 'or' in v: return random.choice([0, 45, 90, 135, 180, 225, 270, 315])
            if 'sp' in v: return random.choice(['cw', 'acw', 'none']) 
            if 'sc' in v: return random.choice([0.35, 0.45, 0.55]) 
            return None

        master_valid = False
        while not master_valid:
            label_sets = [['A','B','C'], ['X','Y','Z'], ['1','2','3']][:num_coded]
            trans = {}
            mapping_str = []
            
            fixed_vals = {v: (get_rand_v(v) if 'sp' not in v else 'none') for v in fixed_vars}
            if 'f_sc' in fixed_vars: fixed_vals['f_sc'] = 0.45 

            for i, var in enumerate(coded_vars):
                # Keeps the fix for invisible spinning circles
                if 'sh' in var: pool = self.rotatable_shapes if (var[0]+'_or' in active_vars or var[0]+'_sp' in active_vars) else self.all_shapes
                elif 'pt' in var: pool = [(c, s) for c, shades in self.shading_categories.items() for s in shades]
                elif 'or' in var: pool = [0, 45, 90, 135, 180, 225, 270, 315]
                elif 'sc' in var: pool = [0.35, 0.45, 0.55]
                else: pool = ['cw', 'acw', 'none']
                
                states = random.sample(pool, 3)
                for label, state in zip(label_sets[i], states): 
                    trans[label] = state
                    mapping_str.append(f"{label}={state}")

            # --- UNBREAKABLE SOLVABILITY RULE ---
            all_possible_codes = ["".join(c) for c in itertools.product(*label_sets)]
            
            valid_codes_found = False
            while not valid_codes_found:
                chosen_codes = random.sample(all_possible_codes, 5)
                target_code = chosen_codes[0]
                clue_codes = chosen_codes[1:]
                
                valid_codes_found = True
                
                # Loop through every character in the Target Code
                for i, char in enumerate(target_code):
                    clue_column = [clue[i] for clue in clue_codes]
                    
                    # If the target's letter is NOT in the clues for this position, reject the whole set and try again
                    if char not in clue_column:
                        valid_codes_found = False
                        break

            clue_noises = [{v: get_rand_v(v) for v in noise_vars} for _ in range(4)]
            target_noise = {v: get_rand_v(v) for v in noise_vars}
            
            target_state = {**fixed_vals, **target_noise}
            for i, char in enumerate(target_code): target_state[coded_vars[i]] = trans[char]
            
            clue_states_list = []
            for idx in range(4):
                s = {**fixed_vals, **clue_noises[idx]}
                for i, char in enumerate(clue_codes[idx]): s[coded_vars[i]] = trans[char]
                clue_states_list.append(s)
            
            if len(set(frozenset(d.items()) for d in clue_states_list)) == 4:
                if frozenset(target_state.items()) not in [frozenset(d.items()) for d in clue_states_list]:
                    master_valid = True

        num_frames = 60
        raw_frames = []

        def render_box(canvas, cx, cy, p_state, label, is_target, frame):
            p = p_state.copy()
            for layer in ['f', 'b']:
                rot = p.get(f'{layer}_or', 0)
                sp = p.get(f'{layer}_sp', 'none')
                if sp == 'cw': rot += (360/num_frames) * frame
                elif sp == 'acw': rot -= (360/num_frames) * frame
                p[f'{layer}_rot_now'] = rot

            f_radius = self.back_r_hd * p.get('f_sc', 0.45)

            self._draw_masked_obj(canvas, p['b_sh'], p['b_pt'], cx, cy, self.back_r_hd, p['b_rot_now'])
            self._draw_masked_obj(canvas, p['f_sh'], p['f_pt'], cx, cy, f_radius, p['f_rot_now'])

            txt = "?" * len(label) if is_target else label
            draw = ImageDraw.Draw(canvas)
            bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
            
            draw.text((cx - (bbox[2]-bbox[0])//2, cy + int(self.back_r_hd * 1.35) + 20*self.sf), txt, font=self.font_hd, fill="black")

        for f in range(num_frames):
            strip = Image.new('RGB', (self.strip_w_hd, self.strip_h_hd), 'white')
            target_img = Image.new('RGB', (self.cell_size_hd+100*self.sf, self.strip_h_hd), 'white')
            for i, code in enumerate(clue_codes):
                render_box(strip, 130*self.sf + i*(self.cell_size_hd+self.spacing_hd), self.cell_size_hd//2+50*self.sf, clue_states_list[i], code, False, f)
            render_box(target_img, target_img.width//2, self.cell_size_hd//2+50*self.sf, target_state, target_code, True, f)
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

        strip_final = []
        target_final = []
        for s_img, t_img in raw_frames:
            strip_cropped = s_img.crop(crop_box_strip)
            target_cropped = t_img.crop(crop_box_target)
            
            tc = Image.new('RGB', (strip_cropped.width, strip_cropped.height), 'white')
            tc.paste(target_cropped, ((tc.width-target_cropped.width)//2, (tc.height-target_cropped.height)//2))
            
            strip_final.append(strip_cropped)
            target_final.append(tc)

        # Identify the exact version that was actually built
        actual_version = next((k for k, v in v_map.items() if v == (num_coded, num_noise)), version)

        return {
            "Difficulty_Score": round(num_coded * 3.5 + num_noise * 1.5, 2),
            "Version": actual_version,
            "Answer": target_code,
            "Signal": "|".join(coded_vars), 
            "Noise": "|".join(noise_vars),
            "Fixed": "|".join(fixed_vars),
            "Mappings": "; ".join(mapping_str), 
            "Images": (strip_final, target_final)
        }

if __name__ == "__main__":
    gen = NVRGenerator()
    num = int(input("How many puzzles to generate? ") or 1)
    results = []
    for i in range(num):
        print(f"Generating Puzzle {i+1}...")
        data = gen.generate_puzzle_set(random.randint(1, 13))
        strip_gifs, target_gifs = data.pop("Images")
        temp_dir = os.path.join(OUTPUT_FOLDER, f"temp_puz_{i}")
        os.makedirs(temp_dir, exist_ok=True)
        
        c_frames = [f.resize((f.width//gen.sf, f.height//gen.sf), Image.LANCZOS) for f in strip_gifs]
        t_frames = [f.resize((f.width//gen.sf, f.height//gen.sf), Image.LANCZOS) for f in target_gifs]
        c_frames[0].save(os.path.join(temp_dir, "Clues.gif"), save_all=True, append_images=c_frames[1:], duration=40, loop=0)
        t_frames[0].save(os.path.join(temp_dir, "Target.gif"), save_all=True, append_images=t_frames[1:], duration=40, loop=0)
        
        data["_temp"] = temp_dir
        results.append(data)
        del strip_gifs, target_gifs, c_frames, t_frames
        gc.collect()

    results.sort(key=lambda x: x["Difficulty_Score"])
    final_manifest = []
    for idx, d in enumerate(results, 1):
        tmp = d.pop("_temp")
        final_dir = os.path.join(OUTPUT_FOLDER, f"Set_{idx}_V{d['Version']}")
        if os.path.exists(final_dir): import shutil; shutil.rmtree(final_dir)
        os.rename(tmp, final_dir)
        final_manifest.append({"Set_ID": idx, **d})

    with open(os.path.join(OUTPUT_FOLDER, "manifest.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_manifest[0].keys())
        writer.writeheader()
        writer.writerows(final_manifest)
    print(f"\nComplete. Files located in: {OUTPUT_FOLDER}")