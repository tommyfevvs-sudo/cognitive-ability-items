import random
import os
import math
import csv
import itertools
import shutil
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Configuration ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_codes_version_e")
TEMP_FOLDER = os.path.join(OUTPUT_FOLDER, "_temp_processing")

MAC_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts", "/System/Library/Fonts", "/System/Library/Fonts/Supplemental"
]

if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)

class NVRAnimatedMatrixGenerator:
    def __init__(self):
        # 1. Feature Decks
        self.all_shapes = ['square', 'circle', 'triangle', 'pentagon', 'hexagon', 'star', 'arrow']
        self.rotatable_shapes = ['triangle', 'arrow', 'pentagon', 'star']
        self.shading_categories = {
            'solid': ['white', '#888888', 'black'],
            'lines': ['vertical', 'diagonal_tl_br', 'diagonal_tr_bl'],
            'grids': ['standard_large', 'tilted_diamond'],
            'wavy': ['wavy_v', 'wavy_h'],
            'tiling': ['brickwork', 'basketweave']
        }

        # 2. Dimensions & Animation Settings
        self.sf = 3 
        self.cell_size_hd = 240 * self.sf 
        self.spacing_hd = 35 * self.sf
        self.strip_w_hd = (self.cell_size_hd * 4) + (self.spacing_hd * 3) + (120 * self.sf)
        self.strip_h_hd = self.cell_size_hd + (350 * self.sf) 
        self.left_r_hd = 26 * self.sf   
        self.right_r_hd = 20 * self.sf  
        
        self.num_frames = 45 # Smooth oscillation loop
        self.frame_duration = 100 

        # 3. Font Loader
        self.font_hd = None
        font_found = False
        for d in MAC_FONT_DIRS:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                l_f = f.lower()
                if "proxima" in l_f and "soft" in l_f:
                    if any(bad in l_f for bad in ['italic', ' it.', ' it ', 'light', ' lt', 'bold', 'semibold', 'medium', ' thin']): continue
                    if l_f.endswith('it.otf') or l_f.endswith('it.ttf'): continue
                    try:
                        self.font_hd = ImageFont.truetype(os.path.join(d, f), 34 * self.sf)
                        font_found = True; break
                    except: continue
            if font_found: break

        if not self.font_hd:
            try: self.font_hd = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 34 * self.sf)
            except: self.font_hd = ImageFont.load_default()

    def get_shape_coords_hd(self, shape_type, cx, cy, r, rotation=0):
        pts = []
        if shape_type == 'circle': return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == 'square': adj = r * 0.90; pts = [(cx-adj, cy-adj), (cx+adj, cy-adj), (cx+adj, cy+adj), (cx-adj, cy+adj)]
        elif shape_type == 'triangle': pts = [(cx + r * math.cos(math.radians(-90 + i * 120)), cy + r * math.sin(math.radians(-90 + i * 120))) for i in range(3)]
        elif shape_type == 'arrow': pts = [(cx + r, cy), (cx - r, cy - r), (cx - r * 0.4, cy), (cx - r, cy + r)]
        elif shape_type == 'star': pts = [(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + i * 36)), cy + (r if i % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + i * 36))) for i in range(10)]
        elif shape_type == 'pentagon': pts = [(cx + r * math.cos(math.radians(-90 + i * 72)), cy + r * math.sin(math.radians(-90 + i * 72))) for i in range(5)]
        elif shape_type == 'hexagon': pts = [(cx + r * math.cos(math.radians(-90 + i*60)), cy + r * math.sin(math.radians(-90 + i*60))) for i in range(6)]

        if rotation != 0:
            rad = math.radians(rotation)
            pts = [(cx + (px-cx)*math.cos(rad) - (py-cy)*math.sin(rad), cy + (px-cx)*math.sin(rad) + (py-cy)*math.cos(rad)) for px, py in pts]

        return pts

    def draw_pattern_hd(self, draw, fill_data, size):
        sf, category, variant = self.sf, fill_data[0], fill_data[1]
        if category == 'solid':
            draw.rectangle([0, 0, size, size], fill=variant)
            return
        if category == 'tiling':
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
                        draw.rectangle([x, y, x + bs, y + bs], outline="black", width=1*sf)
        elif category == 'wavy':
            for i in range(-size, size*2, 15*sf):
                pts = [(i+math.sin(j*0.05)*(5*sf), j) if variant == 'wavy_v' else (j, i+math.sin(j*0.05)*(5*sf)) for j in range(0, size+10, 4*sf)]
                if len(pts) > 1: draw.line(pts, fill="black", width=2*sf)
        elif category == 'lines':
            for li in range(-size, size*2, 14*sf):
                if variant == 'vertical': draw.line([(li, 0), (li, size)], fill="black", width=2*sf)
                elif variant == 'diagonal_tl_br': draw.line([(li, 0), (li+size, size)], fill="black", width=2*sf)
                else: draw.line([(li, 0), (li-size, size)], fill="black", width=2*sf)
        elif category == 'grids':
            if variant == 'tilted_diamond':
                for gi in range(-size, size*2, 16*sf):
                    draw.line([(gi, 0), (gi-size, size)], fill="black", width=2*sf)
                    draw.line([(gi-size, 0), (gi, size)], fill="black", width=2*sf)
            else:
                for gx in range(0, size+10*sf, 22*sf): draw.line([(gx, 0), (gx, size)], fill="black", width=2*sf)
                for gy in range(0, size+10*sf, 22*sf): draw.line([(0, gy), (size, gy)], fill="black", width=2*sf)

    def _draw_masked_obj(self, canvas, shape, pattern, cx, cy, r, rotation=0):
        size = int(r * 3.0) 
        buf = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        mask = Image.new('L', (size, size), 0)
        self.draw_pattern_hd(ImageDraw.Draw(buf), pattern, size)
        loc_pts = self.get_shape_coords_hd(shape, size // 2, size // 2, r, rotation)
        glob_pts = self.get_shape_coords_hd(shape, cx, cy, r, rotation)
        draw = ImageDraw.Draw(canvas)
        weight_hd = int(2.5 * self.sf)

        if shape == 'circle':
            draw.ellipse(glob_pts, fill="white", outline="black", width=weight_hd)
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight_hd)
        else:
            closed_glob = glob_pts + [glob_pts[0], glob_pts[1]]
            draw.line(closed_glob, fill="black", width=weight_hd * 2, joint="curve")
            draw.polygon(glob_pts, fill="white")
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size // 2), int(cy - size // 2)), mask)
            draw.line(closed_glob, fill="black", width=weight_hd, joint="curve")

    def _get_pattern(self, sequence):
        """Converts a sequence into a canonical numerical pattern to check for collisions."""
        seen = {}
        pattern = []
        for item in sequence:
            item_str = str(item) 
            if item_str not in seen:
                seen[item_str] = len(seen)
            pattern.append(seen[item_str])
        return tuple(pattern)
    
    def generate_puzzle_set(self, version):
        all_vars = [
            'left_sh', 'left_pt', 'left_or', 'left_sp',           
            'mid_rc', 'mid_rd',                           
            'rtop_sh', 'rtop_pt', 'rtop_or', 'rtop_pos', 'rtop_sp', 
            'rbot_sh', 'rbot_pt', 'rbot_or', 'rbot_pos', 'rbot_sp'  
        ]
        
        num_coded = max(2, min(3, (version // 8) + 1)) 
        num_noise = min(3, version % 4)

        if num_coded == 1 and num_noise == 0:
            num_noise = 1

        # --- STRICT VARIABLE SELECTION & RELIEF VALVE ---
        target_noise_count = num_noise
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

            if any('or' in v for v in active_vars) and any('sp' in v for v in active_vars):
                continue
                
            invalid_shape_or = False
            for el in ['left', 'rtop', 'rbot']:
                if f"{el}_or" in active_vars and f"{el}_sh" in active_vars:
                    invalid_shape_or = True
            if invalid_shape_or:
                continue
                
            valid_vars = True

        fixed_vars = [v for v in all_vars if v not in active_vars]

        def get_rand_v(v):
            element = v.split('_')[0]
            if 'sh' in v:
                if f"{element}_or" in coded_vars or f"{element}_or" in noise_vars or f"{element}_sp" in coded_vars or f"{element}_sp" in noise_vars: return random.choice(self.rotatable_shapes)
                return random.choice(self.all_shapes)
            if 'pt' in v: 
                cat = random.choice(list(self.shading_categories.keys()))
                return (cat, random.choice(self.shading_categories[cat]))
            if 'or' in v: return random.choice([0, 90, 180, 270])
            if 'rc' in v: return random.choice([1, 2, 3])
            if 'rtop_pos' in v: return random.choice([-70, -45, -20])
            if 'rbot_pos' in v: return random.choice([20, 45, 70]) 
            if 'sp' in v: return random.choice(['static', 'cw', 'ccw'])
            if 'rd' in v: return random.choice(['static', 'up', 'down'])
            return 0

        master_valid = False
        master_attempts = 0
        
        while not master_valid:
            master_attempts += 1
            if master_attempts > 500: 
                if num_noise > 0: 
                    num_noise -= 1
                master_attempts = 0
                noise_vars = noise_vars[:num_noise]
                active_vars = coded_vars + noise_vars
                fixed_vars = [v for v in all_vars if v not in active_vars]

            label_sets = [['A','B','C'], ['X','Y','Z'], ['1','2','3'], ['P','Q','R']][:num_coded]
            trans, mapping_str = {}, []
            fixed_vals = {v: get_rand_v(v) for v in fixed_vars}

            for i, var in enumerate(coded_vars):
                element = var.split('_')[0]
                if 'sh' in var:
                    pool = self.rotatable_shapes if (f"{element}_or" in active_vars or f"{element}_sp" in active_vars) else self.all_shapes
                elif 'pt' in var: pool = [(c, v) for c in self.shading_categories for v in self.shading_categories[c]]
                elif 'or' in var: pool = [0, 90, 180, 270]
                elif 'rc' in var: pool = [1, 2, 3]
                elif 'rtop_pos' in var: pool = [-70, -45, -20]
                elif 'rbot_pos' in var: pool = [20, 45, 70]
                elif 'sp' in var: pool = ['static', 'cw', 'ccw']
                else: pool = ['static', 'up', 'down']
                
                states = random.sample(pool, 3) 
                for label, state in zip(label_sets[i], states): 
                    trans[label] = state
                    mapping_str.append(f"{label}={state}")

            all_possible_codes = ["".join(c) for c in itertools.product(*label_sets)]
            solvable = False
            inner_attempts = 0
            
            while not solvable and inner_attempts < 100:
                inner_attempts += 1
                chosen_codes = random.sample(all_possible_codes, 5)
                target_code, clue_codes = chosen_codes[0], chosen_codes[1:]
                
                target_visible = True
                for i in range(num_coded):
                    chars_in_clues = [clue[i] for clue in clue_codes]
                    if target_code[i] not in chars_in_clues:
                        target_visible = False
                        break
                
                if not target_visible: continue

                if any(len(set(clue[i] for clue in clue_codes)) < 2 for i in range(num_coded)): 
                    continue

                clue_noises = [{v: get_rand_v(v) for v in noise_vars} for _ in range(4)]
                target_noise = {v: get_rand_v(v) for v in noise_vars}
                
                # --- FALSE CORRELATION SAFEGUARD ---
                false_correlation = False
                for n_var in noise_vars:
                    noise_seq = [clue_noises[c_idx][n_var] for c_idx in range(4)]
                    noise_pat = self._get_pattern(noise_seq)
                    
                    for i in range(num_coded):
                        code_seq = [clue_codes[c_idx][i] for c_idx in range(4)]
                        code_pat = self._get_pattern(code_seq)
                        
                        if noise_pat == code_pat:
                            false_correlation = True
                            break
                    if false_correlation: break
                
                if false_correlation: continue
                
                # -----------------------------------
                
                target_state = {**fixed_vals, **target_noise}
                for i, char in enumerate(target_code): target_state[coded_vars[i]] = trans[char]

                clue_states_list = []
                for c_idx in range(4):
                    s = {**fixed_vals, **clue_noises[c_idx]}
                    for i, char in enumerate(clue_codes[c_idx]): s[coded_vars[i]] = trans[char]
                    clue_states_list.append(s)

                all_states = clue_states_list + [target_state]
                if len(set(frozenset(d.items()) for d in all_states)) == 5:
                    solvable = True
                    master_valid = True

        def render_frame(frame_num, state_dict, cx, cy, canvas, txt_code):
            linear_phase = frame_num / self.num_frames
            p = state_dict 
            draw = ImageDraw.Draw(canvas)
            
            box_r = 110 * self.sf
            draw.rectangle([cx - box_r, cy - box_r, cx + box_r, cy + box_r], outline="black", width=3*self.sf)

            def get_spin_angle(base_or, spin_dir):
                if spin_dir == 'cw': return base_or + (linear_phase * 360)
                if spin_dir == 'ccw': return base_or - (linear_phase * 360)
                return base_or

            l_x = cx - 70 * self.sf
            l_rot = get_spin_angle(p['left_or'], p['left_sp'])
            for offset in [-65, 0, 65]:
                self._draw_masked_obj(canvas, p['left_sh'], p['left_pt'], l_x, cy + (offset*self.sf), self.left_r_hd, l_rot)

            m_x = cx - 10 * self.sf
            rail_gap, max_y = 12 * self.sf, 85 * self.sf
            draw.line([(m_x - rail_gap, cy - max_y), (m_x - rail_gap, cy + max_y)], fill="black", width=3*self.sf)
            draw.line([(m_x + rail_gap, cy - max_y), (m_x + rail_gap, cy + max_y)], fill="black", width=3*self.sf)
            
            rung_spacing = 30 * self.sf
            r_count = p['mid_rc']
            ladder_h = max_y * 2
            
            shift = (linear_phase * ladder_h) if p['mid_rd'] == 'down' else (-linear_phase * ladder_h) if p['mid_rd'] == 'up' else 0
            group_y = cy + shift
            
            def draw_rung_group(center_y):
                start_y = center_y - ((r_count - 1) * (rung_spacing / 2))
                for i in range(r_count):
                    ry = start_y + (i * rung_spacing)
                    if (cy - max_y) <= ry <= (cy + max_y):
                        draw.line([(m_x - rail_gap, ry), (m_x + rail_gap, ry)], fill="black", width=3*self.sf)

            draw_rung_group(group_y)
            draw_rung_group(group_y - ladder_h)
            draw_rung_group(group_y + ladder_h)

            r_x = cx + 60 * self.sf
            r1_rot = get_spin_angle(p['rtop_or'], p['rtop_sp'])
            r2_rot = get_spin_angle(p['rbot_or'], p['rbot_sp'])
            self._draw_masked_obj(canvas, p['rtop_sh'], p['rtop_pt'], r_x, cy + (p['rtop_pos'] * self.sf), self.right_r_hd, r1_rot)
            self._draw_masked_obj(canvas, p['rbot_sh'], p['rbot_pt'], r_x, cy + (p['rbot_pos'] * self.sf), self.right_r_hd, r2_rot)

            bbox = draw.textbbox((0, 0), txt_code, font=self.font_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, cy + box_r + 20*self.sf), txt_code, font=self.font_hd, fill="black")

        clue_frames = []
        for f in range(self.num_frames):
            strip = Image.new('RGB', (self.strip_w_hd, self.strip_h_hd), 'white')
            for i, code in enumerate(clue_codes):
                bx_cx = 120 * self.sf + i*(self.cell_size_hd+self.spacing_hd)+self.cell_size_hd//2
                render_frame(f, clue_states_list[i], bx_cx, self.cell_size_hd//2+80*self.sf, strip, code)
            
            if f == 0:
                strip_diff = ImageOps.invert(strip.convert("RGB")).getbbox()
                crop_box = (max(0, strip_diff[0]-10), max(0, strip_diff[1]-10), min(strip.width, strip_diff[2]+10), min(strip.height, strip_diff[3]+10))
            clue_frames.append(strip.crop(crop_box))

        target_frames = []
        for f in range(self.num_frames):
            target_img = Image.new('RGB', (self.cell_size_hd+150*self.sf, self.strip_h_hd), 'white')
            txt = "?" * len(target_code)
            render_frame(f, target_state, target_img.width//2, self.cell_size_hd//2+80*self.sf, target_img, txt)
            
            if f == 0:
                t_diff = ImageOps.invert(target_img.convert("RGB")).getbbox()
                t_crop = target_img.crop(t_diff)
                t_canvas_box = (t_crop.width, t_crop.height)
            
            canvas_target = Image.new('RGB', (crop_box[2]-crop_box[0], crop_box[3]-crop_box[1]), 'white')
            canvas_target.paste(target_img.crop(t_diff), ((canvas_target.width - t_canvas_box[0]) // 2, (canvas_target.height - t_canvas_box[1]) // 2))
            target_frames.append(canvas_target)

        return {
            "Version": version if num_noise == target_noise_count else f"{version} (Downgraded)",
            "Coded_Count": num_coded,
            "Noise_Count": num_noise,
            "Answer": target_code, 
            "Signal": "|".join(coded_vars), 
            "Noise": "|".join(noise_vars),
            "Fixed": "|".join(fixed_vars),
            "Mappings": "; ".join(mapping_str),
            "Frames": (clue_frames, target_frames)
        }

if __name__ == "__main__":
    gen = NVRAnimatedMatrixGenerator()
    how_many = int(input("How many puzzle GIFs to generate? ") or 1)
    print("\nEnter a version (0-30) or leave blank for Random.")
    mode = input("Choice: ").lower() or "random"
    
    # Ensure Temp Folder exists
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    metadata_list = []

    print("\n--- Phase 1: Generating and caching to temp directory ---")
    for i in range(how_many):
        v = random.randint(0, 30) if mode == "random" else int(mode)
        
        # 1. Generate frames in memory
        data = gen.generate_puzzle_set(v)
        clue_frames, target_frames = data.pop("Frames")
        
        # 2. Setup a unique temporary folder
        temp_id = f"temp_{uuid.uuid4().hex[:8]}"
        temp_dir = os.path.join(TEMP_FOLDER, temp_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 3. Immediately save GIFs to clear them from RAM
        clue_frames[0].resize((clue_frames[0].width // gen.sf, clue_frames[0].height // gen.sf), Image.Resampling.LANCZOS).save(
            os.path.join(temp_dir, "Clues.gif"),
            save_all=True, append_images=[f.resize((f.width // gen.sf, f.height // gen.sf), Image.Resampling.LANCZOS) for f in clue_frames[1:]],
            duration=gen.frame_duration, loop=0
        )
        
        target_frames[0].resize((target_frames[0].width // gen.sf, target_frames[0].height // gen.sf), Image.Resampling.LANCZOS).save(
            os.path.join(temp_dir, "Target.gif"),
            save_all=True, append_images=[f.resize((f.width // gen.sf, f.height // gen.sf), Image.Resampling.LANCZOS) for f in target_frames[1:]],
            duration=gen.frame_duration, loop=0
        )

        # 4. Clear frame lists to explicitly free memory
        del clue_frames
        del target_frames
        
        # 5. Store metadata and temp location for Phase 2
        data["_temp_dir"] = temp_dir
        metadata_list.append(data)
        
        print(f"Generated {i+1}/{how_many} [Staged in {temp_id}]")

    print("\n--- Phase 2: Sorting, Renaming, and Finalizing ---")
    
    # Sort metadata by Version (Difficulty). 
    # Extract the base integer in case it says "15 (Downgraded)"
    def get_difficulty(item):
        v_str = str(item["Version"]).split()[0]
        return int(v_str)
        
    metadata_list.sort(key=get_difficulty)

    # Calculate Starting Set_ID to avoid overwrite conflicts
    manifest_path = os.path.join(OUTPUT_FOLDER, "manifest.csv")
    file_exists = os.path.exists(manifest_path)
    start_id = 1
    
    if file_exists:
        try:
            with open(manifest_path, "r", newline="") as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1].strip()
                    if last_line:
                        start_id = int(last_line.split(',')[0]) + 1
        except Exception:
            pass

    # Move files and build the manifest
    manifest = []
    for idx_offset, data in enumerate(metadata_list):
        idx = start_id + idx_offset
        temp_dir = data.pop("_temp_dir") # Remove tracking key before writing to CSV
        
        # Determine final folder name
        final_dir_name = f"Set_{idx}_V{data['Version']}"
        final_dir = os.path.join(OUTPUT_FOLDER, final_dir_name)
        
        # Move the temporary folder to the final location with its new sorted ID
        shutil.move(temp_dir, final_dir)
        
        # Prepare CSV row
        row = {"Set_ID": idx}
        row.update(data)
        manifest.append(row)

    # Append to manifest
    if manifest:
        with open(manifest_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=manifest[0].keys())
            if not file_exists:
                writer.writeheader()
            writer.writerows(manifest)
            
    # Cleanup empty temporary directory
    shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
            
    print(f"\nGIF Production Complete. {how_many} sets ordered and saved in {OUTPUT_FOLDER}")