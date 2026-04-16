import random
import os
import math
import csv
import itertools
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Configuration ---
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_codes_version_f")

MAC_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental"
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

class NVRProfessionalGenerator:
    def __init__(self):
        # Variables Matrix - Rotation swapped for independent Base Shape and Segmentation
        self.variables = {
            'base_shape': {
                'pool': ['circle', 'square', 'hexagon', 'triangle'],
                'clp': 2 
            },
            'segmentation': {
                'pool': [2, 3, 4, 6],
                'clp': 3
            },
            'palette': {
                'pool': [('grey', 'dots'), ('grey', 'crosshatch'), ('black', 'dots'), ('black', 'crosshatch'), ('white', 'dots'), ('black', 'white')],
                'clp': 2
            },
            'container': {
                'pool': ['circle', 'square', 'none'],
                'clp': 1
            }
        }
        
        self.sf = 4 
        self.cell_size = 220 * self.sf
        self.spacing = 65 * self.sf
        self.strip_w = (self.cell_size * 4) + (self.spacing * 3) + (350 * self.sf)
        self.strip_h = self.cell_size + (250 * self.sf) 
        self.base_r = 85 * self.sf   

        # Font Loader
        self.font = None
        print("Searching for Proxima Soft...")
        for d in MAC_FONT_DIRS:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                l_f = f.lower()
                if "proxima" in l_f and "soft" in l_f:
                    forbidden = ['italic', ' it.', ' it ', 'light', ' lt', 'bold', 'semibold', 'medium', ' thin']
                    if any(bad in l_f for bad in forbidden): continue
                    if l_f.endswith('it.otf') or l_f.endswith('it.ttf'): continue
                    try:
                        self.font = ImageFont.truetype(os.path.join(d, f), 36 * self.sf)
                        print(f"SUCCESS: Loaded {f}")
                        break
                    except: pass
            if self.font: break
            
        if not self.font:
            print("Proxima Soft not found. Attempting generic Mac fallback...")
            fallbacks = ["Arial.ttf", "Helvetica.ttf", "SFNS.ttf"]
            for d in MAC_FONT_DIRS:
                for fb in fallbacks:
                    try:
                        self.font = ImageFont.truetype(os.path.join(d, fb), 36 * self.sf)
                        print(f"SUCCESS: Fallback loaded {fb}")
                        break
                    except: pass
                if self.font: break
                
        if not self.font:
            print("No suitable font found, labels will be tiny!")
            self.font = ImageFont.load_default()

    def get_shape_polygon(self, shape_type, cx, cy, base_r):
        """Generates normalized polygons so all shapes share a consistent visual bounding box."""
        pts = []
        if shape_type == 'circle':
            for i in range(120): # High poly count for smooth masking
                a = math.radians(i * 3)
                pts.append((cx + base_r * math.cos(a), cy + base_r * math.sin(a)))
        elif shape_type == 'square':
            s = base_r * 0.9 # Increased slightly so it sits flush with the visual weight of the circle
            pts = [(cx-s, cy-s), (cx+s, cy-s), (cx+s, cy+s), (cx-s, cy+s)]
        elif shape_type == 'hexagon':
            hr = base_r * 1.0 # Reduced from 1.1 to exactly match the circle's radius
            for i in range(6):
                a = math.radians(-90 + i * 60)
                pts.append((cx + hr * math.cos(a), cy + hr * math.sin(a)))
        elif shape_type == 'triangle':
            tr = base_r * 1.25 
            # Calculate the offset needed to visually center the bounding box
            y_offset = tr * 0.25 
            for i in range(3):
                a = math.radians(-90 + i * 120)
                # Apply the y_offset to pull the triangle down
                pts.append((cx + tr * math.cos(a), cy + tr * math.sin(a) + y_offset))
        return pts

    def _create_pattern_layer(self, fill_type, size, sf):
        """Renders specific pattern logic onto an RGBA buffer."""
        layer = Image.new('RGBA', (size, size), (255, 255, 255, 255))
        if fill_type in ['black', 'grey', 'white']:
            # UPDATED: 'black' is now a dark charcoal, 'grey' is lighter for contrast against the charcoal
            color = {'black': (55, 55, 55, 255), 'grey': (215, 215, 215, 255), 'white': (255, 255, 255, 255)}[fill_type]
            return Image.new('RGBA', (size, size), color)
            
        pat_draw = ImageDraw.Draw(layer)
        if fill_type == 'dots':
            for px in range(0, size, 14*sf):
                for py in range(0, size, 14*sf):
                    pat_draw.ellipse([px, py, px+4*sf, py+4*sf], fill='black')
        elif fill_type == 'crosshatch':
            for px in range(-size, size*2, 18*sf):
                pat_draw.line([(px, 0), (px+size, size)], fill='black', width=int(1.5*sf))
                pat_draw.line([(px+size, 0), (px, size)], fill='black', width=int(1.5*sf))
        return layer

    def render_element(self, canvas, cx, cy, state, label, is_target):
        draw = ImageDraw.Draw(canvas)
        r = self.base_r
        sf = self.sf
        line_w = int(2.5 * sf) 
        
        # 1. Draw Container (Expanded to clear the normalized triangle points)
        cont = state.get('container', 'none')
        if cont == 'circle':
            draw.ellipse([cx - r*1.6, cy - r*1.6, cx + r*1.6, cy + r*1.6], outline="black", width=line_w)
        elif cont == 'square':
            draw.rectangle([cx - r*1.5, cy - r*1.5, cx + r*1.5, cy + r*1.5], outline="black", width=line_w)

        # 2. Get normalized shape polygon boundaries
        shape_type = state['base_shape']
        shape_poly = self.get_shape_polygon(shape_type, cx, cy, r)
        
        # 3. Setup Masking Sandbox
        size = int(r * 4)
        local_cx, local_cy = size // 2, size // 2
        
        num_segs = state['segmentation']
        fill_1, fill_2 = state['palette']
        
        fills_layer = Image.new('RGBA', (size, size), (0,0,0,0))
        lines_layer = Image.new('RGBA', (size, size), (0,0,0,0))
        lines_draw = ImageDraw.Draw(lines_layer)

        # 4. Draw Cookie-Cutter Segment Wedges
        for i in range(num_segs):
            start_ang = -90 + i * (360 / num_segs)
            end_ang = -90 + (i + 1) * (360 / num_segs)
            
            fill_type = fill_1 if i % 2 == 0 else fill_2
            pat_layer = self._create_pattern_layer(fill_type, size, sf)
            
            slice_mask = Image.new('L', (size, size), 0)
            ImageDraw.Draw(slice_mask).pieslice([0, 0, size, size], start_ang, end_ang, fill=255)
            
            fills_layer.paste(pat_layer, (0, 0), slice_mask)
            
            # Draw precise dividing lines from center out past the edges
            rad = math.radians(start_ang)
            end_x = local_cx + (size) * math.cos(rad)
            end_y = local_cy + (size) * math.sin(rad)
            lines_draw.line([(local_cx, local_cy), (end_x, end_y)], fill="black", width=line_w)

        # Merge wedges and lines together
        content_layer = Image.alpha_composite(fills_layer, lines_layer)

        # 5. Punch out the content using the Shape Mask
        shape_mask = Image.new('L', (size, size), 0)
        local_shape_poly = [(px - cx + local_cx, py - cy + local_cy) for px, py in shape_poly]
        ImageDraw.Draw(shape_mask).polygon(local_shape_poly, fill=255)
        
        canvas.paste(content_layer, (int(cx - local_cx), int(cy - local_cy)), shape_mask)

        # 6. Draw the crisp outer border over the edges to seal it
        if shape_type == 'circle':
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=line_w)
        else:
            closed_poly = shape_poly + [shape_poly[0]]
            draw.line(closed_poly, fill="black", width=line_w, joint="curve")

        # 7. Draw Label
        txt = "?" * len(label) if is_target else label
        bbox = draw.textbbox((0, 0), txt, font=self.font)
        draw.text((cx - (bbox[2]-bbox[0])//2, cy + int(r * 1.8) + 20*sf), txt, font=self.font, fill="black")

    def generate_puzzle(self, num_codes):
        all_vars = list(self.variables.keys())
        coded_vars = random.sample(all_vars, num_codes)
        
        # Ensure visually heavy elements are prioritized if random selection misses them
        if 'base_shape' not in coded_vars and 'segmentation' not in coded_vars:
            coded_vars[0] = 'segmentation'

        remaining_vars = [v for v in all_vars if v not in coded_vars]
        num_noise = random.randint(1, min(2, len(remaining_vars)))
        noise_vars = random.sample(remaining_vars, num_noise)
        fixed_vars = [v for v in remaining_vars if v not in noise_vars]

        active_states = {}
        trans = {}
        mapping_str = []
        label_sets = []
        master_label_pools = [['A', 'B', 'C'], ['X', 'Y', 'Z'], ['1', '2', '3']]
        
        for idx, var in enumerate(coded_vars):
            states = random.sample(self.variables[var]['pool'], 3)
            active_states[var] = states
            lbls = master_label_pools[idx] 
            label_sets.append(lbls)
            for i, char in enumerate(lbls):
                trans[char] = states[i]
                mapping_str.append(f"{char}={states[i]}")

        for var in noise_vars:
            active_states[var] = random.sample(self.variables[var]['pool'], 2)
            
        fixed_states = {v: random.choice(self.variables[v]['pool']) for v in fixed_vars}

        all_possible_codes = ["".join(c) for c in itertools.product(*label_sets)]
        target_code = random.choice(all_possible_codes)
        remaining = [c for c in all_possible_codes if c != target_code]
        
        # --- Strict Solvability Engine & Relief Valve ---
        solvable = False
        attempts = 0
        
        while not solvable:
            attempts += 1
            if attempts > 200:
                # If we get mathematically stuck, pick a brand new target code and try again
                target_code = random.choice(all_possible_codes)
                remaining = [c for c in all_possible_codes if c != target_code]
                attempts = 0
                
            clue_codes = random.sample(remaining, 4)
            
            # Check 1: Strict Positional Target Presence
            valid_target_presence = True
            for i, char in enumerate(target_code):
                if not any(clue[i] == char for clue in clue_codes):
                    valid_target_presence = False
                    break
            if not valid_target_presence:
                continue
                
            # Check 2: Deductive Logic Check
            if any(len(set(code[i] for code in clue_codes)) == 1 for i in range(num_codes)):
                continue

            clue_states_list = []
            for code in clue_codes:
                s = fixed_states.copy()
                for i, char in enumerate(code):
                    s[coded_vars[i]] = trans[char]
                for nv in noise_vars:
                    s[nv] = random.choice(active_states[nv])
                clue_states_list.append(s)

            target_state_dict = fixed_states.copy()
            for i, char in enumerate(target_code):
                target_state_dict[coded_vars[i]] = trans[char]
            for nv in noise_vars:
                target_state_dict[nv] = random.choice(active_states[nv])

            all_states = clue_states_list + [target_state_dict]
            unique_states = set(frozenset(d.items()) for d in all_states)
            
            if len(unique_states) == 5:
                clue_states = clue_states_list
                target_state = target_state_dict
                solvable = True

        clp_score = sum(self.variables[v]['clp'] for v in coded_vars)
        clp_score += sum(self.variables[v]['clp'] for v in noise_vars)
        clp_score += 2 if num_codes == 2 else 5

        strip = Image.new('RGB', (self.strip_w, self.strip_h), 'white')
        target_img = Image.new('RGB', (self.cell_size+100*self.sf, self.strip_h), 'white')
        
        for i, code in enumerate(clue_codes):
            self.render_element(strip, 180*self.sf + i*(self.cell_size+self.spacing), self.cell_size//2+50*self.sf, clue_states[i], code, False)
        
        self.render_element(target_img, target_img.width//2, self.cell_size//2+50*self.sf, target_state, target_code, True)

        sd = ImageOps.invert(strip).getbbox()
        td = ImageOps.invert(target_img).getbbox()
        
        if sd and td:
            # 1. Find the shared maximum vertical boundaries across BOTH images
            shared_top = min(sd[1], td[1])
            shared_bottom = max(sd[3], td[3])
            
            standard_padding = 20
            # INCREASE THIS NUMBER to shrink the shape in your CMS!
            target_h_padding = 1700
            
            top_crop = max(0, shared_top - standard_padding)
            bottom_crop = shared_bottom + standard_padding
            
            # 2. Crop the Clues strip normally
            strip = strip.crop((
                max(0, sd[0] - standard_padding), 
                top_crop, 
                min(strip.width, sd[2] + standard_padding), 
                min(strip.height, bottom_crop)
            ))
            
            # 3. Crop the Target image perfectly tight on the left and right...
            target_img = target_img.crop((
                td[0], 
                top_crop, 
                td[2], 
                min(target_img.height, bottom_crop)
            ))
            
            # 4. ...and then force the creation of brand new white space on the sides.
            target_img = ImageOps.expand(target_img, border=(target_h_padding, 0, target_h_padding, 0), fill='white')

        return {
            "CLP_Difficulty": clp_score,
            "Coded_Length": num_codes,
            "Answer": target_code,
            "Signal": "|".join(coded_vars),
            "Noise": "|".join(noise_vars),
            "Fixed": "|".join(fixed_vars),
            "Mappings": "; ".join(mapping_str),
            "Images": (strip, target_img)
        }

if __name__ == "__main__":
    gen = NVRProfessionalGenerator()
    num = int(input("How many puzzles to generate? ") or 1)
    results = []
    
    for i in range(num):
        print(f"Generating Puzzle {i+1}...")
        num_codes = random.choice([2, 3])
        data = gen.generate_puzzle(num_codes)
        
        strip_img, target_img = data.pop("Images")
        temp_dir = os.path.join(OUTPUT_FOLDER, f"Set_{i+1}_CLP_{data['CLP_Difficulty']}")
        os.makedirs(temp_dir, exist_ok=True)
        
        s_resized = strip_img.resize((strip_img.width//gen.sf, strip_img.height//gen.sf), Image.LANCZOS)
        t_resized = target_img.resize((target_img.width//gen.sf, target_img.height//gen.sf), Image.LANCZOS)
        
        s_resized.save(os.path.join(temp_dir, "Clues.png"))
        t_resized.save(os.path.join(temp_dir, "Target.png"))
        
        data["Set_ID"] = i + 1
        results.append(data)

    results.sort(key=lambda x: x["CLP_Difficulty"])

    with open(os.path.join(OUTPUT_FOLDER, "manifest.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
    print(f"\nComplete. Files located in: {OUTPUT_FOLDER}")