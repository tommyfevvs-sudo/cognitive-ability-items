import random
import os
import math
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Configuration ---
DESKTOP_PATH = os.path.join(Path.home(), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_codes_a")

# Mac stores fonts in a few different libraries, so we use a list
FONT_DIRS = [
    "/Library/Fonts",
    os.path.join(Path.home(), "Library/Fonts"),
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental"
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

class NVRGenerator:
    def __init__(self):
        # 1. Feature Decks: Shapes (Expanded to maximize variety)
        self.all_shapes = ['circle', 'square', 'pentagon', 'triangle', 'hexagon', 'arrow', 'star', 'cross_shape']
        
        # 2. Feature Decks: Backgrounds
        self.bg_categories = {
            'original': ['cross', 'plus', 'star'],
            'orbits': ['single_ring', 'double_ring', 'satellites'],
            'spines': ['tri_spine', 'compass', 'clock_six'],
            'frames': ['corners', 'brackets', 'diamond_frame']
        }

        # 3. Feature Decks: Shading Pools
        self.arrow_variants = ['up', 'down', 'left', 'right']
        self.line_variants = ['vertical', 'diagonal_tl_br', 'diagonal_tr_bl']
        self.grid_variants = ['standard_large', 'standard_small', 'tilted_diamond']
        self.darkness_variants = ['white', 'grey', 'black']
        self.wavy_variants = ['wavy_v', 'wavy_h', 'wavy_d']
        self.mini_tri_variants = ['tri_up', 'tri_down', 'tri_left', 'tri_right']
        self.legacy_variants = ['dots', 'solid_grey', 'up_arrows_legacy', 'hatched']

        self.shading_categories = {
            'arrows': self.arrow_variants,
            'lines': self.line_variants,
            'grids': self.grid_variants,
            'darkness': self.darkness_variants,
            'wavy': self.wavy_variants,
            'mini_tri': self.mini_tri_variants,
            'legacy': self.legacy_variants
        }
        
        # Base Grid and Layout Constants
        self.cell_size = 200
        self.shape_r = 60
        self.spacing = 35
        self.sf = 4 # Super-Sampling
        
        self.cell_size_hd = self.cell_size * self.sf
        self.shape_r_hd = self.shape_r * self.sf
        self.spacing_hd = self.spacing * self.sf
        
        self.strip_w_hd = (self.cell_size_hd * 4) + (self.spacing_hd * 3) + (120 * self.sf)
        self.strip_h_hd = self.cell_size_hd + (220 * self.sf) 

        # Proxima Font Support
        self.font_hd = None
        try:
            for font_dir in FONT_DIRS:
                if not os.path.exists(font_dir):
                    continue
                available_fonts = os.listdir(font_dir)
                for f in available_fonts:
                    name = f.lower()
                    
                    # 1. Must have "proxima" and "soft"
                    if "proxima" in name and "soft" in name:
                        # 2. Must NOT have any bold or italic identifiers (including shorthand)
                        bad_words = ["bold", "-bd", "bd.", "italic", "ital", "-it", "it."]
                        if not any(bad in name for bad in bad_words):
                            # 3. Must be a valid font file
                            if f.endswith(".ttf") or f.endswith(".otf"):
                                target_font_path = os.path.join(font_dir, f)
                                self.font_hd = ImageFont.truetype(target_font_path, 28 * self.sf)
                                break # Found it, break out of the inner loop
                
                if self.font_hd is not None:
                    break # Found it, break out of the outer directory loop
        except Exception:
            pass
            
        if self.font_hd is None:
            self.font_hd = ImageFont.load_default()

    def draw_background_hd(self, draw, bg_data, cx, cy):
        """EXPLICIT LONG-FORM COORDINATES RESTORED FOR ALL 12 VARIANTS"""
        if bg_data == 'hidden':
            return cy 

        category, variant = bg_data
        r = 85 * self.sf 
        line_w = 2 * self.sf
        color = "#BBBBBB"
        lowest_bg_y_val = cy + r
        
        if category == 'original':
            if variant == 'cross':
                x1_start_x, x1_start_y = cx - r, cy - r
                x1_end_x, x1_end_y = cx + r, cy + r
                draw.line([(x1_start_x, x1_start_y), (x1_end_x, x1_end_y)], fill=color, width=line_w)
                x2_start_x, x2_start_y = cx + r, cy - r
                x2_end_x, x2_end_y = cx - r, cy + r
                draw.line([(x2_start_x, x2_start_y), (x2_end_x, x2_end_y)], fill=color, width=line_w)
            elif variant == 'plus':
                draw.line([(cx, cy - r), (cx, cy + r)], fill=color, width=line_w)
                draw.line([(cx - r, cy), (cx + r, cy)], fill=color, width=line_w)
            elif variant == 'star':
                draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=color, width=line_w)
                draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill=color, width=line_w)
                draw.line([(cx, cy - r), (cx, cy + r)], fill=color, width=line_w)
                draw.line([(cx - r, cy), (cx + r, cy)], fill=color, width=line_w)

        elif category == 'orbits':
            if variant == 'single_ring':
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=line_w)
            elif variant == 'double_ring':
                draw.ellipse([cx - r * 1.1, cy - r * 1.1, cx + r * 1.1, cy + r * 1.1], outline=color, width=line_w)
                draw.ellipse([cx - r * 0.85, cy - r * 0.85, cx + r * 0.85, cy + r * 0.85], outline=color, width=line_w)
            elif variant == 'satellites':
                for ang in [-90, 30, 150]:
                    dx = cx + (r * 1.05) * math.cos(math.radians(ang))
                    dy = cy + (r * 1.05) * math.sin(math.radians(ang))
                    draw.ellipse([dx - 6*self.sf, dy - 6*self.sf, dx + 6*self.sf, dy + 6*self.sf], fill=color)

        elif category == 'spines':
            if variant == 'tri_spine':
                for ang in [-90, 30, 150]:
                    draw.line([(cx, cy), (cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang)))], fill=color, width=line_w)
            elif variant == 'compass':
                draw.line([(cx, cy - r), (cx, cy - r * 0.7)], fill=color, width=line_w)
                draw.line([(cx, cy + r), (cx, cy + r * 0.7)], fill=color, width=line_w)
                draw.line([(cx - r, cy), (cx - r * 0.7, cy)], fill=color, width=line_w)
                draw.line([(cx + r, cy), (cx + r * 0.7, cy)], fill=color, width=line_w)
            elif variant == 'clock_six':
                draw.line([(cx, cy), (cx, cy + r)], fill=color, width=line_w)

        elif category == 'frames':
            if variant == 'corners':
                cs = 20 * self.sf
                draw.line([(cx-r, cy-r), (cx-r+cs, cy-r)], fill=color, width=line_w)
                draw.line([(cx-r, cy-r), (cx-r, cy-r+cs)], fill=color, width=line_w)
                draw.line([(cx+r, cy-r), (cx+r-cs, cy-r)], fill=color, width=line_w)
                draw.line([(cx+r, cy-r), (cx+r, cy-r+cs)], fill=color, width=line_w)
                draw.line([(cx-r, cy+r), (cx-r+cs, cy+r)], fill=color, width=line_w)
                draw.line([(cx-r, cy+r), (cx-r, cy+r-cs)], fill=color, width=line_w)
                draw.line([(cx+r, cy+r), (cx+r-cs, cy+r)], fill=color, width=line_w)
                draw.line([(cx+r, cy+r), (cx+r, cy+r-cs)], fill=color, width=line_w)
            elif variant == 'brackets':
                draw.line([(cx - r, cy - r), (cx - r, cy + r)], fill=color, width=line_w)
                draw.line([(cx + r, cy - r), (cx + r, cy + r)], fill=color, width=line_w)
            elif variant == 'diamond_frame':
                draw.line([(cx, cy - r), (cx + r, cy)], fill=color, width=line_w)
                draw.line([(cx + r, cy), (cx, cy + r)], fill=color, width=line_w)
                draw.line([(cx, cy + r), (cx - r, cy)], fill=color, width=line_w)
                draw.line([(cx - r, cy), (cx, cy - r)], fill=color, width=line_w)
            
        return lowest_bg_y_val

    def get_shape_coords_hd(self, shape_type, cx, cy):
        """EXPLICIT VERTEX MATH RESTORED - ALL SHAPES CENTERED & EQUILATERAL"""
        r = self.shape_r_hd
        if shape_type == 'circle':
            return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == 'square':
            adj = r * 0.85
            return [(cx - adj, cy - adj), (cx + adj, cy - adj), (cx + adj, cy + adj), (cx - adj, cy + adj)]
        elif shape_type == 'triangle':
            h = r * 1.7 * 0.85
            return [(cx, cy - h/2), (cx + r, cy + h/2), (cx - r, cy + h/2)]
        elif shape_type == 'arrow':
            return [(cx, cy - r), (cx + r*0.8, cy), (cx, cy + r), (cx - r*0.8, cy)]
        elif shape_type == 'star':
            pts = []
            for i in range(10):
                ang = math.radians(-90 + i * 36)
                curr_r = r if i % 2 == 0 else r * 0.45
                pts.append((cx + curr_r * math.cos(ang), cy + curr_r * math.sin(ang)))
            return pts
        elif shape_type == 'cross_shape':
            w = r * 0.35
            return [(cx-w, cy-r), (cx+w, cy-r), (cx+w, cy-w), (cx+r, cy-w), (cx+r, cy+w), (cx+w, cy+w), (cx+w, cy+r), (cx-w, cy+r), (cx-w, cy+w), (cx-r, cy+w), (cx-r, cy-w), (cx-w, cy-w)]
        elif shape_type == 'pentagon':
            points = []
            for ang in [-90, -18, 54, 126, 198]:
                points.append((cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))))
            return points
        elif shape_type == 'hexagon':
            points = []
            for i in range(6):
                ang = math.radians(-90 + (i * 60))
                points.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            return points

    def draw_pattern_hd(self, draw, fill_data, size):
        """EXPLICIT SHADING LOOPS RESTORED"""
        sf = self.sf
        category, variant = fill_data
        
        if category == 'legacy':
            if variant == 'solid_grey':
                draw.rectangle([10*sf, 10*sf, size-10*sf, size-10*sf], fill="#A0A0A0")
            elif variant == 'dots':
                for x_l in range(20 * sf, size - 20 * sf, 15 * sf):
                    for y_l in range(20 * sf, size - 20 * sf, 15 * sf):
                        draw.ellipse([x_l, y_l, x_l + 4*sf, y_l + 4*sf], fill="black")
            elif variant == 'hatched':
                for h_i in range(-size, size * 2, 12 * sf):
                    draw.line([(h_i, 0), (h_i + size, size)], fill="black", width=1 * sf)
            elif variant == 'up_arrows_legacy':
                for ax_l in range(30 * sf, size - 30 * sf, 22 * sf):
                    for ay_l in range(30 * sf, size - 30 * sf, 22 * sf):
                        draw.line([(ax_l, ay_l + 15*sf), (ax_l, ay_l + 5*sf)], fill="black", width=2*sf)
                        draw.line([(ax_l - 3*sf, ay_l + 8*sf), (ax_l, ay_l + 5*sf)], fill="black", width=2*sf)
                        draw.line([(ax_l + 3*sf, ay_l + 8*sf), (ax_l, ay_l + 5*sf)], fill="black", width=2*sf)

        elif category == 'arrows':
            for ax in range(25 * sf, size - 15 * sf, 26 * sf):
                for ay in range(25 * sf, size - 15 * sf, 26 * sf):
                    if variant == 'up':
                        h, s, l, r_head = (ax, ay-6*sf), (ax, ay+6*sf), (ax-4*sf, ay-2*sf), (ax+4*sf, ay-2*sf)
                    elif variant == 'down':
                        h, s, l, r_head = (ax, ay+6*sf), (ax, ay-6*sf), (ax-4*sf, ay+2*sf), (ax+4*sf, ay+2*sf)
                    elif variant == 'left':
                        h, s, l, r_head = (ax-6*sf, ay), (ax+6*sf, ay), (ax-2*sf, ay-4*sf), (ax-2*sf, ay+4*sf)
                    else:
                        h, s, l, r_head = (ax+6*sf, ay), (ax-6*sf, ay), (ax+2*sf, ay-4*sf), (ax+2*sf, ay+4*sf)
                    draw.line([s, h], fill="black", width=2*sf)
                    draw.line([l, h], fill="black", width=2*sf)
                    draw.line([r_head, h], fill="black", width=2*sf)

        elif category == 'wavy':
            for i_w in range(-size, size * 2, 15 * sf):
                pts = []
                for j_w in range(0, size + 10, 4 * sf):
                    off = math.sin(j_w * 0.05) * (5 * sf)
                    if variant == 'wavy_v': pts.append((i_w + off, j_w))
                    elif variant == 'wavy_h': pts.append((j_w, i_w + off))
                    else: pts.append((i_w + j_w + off, j_w))
                if len(pts) > 1: draw.line(pts, fill="black", width=1*sf)

        elif category == 'mini_tri':
            ts, gp = 6 * sf, 22 * sf
            for tx in range(20 * sf, size - 10 * sf, gp):
                for ty in range(20 * sf, size - 10 * sf, gp):
                    if variant == 'tri_up': tri = [(tx, ty - ts), (tx + ts, ty + ts), (tx - ts, ty + ts)]
                    elif variant == 'tri_down': tri = [(tx, ty + ts), (tx + ts, ty - ts), (tx - ts, ty - ts)]
                    elif variant == 'tri_left': tri = [(tx - ts, ty), (tx + ts, ty - ts), (tx + ts, ty + ts)]
                    else: tri = [(tx + ts, ty), (tx - ts, ty - ts), (tx - ts, ty + ts)]
                    draw.polygon(tri, fill="black")

        elif category == 'lines':
            for li in range(-size, size * 2, 14 * sf):
                if variant == 'vertical': draw.line([(li, 0), (li, size)], fill="black", width=1*sf)
                elif variant == 'diagonal_tl_br': draw.line([(li, 0), (li + size, size)], fill="black", width=1*sf)
                else: draw.line([(li, 0), (li - size, size)], fill="black", width=1*sf)

        elif category == 'grids':
            gs = 16 * sf if variant == 'tilted_diamond' else (22 * sf if 'large' in variant else 10 * sf)
            if variant == 'tilted_diamond':
                for gi in range(-size, size * 2, gs):
                    draw.line([(gi, 0), (gi - size, size)], fill="black", width=1*sf)
                    draw.line([(gi - size, 0), (gi, size)], fill="black", width=1*sf)
            else:
                for gx in range(0, size + 10*sf, gs): draw.line([(gx, 0), (gx, size)], fill="black", width=1*sf)
                for gy in range(0, size + 10*sf, gs): draw.line([(0, gy), (size, gy)], fill="black", width=1*sf)

        elif category == 'darkness':
            c_fill = "#A0A0A0" if variant == 'grey' else "black"
            draw.rectangle([0, 0, size, size], fill=c_fill)

    def generate_puzzle_assets(self):
        """Generates raw assets and metadata but does NOT save yet."""
        level = random.choice([0, 1, 2, 3])
        num_diff = 1.5 + (level * 2.5)
        roles_pool = ['Shape', 'Shading', 'BG']
        random.shuffle(roles_pool)
        num_coded = 3 if level == 3 else 2
        coded_roles = roles_pool[:num_coded]
        sh_cat = random.choice(list(self.shading_categories.keys()))
        bg_cat = random.choice(list(self.bg_categories.keys()))
        decks = {
            'Shape': random.sample(self.all_shapes, 3),
            'Shading': [(sh_cat, v) for v in random.sample(self.shading_categories[sh_cat], 3)],
            'BG': [(bg_cat, v) for v in random.sample(self.bg_categories[bg_cat], 3)]
        }
        label_sets = [['A', 'B', 'C'], ['X', 'Y', 'Z'], ['1', '2', '3']]
        trans, r_map = {}, {}
        for i, role in enumerate(coded_roles):
            r_map[role] = i
            trans.update(zip(label_sets[i], decks[role]))
        target_code = "".join(random.choice(label_sets[i]) for i in range(num_coded))
        solvable = False
        while not solvable:
            clues = []
            while len(clues) < 4:
                c = "".join(random.choice(label_sets[i]) for i in range(num_coded))
                if c != target_code and c not in clues: clues.append(c)
            if all(any(clue[i] == target_code[i] for clue in clues) for i in range(num_coded)):
                solvable = True

        def get_f(role, code):
            if role in coded_roles: return trans[code[r_map[role]]]
            if level == 0: return 'hidden' if role == 'BG' else decks[role][0]
            return decks[role][0] if level == 1 else random.choice(decks[role])

        def draw_box(canvas, code, box_cx, box_cy, is_target=False):
            draw = ImageDraw.Draw(canvas)
            low_bg = self.draw_background_hd(draw, get_f('BG', code), box_cx, box_cy)
            s_type, f_data = get_f('Shape', code), get_f('Shading', code)
            if f_data == 'hidden': f_data = ('darkness', 'white')
            
            # 1. Setup Buffers
            buf = Image.new('RGBA', (self.cell_size_hd, self.cell_size_hd), (255,255,255,0))
            mask = Image.new('L', (self.cell_size_hd, self.cell_size_hd), 0)
            
            # 2. Draw the Shading Pattern
            self.draw_pattern_hd(ImageDraw.Draw(buf), f_data, self.cell_size_hd)
            
            # 3. Define the coordinates
            loc_pts = self.get_shape_coords_hd(s_type, self.cell_size_hd // 2, self.cell_size_hd // 2)
            glob_pts = self.get_shape_coords_hd(s_type, box_cx, box_cy)
            
            # --- THE FIX: ROUNDED IN/OUT CORNERS ---
            outline_w = 4 * self.sf
            
            if s_type == 'circle':
                # Circle doesn't have corners, so standard drawing works
                ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
                canvas.paste(buf, (int(box_cx - self.cell_size_hd // 2), int(box_cy - self.cell_size_hd // 2)), mask)
                draw.ellipse(glob_pts, outline="black", width=outline_w)
                low_s = glob_pts[3]
            else:
                # STEP A: Draw the "Outline" as a thick black stroke
                # THE FIX: Append the first TWO points to the end of the list.
                # This trick forces PIL to render the "joint" at the start/end point.
                closed_glob = glob_pts + [glob_pts[0], glob_pts[1]]
                
                # Draw the thick "skeleton" with the joint setting
                draw.line(closed_glob, fill="black", width=outline_w * 2, joint="curve")
                
                # Fill the center black to ensure no white gaps in the middle
                draw.polygon(glob_pts, fill="black")

                # STEP B: Prepare the mask for the pattern
                # (Same as before)
                ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
                
                # STEP C: Paste the pattern on top
                canvas.paste(buf, (int(box_cx - self.cell_size_hd // 2), int(box_cy - self.cell_size_hd // 2)), mask)
                
                low_s = max(p[1] for p in glob_pts)
            # --- END FIX ---

            txt = "?" * num_coded if is_target else code
            bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
            draw.text((box_cx - (bbox[2]-bbox[0])//2, max(low_bg, low_s) + 15 * self.sf), txt, font=self.font_hd, fill="black")

        strip = Image.new('RGB', (self.strip_w_hd, self.strip_h_hd), 'white')
        for i, code in enumerate(clues):
            bx_cx = 100 * self.sf + i * (self.cell_size_hd + self.spacing_hd) + self.cell_size_hd // 2
            draw_box(strip, code, bx_cx, self.cell_size_hd // 2 + 20 * self.sf)
        target = Image.new('RGB', (self.cell_size_hd + 800*self.sf, self.strip_h_hd), 'white')
        draw_box(target, target_code, target.width // 2, self.cell_size_hd // 2 + 20 * self.sf, True)

        return {
            'strip': strip, 'target': target, 'level': level, 'num_diff': num_diff,
            'answer': target_code, 'coded_roles': coded_roles, 'sh_cat': sh_cat, 'bg_cat': bg_cat
        }

if __name__ == "__main__":
    count = int(input("How many puzzle sets? ") or 1)
    gen = NVRGenerator()
    audit_path = os.path.join(OUTPUT_FOLDER, "audit.csv")

    batch_num = 1
    file_exists = os.path.isfile(audit_path)
    if file_exists:
        try:
            with open(audit_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                batches = [int(row['batch_number']) for row in reader if row.get('batch_number') and row['batch_number'].isdigit()]
                if batches: batch_num = max(batches) + 1
        except Exception: batch_num = 1

    temp_puzzles = [gen.generate_puzzle_assets() for _ in range(count)]
    temp_puzzles.sort(key=lambda x: x['num_diff'])

    diff_map = {1.5: "easiest", 4.0: "easy", 6.5: "hard", 9.0: "hardest"}
    final_audit = []

    for i, p_data in enumerate(temp_puzzles, 1):
        item_idx_str = f"{i:03d}"
        diff_label = diff_map.get(p_data['num_diff'], "unknown")
        folder_name = f"NVR_codes_A_{batch_num}.{item_idx_str}_diff_{diff_label}"
        puzzle_folder = os.path.join(OUTPUT_FOLDER, folder_name)
        os.makedirs(puzzle_folder, exist_ok=True)

        def save_img(img, name, t_mode=False):
            bbox = ImageOps.invert(img.convert('RGB')).getbbox()
            if bbox:
                p, hp = 10*gen.sf, (700*gen.sf if t_mode else 10*gen.sf)
                img = img.crop((max(0, bbox[0]-hp), max(0, bbox[1]-p), min(img.width, bbox[2]+hp), min(img.height, bbox[3]+p)))
            img.resize((img.width//gen.sf, img.height//gen.sf), Image.Resampling.LANCZOS).save(os.path.join(puzzle_folder, name))

        save_img(p_data['strip'], "Clues_Strip.png")
        save_img(p_data['target'], "Target_Box.png", True)

        final_audit.append({
            'batch_number': batch_num,
            'item_id': f"{batch_num}.{item_idx_str}",
            'folder_name': folder_name,
            'answer': p_data['answer'],
            'puzzle_version': f"Version {p_data['level']}",
            'variable_1_ABC_Role': p_data['coded_roles'][0],
            'variable_2_XYZ_Role': p_data['coded_roles'][1],
            'variable_3_123_Role': p_data['coded_roles'][2] if p_data['level'] == 3 else "N/A",
            'shading_category': p_data['sh_cat'],
            'background_category': p_data['bg_cat'],
            'difficulty_rating': diff_label
        })

    mode = 'a' if file_exists else 'w'
    with open(audit_path, mode, newline='') as f:
        w = csv.DictWriter(f, fieldnames=final_audit[0].keys())
        if not file_exists: w.writeheader()
        w.writerows(final_audit)

    print(f"Done! Batch {batch_num} sorted and saved to Desktop/NVR_Codes_A")