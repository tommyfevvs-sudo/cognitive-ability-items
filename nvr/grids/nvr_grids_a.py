import os
import random
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_grids_a")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Font search paths ──────────────────────────────────────────────────────────
FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
]
FALLBACK_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

class HDMinimalNVRGenerator:
    """Generates 2x2 Minimal NVR Grid items with Segregated Shape Pools."""

    def __init__(self):
        # ── Rendering & HD scale factors ──
        self.sf = 4
        self.cell_size_hd  = 200 * self.sf
        self.grid_line_hd  = int(3  * self.sf)
        self.border_hd     = int(5  * self.sf)
        self.outer_pad_hd  = int(30 * self.sf)
        self.label_pad_hd  = int(90 * self.sf) 

        # ── Object geometry (fractions of cell_size_hd) ──
        self.base_radius_frac = 0.25
        self.outline_w_hd     = int(2.5 * self.sf)

        # ── Rule Options ──
        self.scales = [0.60, 0.85, 1.10, 1.35, 1.60] 
        self.spins = [1, -1] # 1 = Clockwise, -1 = Anti-Clockwise
        self.extensions = [0.40, 0.65, 0.90, 1.15, 1.40] 
        self.positions = [
            (0.0, 0.0),       
            (-0.25, -0.25),   
            (0.25, -0.25),    
            (-0.25, 0.25),    
            (0.25, 0.25),     
            (0.0, -0.25),     
            (0.0, 0.25),      
            (-0.25, 0.0),     
            (0.25, 0.0)       
        ]
        
        self.fill_states = ["outline", "solid"]
        
        # ── Segregated Shape Pools ──
        self.standard_pool = [1, 2, 3, 4, 5, 6] 
        # 7:Tri, 8:Sq, 9:Dia, 10:Rho, 11:Pent, 12:Hex, 13:Hept, 14:Oct
        self.polygon_pool = [7, 8, 9, 10, 11, 12, 13, 14] 
        
        # Ordered sequence for sequential side generation
        self.poly_sequence = [7, 8, 11, 12, 13, 14]

        # ── Font loading ──
        self.font_hd  = None
        found = False

        print("Searching for Proxima Soft Regular...")
        for d in FONT_DIRS:
            if not os.path.isdir(d): continue
            try:
                for fname in os.listdir(d):
                    lf = fname.lower()
                    if "proxima" in lf and "soft" in lf:
                        bad = ["italic", " it.", " it ", "light", " lt", "bold", "semibold", "medium", " thin"]
                        if any(b in lf for b in bad): continue
                        if lf.endswith("it.otf") or lf.endswith("it.ttf"): continue
                        try:
                            fp = os.path.join(d, fname)
                            self.font_hd = ImageFont.truetype(fp, 44 * self.sf)
                            print(f"  SUCCESS: {fname}")
                            found = True
                            break
                        except Exception:
                            continue
                if found: break
            except Exception:
                continue

        if not found:
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd = ImageFont.truetype(fp, 44 * self.sf)
                        print(f"  Fallback: {fp}")
                        found = True
                        break
                    except Exception:
                        continue
        if not found:
            self.font_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-RULE LOGIC GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_attr_grid(self, attr, direction, selected_types):
        if direction == "Constant":
            if attr == "type": v = selected_types[0]
            elif attr == "scale": v = random.choice(self.scales)
            elif attr == "spin": v = 0
            elif attr == "extension_mult": v = random.choice(self.extensions)
            elif attr == "position_offset": v = random.choice(self.positions)
            elif attr == "fill_state": v = random.choice(self.fill_states)
            return {"A1": v, "B1": v, "A2": v, "B2": v}
            
        elif direction == "Horizontal":
            if attr == "type": v = selected_types 
            elif attr == "scale": v = random.sample(self.scales, 2)
            elif attr == "spin": v = random.sample(self.spins, 2)
            elif attr == "extension_mult": v = random.sample(self.extensions, 2)
            elif attr == "position_offset": v = random.sample(self.positions, 2)
            elif attr == "fill_state": v = list(self.fill_states)
            return {"A1": v[0], "B1": v[1], "A2": v[0], "B2": v[1]}
            
        elif direction == "Vertical":
            if attr == "type": v = selected_types
            elif attr == "scale": v = random.sample(self.scales, 2)
            elif attr == "spin": v = random.sample(self.spins, 2)
            elif attr == "extension_mult": v = random.sample(self.extensions, 2)
            elif attr == "position_offset": v = random.sample(self.positions, 2)
            elif attr == "fill_state": v = list(self.fill_states)
            return {"A1": v[0], "B1": v[0], "A2": v[1], "B2": v[1]}
            
        elif direction == "Diagonal":
            if attr == "type":
                return {"A1": selected_types[0], "B2": selected_types[1], "A2": selected_types[0], "B1": selected_types[1]} 
            elif attr == "scale":
                idx1 = random.randint(0, len(self.scales)-2)
                idx2 = random.randint(0, len(self.scales)-2)
                return {"A1": self.scales[idx1], "B2": self.scales[idx1+1], "A2": self.scales[idx2], "B1": self.scales[idx2+1]}
            elif attr == "spin":
                v = random.sample(self.spins, 2)
                if random.choice([True, False]): return {"A1": v[0], "B2": v[1], "A2": 0, "B1": 0}
                else: return {"A1": 0, "B2": 0, "A2": v[0], "B1": v[1]}
            elif attr == "extension_mult":
                idx1 = random.randint(0, len(self.extensions)-2)
                idx2 = random.randint(0, len(self.extensions)-2)
                return {"A1": self.extensions[idx1], "B2": self.extensions[idx1+1], "A2": self.extensions[idx2], "B1": self.extensions[idx2+1]}
            elif attr == "position_offset":
                v = random.sample(self.positions, 4)
                return {"A1": v[0], "B2": v[1], "A2": v[2], "B1": v[3]}
            elif attr == "fill_state":
                if random.choice([True, False]):
                    return {"A1": "solid", "B2": "outline", "A2": "solid", "B1": "solid"}
                else:
                    return {"A1": "solid", "B2": "solid", "A2": "outline", "B1": "solid"}

        elif direction == "Sequential":
            if attr == "type":
                idx = random.randint(0, len(self.poly_sequence) - 4)
                seq = self.poly_sequence[idx:idx+4]
                if random.choice([True, False]): seq.reverse()
                v = seq
            elif attr == "scale":
                seq = self.scales.copy()
                if random.choice([True, False]): seq.reverse()
                v = seq[:4]
            elif attr == "extension_mult":
                seq = self.extensions.copy()
                if random.choice([True, False]): seq.reverse()
                v = seq[:4]
            elif attr == "position_offset":
                paths = [
                    [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)], 
                    [(-0.25, -0.25), (-0.25, 0.25), (0.25, 0.25), (0.25, -0.25)]  
                ]
                v = random.choice(paths)
            return {"A1": v[0], "B1": v[1], "A2": v[2], "B2": v[3]}

    def generate_logic(self):
        num_rules = random.choice([1, 2, 3])
        attrs = ["type", "scale", "spin", "position_offset", "extension_mult", "fill_state"]
        
        while True:
            chosen_rules = random.sample(attrs, num_rules)
            if "scale" in chosen_rules and "extension_mult" in chosen_rules: continue

            temp_rules = {attr: "Constant" for attr in attrs}
            directions = ["Horizontal", "Vertical", "Diagonal", "Sequential"]
            
            for attr in attrs:
                if attr in chosen_rules:
                    valid_dirs = directions.copy()
                    if attr in ["fill_state", "spin"]: 
                        valid_dirs.remove("Sequential")
                    temp_rules[attr] = random.choice(valid_dirs)
            
            if temp_rules["scale"] != "Constant" and temp_rules["type"] == temp_rules["scale"]: continue
            if temp_rules["extension_mult"] != "Constant" and temp_rules["type"] == temp_rules["extension_mult"]: continue
            
            rules_applied = temp_rules
            break
            
        needs_poly = (rules_applied["fill_state"] != "Constant") or (rules_applied["type"] == "Sequential")
        if needs_poly:
            valid_pool = self.polygon_pool
        else:
            valid_pool = random.choice([self.standard_pool, self.polygon_pool])
        
        if rules_applied["type"] == "Constant":
            t = random.choice(valid_pool)
            selected_types = [t, t]
        else:
            selected_types = random.sample(valid_pool, 2)

        grid_data = {}
        for attr in attrs:
            grid_data[attr] = self.generate_attr_grid(attr, rules_applied[attr], selected_types)
                
        cells = {}
        for cell_id in ["A1", "B1", "A2", "B2"]:
            cells[cell_id] = {
                "type": grid_data["type"][cell_id],
                "scale": grid_data["scale"][cell_id],
                "spin": grid_data["spin"][cell_id],
                "position_offset": grid_data["position_offset"][cell_id],
                "extension_mult": grid_data["extension_mult"][cell_id],
                "fill_state": grid_data["fill_state"][cell_id]
            }
            
        return cells, num_rules, rules_applied

    def calculate_difficulty(self, num_rules, rules_applied):
        score = 0
        direction_weights = {"Constant": 0.0, "Horizontal": 1.0, "Vertical": 1.0, "Diagonal": 2.0, "Sequential": 2.5}
        for attr, direction in rules_applied.items():
            score += direction_weights.get(direction, 0.0)
            
        if num_rules == 2: score += 2.0
        elif num_rules == 3: score += 4.0
        return round(score, 1)

    # ═══════════════════════════════════════════════════════════════════════════
    # ENHANCED DISTRACTOR GENERATION 
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_options(self, correct_obj, rules_applied, cells):
        active_rules = [attr for attr, direction in rules_applied.items() if direction != "Constant"]
        num_rules = len(active_rules)
        random.shuffle(active_rules) 
        
        is_poly = correct_obj["type"] in self.polygon_pool
        spin_is_active = rules_applied["spin"] != "Constant"
        
        # Determine used types to prevent obvious shape distractors
        used_types = list(set(cell["type"] for cell in cells.values()))

        # 1. Determine Logic Option & LCM based on Table
        if num_rules <= 1:
            logic_name = "Default"
            lcm = 0.0
            blueprints = ["Random"] * 4
        elif num_rules == 2:
            choice = random.choice([1, 2, 3])
            if choice == 1:
                logic_name = "Option 1"
                lcm = 0.0
                blueprints = ["Random"] * 4
            elif choice == 2:
                logic_name = "Option 2"
                lcm = 0.2
                blueprints = [f"Rule_{active_rules[0]}_Only", "Random", "Random", "Random"]
            else: 
                logic_name = "Option 3"
                lcm = 0.5
                blueprints = [f"Rule_{active_rules[0]}_Only", f"Rule_{active_rules[1]}_Only", "Random", "Random"]
        else: # num_rules == 3
            choice = random.choice([4, 5, 6, 7, 8, 9, 10])
            if choice == 4:
                logic_name = "Option 4"
                lcm = 0.0
                blueprints = ["Random"] * 4
            elif choice == 5:
                logic_name = "Option 5"
                lcm = 0.3
                blueprints = [f"Rule_{active_rules[0]}_Only", "Random", "Random", "Random"]
            elif choice == 6:
                logic_name = "Option 6"
                lcm = 0.7
                blueprints = [f"Rule_{active_rules[0]}_Only", f"Rule_{active_rules[1]}_Only", "Random", "Random"]
            elif choice == 7: 
                logic_name = "Option 7"
                lcm = 1.2
                blueprints = [f"Rule_{active_rules[0]}_Only", f"Rule_{active_rules[1]}_Only", f"Rule_{active_rules[2]}_Only", "Random"]
            elif choice == 8:
                logic_name = "Option 8"
                lcm = 1.5
                blueprints = [f"Rule_{active_rules[0]}+{active_rules[1]}_Only", f"Rule_{active_rules[2]}_Only", "Random", "Random"]
            elif choice == 9:
                logic_name = "Option 9"
                lcm = 1.8
                blueprints = [f"Rule_{active_rules[0]}+{active_rules[1]}_Only", f"Rule_{active_rules[1]}+{active_rules[2]}_Only", f"Rule_{active_rules[0]}_Only", "Random"]
            elif choice == 10:
                logic_name = "Option 10"
                lcm = 2.2
                blueprints = [f"Rule_{active_rules[0]}+{active_rules[1]}_Only", f"Rule_{active_rules[1]}+{active_rules[2]}_Only", f"Rule_{active_rules[0]}_Only", f"Rule_{active_rules[2]}_Only"]

        options_with_meta = [{"obj": correct_obj.copy(), "logic": "Correct"}]

        def get_wrong_val(attr, current_val):
            if attr == "type":
                # Constrain random shape selection to only shapes used in the puzzle
                wrong = [t for t in used_types if t != current_val]
                return random.choice(wrong) if wrong else current_val
            elif attr == "scale":
                wrong = [s for s in self.scales if s != current_val]
                return random.choice(wrong) if wrong else current_val
            elif attr == "spin":
                return random.choice([1, -1]) if current_val == 0 else (-1 if current_val == 1 else 1)
            elif attr == "position_offset":
                wrong = [p for p in self.positions if p != current_val]
                return random.choice(wrong) if wrong else current_val
            elif attr == "extension_mult":
                wrong = [e for e in self.extensions if e != current_val]
                return random.choice(wrong) if wrong else current_val
            elif attr == "fill_state":
                return "solid" if current_val == "outline" else "outline"
            return current_val

        valid_visual_traits = ["type", "scale", "position_offset", "extension_mult"]
        if spin_is_active: valid_visual_traits.append("spin")
        if is_poly: valid_visual_traits.append("fill_state")

        def is_visually_unique(new_obj, current_list):
            for item in current_list:
                opt = item["obj"]
                diff = False
                for attr in valid_visual_traits:
                    if opt[attr] != new_obj[attr]:
                        diff = True
                        break
                if not diff:
                    return False
            return True

        # 2. Generate Distractors from Blueprints
        for bp in blueprints:
            candidate = correct_obj.copy()
            
            if bp.startswith("Rule_") and bp.endswith("_Only"):
                target_attrs = bp.replace("Rule_", "").replace("_Only", "").split("+")
                
                # Iterative uniqueness loop for logic-based distractors
                found_unique = False
                for _ in range(50):
                    cand = correct_obj.copy()
                    
                    # Ensure non-target active rules are broken
                    for attr in active_rules:
                        if attr not in target_attrs:
                            cand[attr] = get_wrong_val(attr, cand[attr])
                    
                    # Randomly mutate inactive traits to help guarantee visual uniqueness
                    # This does not break the core logic pattern since these rules are "Constant" in the grid
                    inactive_rules = [a for a in valid_visual_traits if a not in active_rules]
                    for attr in inactive_rules:
                        if random.random() < 0.4:
                            cand[attr] = get_wrong_val(attr, cand[attr])
                            
                    if is_visually_unique(cand, options_with_meta):
                        candidate = cand
                        found_unique = True
                        break
                
                if not found_unique:
                    # Failsafe loop if collision still happens
                    for _ in range(50):
                        attr = random.choice(valid_visual_traits)
                        candidate[attr] = get_wrong_val(attr, candidate[attr])
                        if is_visually_unique(candidate, options_with_meta): break
            
            else: # Random 
                found_unique = False
                for _ in range(100):
                    cand = correct_obj.copy()
                    num_mutations = random.randint(1, min(3, len(valid_visual_traits)))
                    attrs_to_mutate = random.sample(valid_visual_traits, num_mutations)
                    
                    for attr in attrs_to_mutate:
                        cand[attr] = get_wrong_val(attr, cand[attr])
                    
                    if is_visually_unique(cand, options_with_meta):
                        candidate = cand
                        found_unique = True
                        break
                        
                if not found_unique:
                    # Absolute failsafe for random distractors
                    for _ in range(50):
                        attr = random.choice(valid_visual_traits)
                        candidate[attr] = get_wrong_val(attr, candidate[attr])
                        if is_visually_unique(candidate, options_with_meta): break
                        
            options_with_meta.append({"obj": candidate, "logic": bp})

        # 3. Shuffle Positions and Create Mapping
        random.shuffle(options_with_meta)
        ans_options = [item["obj"] for item in options_with_meta]
        labels = ["A", "B", "C", "D", "E"]
        
        correct_idx = next(i for i, item in enumerate(options_with_meta) if item["logic"] == "Correct")
        correct_ans_label = labels[correct_idx]

        logic_mapping = {}
        for i, item in enumerate(options_with_meta):
            logic_mapping[f"Pos_{i+1}_{labels[i]}"] = item["logic"]

        logic_meta = {
            "logic_name": logic_name,
            "lcm": lcm,
            "mapping": logic_mapping
        }

        return ans_options, correct_ans_label, logic_meta

    # ═══════════════════════════════════════════════════════════════════════════
    # DRAWING ROUTINES 
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_object(self, target_img, cx, cy, obj, fit_factor=1.0, cell_size=None, current_angle=0):
        if obj is None: return
        if cell_size is None: cell_size = self.cell_size_hd

        base_r = cell_size * self.base_radius_frac * fit_factor
        r = base_r * obj["scale"]
        
        off_frac_x, off_frac_y = obj["position_offset"]
        center_x = cx + (off_frac_x * cell_size * fit_factor)
        center_y = cy + (off_frac_y * cell_size * fit_factor)
        
        rot = obj["spin"] * current_angle
        ext_mult = obj["extension_mult"]
        original_overhang = base_r * obj["scale"]
        current_overhang = original_overhang * ext_mult

        temp_size = int(cell_size * 3) 
        temp_img = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        tcx, tcy = temp_size // 2, temp_size // 2

        t = obj["type"]
        lw = self.outline_w_hd

        if t in [1, 2]:
            temp_draw.ellipse([tcx - r, tcy - r, tcx + r, tcy + r], outline="black", width=lw)
            if t == 1: temp_draw.line([tcx, tcy, tcx, tcy - r - current_overhang], fill="black", width=lw)
            elif t == 2: temp_draw.line([tcx, tcy - r - current_overhang, tcx, tcy + r + current_overhang], fill="black", width=lw)

        elif t == 3: 
            points = [(tcx - r/2, tcy + r), (tcx + r/2, tcy + r), (tcx + r, tcy), (tcx + r/4, tcy - r), (tcx - r, tcy)]
            temp_draw.polygon(points, fill="black")
            plume_h = (2 * r) * 0.45 * ext_mult
            plume_bbox = [tcx + r/4 - lw, tcy - r - plume_h + lw, tcx + r/4 + plume_h - lw, tcy - r + plume_h + lw]
            temp_draw.arc(plume_bbox, start=180, end=270, fill="black", width=lw)

        elif t == 4: 
            ew, eh = r * 0.8, r * 1.2 
            temp_draw.ellipse([tcx - ew, tcy - eh, tcx + ew, tcy + eh], outline="black", width=lw)
            vert_ext, horz_ext = (2 * eh) * 0.15 * ext_mult, (2 * ew) * 0.20 * ext_mult
            temp_draw.line([tcx, tcy, tcx, tcy + eh + vert_ext], fill="black", width=lw)
            temp_draw.line([tcx, tcy, tcx + ew + horz_ext, tcy], fill="black", width=lw)

        elif t == 5: 
            temp_draw.ellipse([tcx - r, tcy - r, tcx + r, tcy + r], outline="black", width=lw)
            r_node = r * 0.35
            axis_ext = (2*r + 2*r_node) * 0.15 * ext_mult
            temp_draw.line([tcx, tcy - r - r_node - axis_ext, tcx, tcy + r + r_node + axis_ext], fill="black", width=lw)
            temp_draw.ellipse([tcx - r_node, tcy - r - r_node, tcx + r_node, tcy - r + r_node], fill="black")
            temp_draw.ellipse([tcx - r_node, tcy + r - r_node, tcx + r_node, tcy + r + r_node], fill="black")

        elif t == 6: 
            r_node = r * 0.35
            axis_ext = (2*r + 2*r_node) * 0.15 * ext_mult
            top_y, bot_y = tcy - r - r_node - axis_ext, tcy + r + r_node + axis_ext
            temp_draw.line([tcx, top_y, tcx, bot_y], fill="black", width=lw)
            cap_w = r_node * 0.4 
            temp_draw.line([tcx - cap_w, top_y, tcx + cap_w, top_y], fill="black", width=lw)
            temp_draw.line([tcx - cap_w, bot_y, tcx + cap_w, bot_y], fill="black", width=lw)
            temp_draw.ellipse([tcx - r_node, tcy - r - r_node, tcx + r_node, tcy - r + r_node], fill="black")
            temp_draw.ellipse([tcx - r_node, tcy + r - r_node, tcx + r_node, tcy + r + r_node], fill="black")

        elif t in range(7, 15):
            v_map = {7:3, 8:4, 9:4, 10:4, 11:5, 12:6, 13:7, 14:8}
            v = v_map[t]
            
            offset = -math.pi / 2
            if t == 8: offset = -math.pi / 4 
            elif t == 14: offset = -math.pi / 8 
            
            x_scale = 0.6 if t == 10 else 1.0 
            
            is_solid = (obj["fill_state"] == "solid")
            fill_color = "black" if is_solid else None
            pts = []
            
            for i in range(v):
                angle = i * (2 * math.pi / v) + offset
                px = tcx + (r * x_scale) * math.cos(angle)
                py = tcy + r * math.sin(angle)
                pts.append((px, py))
                
            temp_draw.polygon(pts, fill=fill_color, outline="black", width=lw)
            
            if ext_mult > 0:
                for i in range(v):
                    angle = i * (2 * math.pi / v) + offset
                    vx = tcx + (r * x_scale) * math.cos(angle)
                    vy = tcy + r * math.sin(angle)
                    ex = tcx + ((r + current_overhang) * x_scale) * math.cos(angle)
                    ey = tcy + (r + current_overhang) * math.sin(angle)
                    temp_draw.line([vx, vy, ex, ey], fill="black", width=lw)

        rotated_img = temp_img.rotate(-rot, resample=Image.Resampling.BICUBIC, center=(tcx, tcy))
        paste_x, paste_y = int(center_x - tcx), int(center_y - tcy)
        target_img.paste(rotated_img, (paste_x, paste_y), rotated_img)

    def draw_text_centered(self, draw, x, y, text):
        bbox = draw.textbbox((0, 0), text, font=self.font_hd)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x - tw // 2, y - th // 2), text, font=self.font_hd, fill="black")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RENDERING AND EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
    def render_item(self, base_filename, puzzle_data):
        cells = puzzle_data["cells"]
        ans_options = puzzle_data["ans_options"]
        fit_factor = puzzle_data["fit_factor"]
        target_cell = puzzle_data.get("target_cell", "B2")
        is_gif = puzzle_data.get("is_gif", False)

        cs = self.cell_size_hd
        lw = self.grid_line_hd
        bw = self.border_hd
        grid_span = 2 * cs + lw

        grid_canvas_w = 2 * self.outer_pad_hd + 2 * bw + grid_span
        ans_cs = cs 
        ans_spacing = int(40 * self.sf)
        ans_strip_w = 5 * ans_cs + 4 * ans_spacing
        ans_canvas_h = ans_cs + int(150 * self.sf) 

        frames_count = 20 if is_gif else 1
        grid_frames, ans_frames = [], []

        for f in range(frames_count):
            current_angle = (360 / frames_count) * f if is_gif else 0

            grid_canvas = Image.new("RGBA", (grid_canvas_w, grid_canvas_w), "white")
            draw_grid = ImageDraw.Draw(grid_canvas)
            grid_x, grid_y = self.outer_pad_hd, self.outer_pad_hd

            draw_grid.rectangle([grid_x, grid_y, grid_x + 2*bw + grid_span, grid_y + 2*bw + grid_span], outline="black", width=bw)
            ix, iy = grid_x + bw + cs, grid_y + bw + cs
            draw_grid.rectangle([ix, grid_y + bw, ix + lw, grid_y + bw + grid_span], fill="black") 
            draw_grid.rectangle([grid_x + bw, iy, grid_x + bw + grid_span, iy + lw], fill="black") 

            coords = {
                "A1": (grid_x + bw + cs//2,           grid_y + bw + cs//2),
                "B1": (grid_x + bw + cs + lw + cs//2, grid_y + bw + cs//2),
                "A2": (grid_x + bw + cs//2,           grid_y + bw + cs + lw + cs//2),
                "B2": (grid_x + bw + cs + lw + cs//2, grid_y + bw + cs + lw + cs//2),
            }

            for cell_name, obj_data in cells.items():
                if cell_name != target_cell:
                    self.draw_object(grid_canvas, coords[cell_name][0], coords[cell_name][1], obj_data, fit_factor, current_angle=current_angle)

            ans_canvas = Image.new("RGBA", (ans_strip_w + 2 * self.outer_pad_hd, ans_canvas_h + 2 * self.outer_pad_hd), "white")
            draw_ans = ImageDraw.Draw(ans_canvas)
            ans_start_x, ans_start_y = self.outer_pad_hd, self.outer_pad_hd
            option_labels = ["A", "B", "C", "D", "E"]
            
            for idx, opt_obj in enumerate(ans_options):
                box_x = ans_start_x + idx * (ans_cs + ans_spacing)
                box_y = ans_start_y
                
                draw_ans.rectangle([box_x, box_y, box_x + ans_cs, box_y + ans_cs], outline="black", width=bw)
                opt_cx, opt_cy = box_x + ans_cs // 2, box_y + ans_cs // 2
                self.draw_object(ans_canvas, opt_cx, opt_cy, opt_obj, fit_factor, cell_size=ans_cs, current_angle=current_angle)
                
                lbl_y = box_y + ans_cs + int(50 * self.sf)
                self.draw_text_centered(draw_ans, opt_cx, lbl_y, option_labels[idx])

            grid_bd = ImageOps.invert(grid_canvas.convert("RGB")).getbbox()
            ans_bd = ImageOps.invert(ans_canvas.convert("RGB")).getbbox()

            top_pad, bottom_pad = int(10 * self.sf), int(10 * self.sf) 

            grid_top, grid_bottom = max(0, grid_bd[1] - top_pad), min(grid_canvas.height, grid_bd[3] + bottom_pad)
            grid_tight_h = grid_bottom - grid_top

            ans_top, ans_bottom = max(0, ans_bd[1] - top_pad), min(ans_canvas.height, ans_bd[3] + bottom_pad)
            ans_tight_h = ans_bottom - ans_top

            grid_content_w = grid_bd[2] - grid_bd[0]
            ans_content_w = ans_bd[2] - ans_bd[0]

            grid_169_w = int(grid_tight_h * (16 / 9))
            master_w = max(grid_169_w, ans_content_w)

            final_grid_hd = Image.new("RGBA", (master_w, grid_tight_h), "white")
            grid_content = grid_canvas.crop((grid_bd[0], grid_top, grid_bd[2], grid_bottom))
            
            final_ans_hd = Image.new("RGBA", (master_w, ans_tight_h), "white")
            ans_content = ans_canvas.crop((ans_bd[0], ans_top, ans_bd[2], ans_bottom))

            final_grid_hd.paste(grid_content, ((master_w - grid_content_w) // 2, 0))
            final_ans_hd.paste(ans_content, ((master_w - ans_content_w) // 2, 0))

            final_grid = final_grid_hd.resize((final_grid_hd.width // self.sf, final_grid_hd.height // self.sf), Image.Resampling.LANCZOS)
            final_ans = final_ans_hd.resize((final_ans_hd.width // self.sf, final_ans_hd.height // self.sf), Image.Resampling.LANCZOS)

            grid_frames.append(final_grid)
            ans_frames.append(final_ans)

        if is_gif:
            grid_path = os.path.join(OUTPUT_FOLDER, f"{base_filename}_grid.gif")
            ans_path  = os.path.join(OUTPUT_FOLDER, f"{base_filename}_answers.gif")
            grid_frames[0].save(grid_path, save_all=True, append_images=grid_frames[1:], duration=60, loop=0)
            ans_frames[0].save(ans_path, save_all=True, append_images=ans_frames[1:], duration=60, loop=0)
        else:
            grid_path = os.path.join(OUTPUT_FOLDER, f"{base_filename}_grid.png")
            ans_path  = os.path.join(OUTPUT_FOLDER, f"{base_filename}_answers.png")
            grid_frames[0].save(grid_path)
            ans_frames[0].save(ans_path)

if __name__ == "__main__":
    import csv
    import shutil

    print("=" * 45)
    print("Enhanced Logic Distractors & Scoring NVR Generator")
    print("=" * 45)
    
    try:
        user_input = input("How many puzzles would you like to generate? ")
        num_puzzles = int(user_input)
        if num_puzzles <= 0: raise ValueError
    except ValueError:
        print("Invalid number entered. Defaulting to 1 puzzle.")
        num_puzzles = 1

    generator = HDMinimalNVRGenerator()
    puzzles_meta = []

    print("\nGenerating and rendering temporary files...")
    for i in range(1, num_puzzles + 1):
        temp_base = f"temp_{i:05d}"
        
        cells, num_rules, rules = generator.generate_logic()
        target_cell = random.choice(["A1", "A2", "B1", "B2"])
        correct_obj = cells[target_cell]
        
        # New Enhanced Options Generation
        ans_options, correct_ans_label, logic_meta = generator.generate_options(correct_obj, rules, cells)
        
        # New Scoring Calc
        base_score = generator.calculate_difficulty(num_rules, rules)
        total_score = round(base_score + logic_meta["lcm"], 1)
        
        grid_objects = [obj for k, obj in cells.items() if k != target_cell]
        all_objects = grid_objects + ans_options
        
        is_gif = rules.get("spin", "Constant") != "Constant"
        
        max_extent_frac = 0.0
        for obj in all_objects:
            if obj is None: continue
            off_x, off_y = obj["position_offset"]
            max_off = max(abs(off_x), abs(off_y))
            reach = generator.base_radius_frac * obj["scale"] * (1.0 + obj["extension_mult"])
            extent = max_off + reach
            if extent > max_extent_frac:
                max_extent_frac = extent
        fit_factor = 0.40 / max_extent_frac if max_extent_frac > 0 else 1.0

        puzzle_data = {
            "cells": cells,
            "ans_options": ans_options,
            "fit_factor": fit_factor,
            "target_cell": target_cell,
            "is_gif": is_gif
        }
        
        media_type = "GIF (Animated)" if is_gif else "PNG (Static)"
        print(f"  -> Rendering {temp_base} | {logic_meta['logic_name']} | Score: {total_score}")
        generator.render_item(temp_base, puzzle_data)

        puzzles_meta.append({
            "temp_name": temp_base,
            "base_score": base_score,
            "total_score": total_score,
            "num_rules": num_rules,
            "rules": rules,
            "logic_meta": logic_meta,
            "target_cell": target_cell,
            "correct_ans_label": correct_ans_label,
            "is_gif": is_gif
        })

    print("\nSorting by final difficulty score and renaming files on disk...")
    puzzles_meta.sort(key=lambda x: x["total_score"])

    manifest_path = os.path.join(OUTPUT_FOLDER, "Puzzle_Manifest.csv")
    
    with open(manifest_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        
        # Expanded Header structure based on table specifications
        writer.writerow(["Filename", "Base_Difficulty", "LCM_Modifier", "Total_Score", 
                         "Num_Rules", "Logic_Option",
                         "Horizontal_Rule", "Vertical_Rule", "Diagonal_Rule", 
                         "Sequential_Rule", "Fixed_Variables", 
                         "Target_Cell", "Correct_Answer", "Position_Mapping", "Media_Format"])
        
        for i, meta in enumerate(puzzles_meta):
            final_base = f"Puzzle_{i+1:03d}"
            ext = ".gif" if meta["is_gif"] else ".png"
            
            temp_grid = os.path.join(OUTPUT_FOLDER, f"{meta['temp_name']}_grid{ext}")
            temp_ans  = os.path.join(OUTPUT_FOLDER, f"{meta['temp_name']}_answers{ext}")
            
            final_grid = os.path.join(OUTPUT_FOLDER, f"{final_base}_grid{ext}")
            final_ans  = os.path.join(OUTPUT_FOLDER, f"{final_base}_answers{ext}")
            
            if os.path.exists(temp_grid): shutil.move(temp_grid, final_grid)
            if os.path.exists(temp_ans):  shutil.move(temp_ans, final_ans)
            
            r = meta["rules"]
            dir_map = {"Horizontal": [], "Vertical": [], "Diagonal": [], "Sequential": [], "Constant": []}
            for attr_name, dir_name in r.items():
                dir_map[dir_name].append(attr_name)
                
            h_rule = ", ".join(dir_map["Horizontal"]) or "None"
            v_rule = ", ".join(dir_map["Vertical"]) or "None"
            d_rule = ", ".join(dir_map["Diagonal"]) or "None"
            seq_rule = ", ".join(dir_map["Sequential"]) or "None"
            fixed_rule = ", ".join(dir_map["Constant"]) or "None"
            
            media_format = "GIF" if meta["is_gif"] else "PNG"
            
            # Stringify mapping into a clean readable string
            mapping_str = " | ".join([f"{k}: {v}" for k, v in meta["logic_meta"]["mapping"].items()])
            
            writer.writerow([
                final_base, meta["base_score"], meta["logic_meta"]["lcm"], meta["total_score"],
                meta["num_rules"], meta["logic_meta"]["logic_name"], 
                h_rule, v_rule, d_rule, seq_rule, fixed_rule, 
                meta["target_cell"], meta["correct_ans_label"], mapping_str, media_format
            ])

    print(f"\nDone! Processed {num_puzzles} puzzles. Manifest saved at:\n{manifest_path}")
