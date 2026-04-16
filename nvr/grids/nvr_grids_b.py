import os
import random
import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_grids_b")
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

class HDDesign4NVRGenerator:
    """Generates 2x2 NVR Grid items based on various spatial logic frameworks."""

    def __init__(self):
        self.sf = 4
        self.cell_size_hd  = 200 * self.sf
        self.grid_line_hd  = int(3  * self.sf)
        self.border_hd     = int(5  * self.sf)
        self.outer_pad_hd  = int(30 * self.sf)
        
        self.label_pad_hd  = int(90 * self.sf) 
        self.outline_w_hd  = int(2.5 * self.sf)

        self.valid_coords = [1, 2, 3, 4] 
        self.shapes = [3, 4, 5, 6, 8] 
        self.fills = ["outline", "solid"]
        
        self.scales = [0.6, 1.0, 1.4] 
        self.rotations = [0, 45, 90, 180]
        self.flips = ["none", "h", "v"] 

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
            print("  WARNING: Using built-in default font.")
            self.font_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════
    # VISUAL SYMMETRY & STRICT UNIQUENESS SAFEGUARDS
    # ═══════════════════════════════════════════════════════════════════════════
    def get_visual_footprint(self, obj):
        points = []
        for i in range(obj["sides"]):
            angle = math.radians(obj["rot"] + (i * 360.0 / obj["sides"]) - 90)
            px = math.cos(angle)
            py = math.sin(angle)
            if obj.get("flip") == "h":
                px = -px
            elif obj.get("flip") == "v":
                py = -py
            
            px = round(px + 0.0, 3)
            py = round(py + 0.0, 3)
            points.append((px, py))
        
        points.sort()
        return tuple(points)
        
    def get_object_visual_state(self, obj):
        """Distills an object into an ID-agnostic hashable state."""
        footprint = self.get_visual_footprint(obj)
        return (footprint, obj["pos"], obj["fill"], obj["scale"])

    def objects_are_visually_identical(self, obj1, obj2):
        return self.get_object_visual_state(obj1) == self.get_object_visual_state(obj2)

    def cells_are_visually_identical(self, cell1, cell2):
        """Strictly compares two cells. Ignores internal object IDs. Only compares what is drawn."""
        if len(cell1) != len(cell2): return False
        
        states1 = [self.get_object_visual_state(o) for o in cell1]
        states2 = [self.get_object_visual_state(o) for o in cell2]
        
        return Counter(states1) == Counter(states2)

    def rule_causes_visual_change(self, cell_before, cell_after, target_id=None):
        if len(cell_before) != len(cell_after): return True 
        for o_before in cell_before:
            if target_id is not None and o_before["id"] != target_id: continue 
            o_after = next((o for o in cell_after if o["id"] == o_before["id"]), None)
            if not o_after: return True 
            if not self.objects_are_visually_identical(o_before, o_after): return True 
        return False

    def grid_is_unique(self, cells):
        cell_list = [cells["A1"], cells["B1"], cells["A2"], cells["B2"]]
        if any(c is None for c in cell_list): return False
        for i in range(len(cell_list)):
            for j in range(i + 1, len(cell_list)):
                if self.cells_are_visually_identical(cell_list[i], cell_list[j]):
                    return False
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # LOGIC GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    def create_anchor_group(self):
        """Creates an Anchor Group, enforcing strictly distinct geometric shapes within the cell."""
        num_objects = random.choices([2, 3, 4], weights=[50, 35, 15], k=1)[0]
        group = []
        used_coords = set()
        
        chosen_shapes = random.sample(self.shapes, num_objects)

        for i in range(1, num_objects + 1):
            pos = (random.choice(self.valid_coords), random.choice(self.valid_coords))
            while pos in used_coords:
                pos = (random.choice(self.valid_coords), random.choice(self.valid_coords))
            used_coords.add(pos)

            group.append({
                "id": i,
                "sides": chosen_shapes[i-1],
                "pos": pos,
                "scale": 1.0, 
                "rot": 0, 
                "fill": random.choice(self.fills),
                "flip": "none" 
            })
        return group

    def get_random_rule(self, rule_type):
        if rule_type == "Translation":
            dx, dy = random.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
            dir_str = "Right" if dx==1 else "Left" if dx==-1 else "Down" if dy==1 else "Up"
            return (dx, dy), f"Move 1 space {dir_str}"
        elif rule_type == "Add Sides":
            r_val = random.choice([1, -1])
            return r_val, f"{'Add' if r_val == 1 else 'Subtract'} 1 side"
        elif rule_type == "Change Scale":
            r_val = random.choice([1, -1])
            return r_val, f"{'Increase' if r_val == 1 else 'Decrease'} size"
        elif rule_type == "Rotate":
            r_val = random.choice([45, 90, 180])
            return r_val, f"Rotate {r_val} degrees"
        elif rule_type == "Reflect":
            return "v", "Reflect Vertically"
        elif rule_type == "Change Quantity":
            r_val = random.choice([1, -1])
            return r_val, f"{'Add' if r_val==1 else 'Remove'} 1 object"
        elif rule_type == "Toggle Fill":
            return None, "Toggle between Solid/Outline"

    def apply_rule(self, cell, rule_type, rule_val, target_id=None):
        new_cell = [obj.copy() for obj in cell]
        
        if rule_type == "Change Quantity":
            if rule_val == 1 and len(new_cell) < 4:
                existing_coords = [o["pos"] for o in new_cell]
                avail_coords = [(x,y) for x in self.valid_coords for y in self.valid_coords if (x,y) not in existing_coords]
                
                existing_shapes = [o["sides"] for o in new_cell]
                avail_shapes = [s for s in self.shapes if s not in existing_shapes]
                if not avail_shapes: avail_shapes = self.shapes
                
                if avail_coords:
                    new_id = max([o["id"] for o in new_cell]) + 1
                    new_cell.append({
                        "id": new_id,
                        "sides": random.choice(avail_shapes),
                        "pos": random.choice(avail_coords),
                        "scale": 1.0,
                        "rot": 0,
                        "fill": random.choice(self.fills),
                        "flip": "none"
                    })
            elif rule_val == -1 and len(new_cell) > 2: 
                new_cell.pop()
            return new_cell

        for obj in new_cell:
            if target_id is not None and obj["id"] != target_id: continue
                
            if rule_type == "Translation":
                dx, dy = rule_val
                obj["pos"] = (obj["pos"][0] + dx, obj["pos"][1] + dy)
            elif rule_type == "Add Sides":
                idx = self.shapes.index(obj["sides"])
                obj["sides"] = self.shapes[(idx + rule_val) % len(self.shapes)]
            elif rule_type == "Toggle Fill":
                obj["fill"] = "solid" if obj["fill"] == "outline" else "outline"
            elif rule_type == "Change Scale":
                idx = self.scales.index(obj["scale"])
                obj["scale"] = self.scales[(idx + rule_val) % len(self.scales)]
            elif rule_type == "Rotate":
                obj["rot"] = (obj["rot"] + rule_val) % 360
            elif rule_type == "Reflect":
                if rule_val == "h": obj["flip"] = "none" if obj["flip"] == "h" else "h"
                elif rule_val == "v": obj["flip"] = "none" if obj["flip"] == "v" else "v"
                
        return new_cell

    def calculate_difficulty(self, logic_type, direction, rule_types, num_objects, target_cell):
        score = 0.0
        
        if logic_type == "Parallel":
            score += 1.0
            if direction == "Diagonal": score += 1.5
            else: score += 0.5
        elif logic_type == "Matrix": score += 2.0
        elif logic_type == "Continuous": score += 1.0
            
        if target_cell != "B2": score += 1.0
        score += (num_objects - 2) * 0.5

        rule_weights = {"Toggle Fill": 0.5, "Translation": 1.0, "Change Scale": 1.0, "Add Sides": 1.5, "Change Quantity": 1.5, "Rotate": 2.0, "Reflect": 2.5}
        for rt in rule_types: score += rule_weights.get(rt, 1.0)
        if len(rule_types) > 1: score += 1.5 * (len(rule_types) - 1)

        return round(score, 1)
    
    def generate_logic(self):
        while True:
            grid_raw_rules = []
            target_cell = random.choice(["A1", "A2", "B1", "B2"])
            logic_type = random.choices(["Parallel", "Matrix", "Continuous"], weights=[40, 35, 25], k=1)[0]
            cells = {"A1": None, "B1": None, "A2": None, "B2": None}
            rules_applied = {}
            is_valid = True
            applied_rule_types = []
            direction = "N/A"

            if logic_type == "Parallel":
                direction = random.choice(["Row to Row", "Column to Column", "Diagonal"])
                rule_vars = ["Translation", "Toggle Fill", "Add Sides", "Change Scale", "Rotate", "Reflect", "Change Quantity"]
                num_rules = random.choices([1, 2], weights=[50, 50], k=1)[0]
                chosen_r_types = random.sample(rule_vars, num_rules)

                applied_rules = []
                for idx, rt in enumerate(chosen_r_types):
                    val, desc = self.get_random_rule(rt)
                    applied_rules.append((rt, val))
                    applied_rule_types.append(rt)
                    grid_raw_rules.append((rt, val, None))
                    rules_applied[f"Rule {idx+1}"] = desc

                def apply_all(c):
                    temp = c
                    for rt, val in applied_rules: temp = self.apply_rule(temp, rt, val)
                    return temp

                group1 = self.create_anchor_group()
                group2 = self.create_anchor_group()
                while self.cells_are_visually_identical(group1, group2):
                    group2 = self.create_anchor_group()

                if direction == "Row to Row":
                    rules_applied["Direction"] = "Vertical (Top transforms to Bottom)"
                    cells["A1"], cells["B1"] = group1, group2 
                    cells["A2"] = apply_all(group1)           
                    cells["B2"] = apply_all(group2)           
                elif direction == "Column to Column":
                    rules_applied["Direction"] = "Horizontal (Left transforms to Right)"
                    cells["A1"], cells["A2"] = group1, group2 
                    cells["B1"] = apply_all(group1)           
                    cells["B2"] = apply_all(group2)           
                elif direction == "Diagonal":
                    rules_applied["Direction"] = "Diagonal (A1->B2 and A2->B1)"
                    cells["A1"], cells["A2"] = group1, group2 
                    cells["B2"] = apply_all(group1)           
                    cells["B1"] = apply_all(group2)           

                if not self.rule_causes_visual_change(cells["A1"], cells["A2" if direction in ["Row to Row", "Diagonal"] else "B1"]): is_valid = False
                if not self.rule_causes_visual_change(cells["B1" if direction in ["Row to Row", "Diagonal"] else "A2"], cells["B2"]): is_valid = False

            else:
                A1 = self.create_anchor_group()
                cells["A1"] = A1

                if logic_type == "Matrix":
                    matrix_rule_vars = ["Translation", "Toggle Fill", "Add Sides", "Change Scale", "Rotate", "Reflect"]
                    chosen_r_types = random.sample(matrix_rule_vars, 2)

                    r1_val, r1_desc = self.get_random_rule(chosen_r_types[0])
                    r2_val, r2_desc = self.get_random_rule(chosen_r_types[1])

                    applied_rule_types.extend(chosen_r_types)
                    grid_raw_rules.append((chosen_r_types[0], r1_val, None))
                    grid_raw_rules.append((chosen_r_types[1], r2_val, None))
                    rules_applied["Rule 1"] = f"{r1_desc} (Applies Horizontally)"
                    rules_applied["Rule 2"] = f"{r2_desc} (Applies Vertically)"
                    rules_applied["Direction"] = "Matrix (Independent Axes)"
                    direction = "Matrix (Independent Axes)"

                    B1 = self.apply_rule(A1, chosen_r_types[0], r1_val) 
                    A2 = self.apply_rule(A1, chosen_r_types[1], r2_val) 
                    B2 = self.apply_rule(B1, chosen_r_types[1], r2_val) 

                    cells["B1"] = B1
                    cells["A2"] = A2
                    cells["B2"] = B2

                    if not self.rule_causes_visual_change(cells["A1"], cells["B1"]): is_valid = False
                    if not self.rule_causes_visual_change(cells["A1"], cells["A2"]): is_valid = False

                elif logic_type == "Continuous":
                    direction = "Continuous Sequence"
                    rules_applied["Direction"] = "Continuous Sequence (A1 -> B1 -> A2 -> B2)"
                    rule_vars = ["Translation", "Toggle Fill", "Add Sides", "Change Scale", "Rotate", "Change Quantity"]
                    num_rules = random.choices([1, 2], weights=[60, 40], k=1)[0]
                    chosen_r_types = random.sample(rule_vars, num_rules)

                    # New Logic: Enforce tracking of a single object if only 1 rule is applied (to reduce noise)
                    target_id = None
                    if num_rules == 1 and chosen_r_types[0] != "Change Quantity":
                        target_id = random.choice([o["id"] for o in cells["A1"]])

                    applied_rules = []
                    for idx, rt in enumerate(chosen_r_types):
                        val, desc = self.get_random_rule(rt)
                        if target_id is not None:
                            desc += f" (Applies strictly to Obj {target_id})"
                        applied_rules.append((rt, val))
                        applied_rule_types.append(rt)
                        grid_raw_rules.append((rt, val, target_id))
                        rules_applied[f"Rule {idx+1}"] = desc

                    def apply_all(c):
                        temp = c
                        for rt, val in applied_rules: 
                            temp = self.apply_rule(temp, rt, val, target_id=target_id)
                        return temp

                    cells["B1"] = apply_all(cells["A1"])
                    cells["A2"] = apply_all(cells["B1"])
                    cells["B2"] = apply_all(cells["A2"])

                    if not self.rule_causes_visual_change(cells["A1"], cells["B1"], target_id): is_valid = False
                    if not self.rule_causes_visual_change(cells["B1"], cells["A2"], target_id): is_valid = False
                    if not self.rule_causes_visual_change(cells["A2"], cells["B2"], target_id): is_valid = False

            def is_in_bounds(cell):
                if cell is None: return False
                for obj in cell:
                    if not (1 <= obj["pos"][0] <= 4 and 1 <= obj["pos"][1] <= 4): return False
                return True

            if not all(is_in_bounds(c) for c in [cells["A1"], cells["A2"], cells["B1"], cells["B2"]]):
                is_valid = False

            if not self.grid_is_unique(cells):
                is_valid = False

            if is_valid:
                obj_count = len(cells["A1"])
                score = self.calculate_difficulty(logic_type, direction, applied_rule_types, obj_count, target_cell)
                return cells, logic_type, rules_applied, score, target_cell, grid_raw_rules

    def apply_inverse_rule(self, cell, rule_type, rule_val, target_id=None):
        """Mathematically reverses a rule to simulate a missed step."""
        inv_val = rule_val
        if rule_type == "Translation": 
            inv_val = (-rule_val[0], -rule_val[1])
        elif rule_type in ["Add Sides", "Change Scale", "Rotate", "Change Quantity"]: 
            inv_val = -rule_val
        # Toggle Fill and Reflect are their own inverses, so inv_val remains unchanged
        return self.apply_rule(cell, rule_type, inv_val, target_id)

    def is_cell_in_bounds(self, cell):
        if not cell: return False
        for obj in cell:
            if not (1 <= obj["pos"][0] <= 4 and 1 <= obj["pos"][1] <= 4): return False
        return True

    def generate_options(self, correct_cell, grid_raw_rules, cells):
        options = [[obj.copy() for obj in correct_cell]]
        num_rules = len(grid_raw_rules)
        difficulty_modifier = 0.0
        
        # 1. Determine used shapes to prevent obvious shape distractors
        used_shapes = set()
        for cell in cells.values():
            if cell is not None:
                for obj in cell:
                    used_shapes.add(obj["sides"])
        used_shapes = list(used_shapes)

        def is_visually_unique(new_cell):
            for opt in options:
                if self.cells_are_visually_identical(opt, new_cell): return False
            return True

        def get_unique_distractor(mutation_func):
            for _ in range(100):
                candidate = [obj.copy() for obj in correct_cell]
                mutation_func(candidate)
                if is_visually_unique(candidate): return candidate
            
            # Fallback randomizer to prevent infinite loops
            for _ in range(50):
                candidate = [obj.copy() for obj in correct_cell]
                if candidate:
                    target = random.choice(range(len(candidate)))
                    candidate[target]["pos"] = (random.choice(self.valid_coords), random.choice(self.valid_coords))
                    candidate[target]["fill"] = random.choice(self.fills)
                    candidate[target]["rot"] = random.choice(self.rotations)
                    # Constrain to used shapes here as well
                    candidate[target]["sides"] = random.choice(used_shapes) if used_shapes else random.choice(self.shapes)
                if is_visually_unique(candidate):
                    return candidate
            return candidate # Absolute failsafe

        # --- Random Mutators (The 'R' in the CSV) ---
        def mutate_pos(cell):
            if cell:
                wrong_x = [x for x in self.valid_coords if x != cell[0]["pos"][0]]
                if wrong_x: cell[0]["pos"] = (random.choice(wrong_x), cell[0]["pos"][1])
        
        def mutate_shape(cell):
            if len(cell) > 1:
                # Restrict to shapes actively used in the puzzle
                avail_shapes = [s for s in used_shapes if s != cell[1]["sides"]]
                if not avail_shapes: avail_shapes = [s for s in self.shapes if s != cell[1]["sides"]]
                if avail_shapes:
                    cell[1]["sides"] = random.choice(avail_shapes)
                
        def mutate_scale_or_rot(cell):
            if cell:
                target = random.choice(range(len(cell)))
                if random.choice([True, False]):
                    wrong_scales = [s for s in self.scales if s != cell[target]["scale"]]
                    if wrong_scales: cell[target]["scale"] = random.choice(wrong_scales)
                else:
                    wrong_rots = [r for r in self.rotations if r != cell[target]["rot"] and r != 0]
                    if wrong_rots: cell[target]["rot"] = random.choice(wrong_rots)
                    
        def mutate_compound(cell):
            if len(cell) > 1:
                cell[0]["pos"] = (random.choice(self.valid_coords), random.choice(self.valid_coords))
                cell[1]["fill"] = "solid" if cell[1]["fill"] == "outline" else "outline"

        # --- Generate Partial Rule Distractors (The U1, U2, U3 in the CSV) ---
        def get_inverse_candidate(rule_indices):
            """Applies the inverse of multiple rules to simulate a multi-step logic failure."""
            cand = [obj.copy() for obj in correct_cell]
            for idx in rule_indices:
                if idx < len(grid_raw_rules):
                    rt, val, tid = grid_raw_rules[idx]
                    cand = self.apply_inverse_rule(cand, rt, val, tid)
            if self.is_cell_in_bounds(cand):
                return cand
            return None

        u_candidates = {
            'U1': get_inverse_candidate([0]),
            'U2': get_inverse_candidate([1]),
            'U3': get_inverse_candidate([2]),
            'U1+2': get_inverse_candidate([0, 1]),
            'U2+3': get_inverse_candidate([1, 2])
        }

        # --- Profile Selection based on Logic ---
        profile = []
        if num_rules <= 1:
            profile, difficulty_modifier = ['R', 'R', 'R', 'R'], 0.0
        elif num_rules == 2:
            choice = random.choices([1, 2, 3], weights=[33, 33, 34])[0]
            if choice == 1:   profile, difficulty_modifier = ['R', 'R', 'R', 'R'], 0.0
            elif choice == 2: profile, difficulty_modifier = ['U1', 'R', 'R', 'R'], 0.2
            else:             profile, difficulty_modifier = ['U1', 'U2', 'R', 'R'], 0.5
        else: # 3 or more rules
            choice = random.choice([4, 5, 6, 7, 8, 9, 10])
            if choice == 4:   profile, difficulty_modifier = ['R', 'R', 'R', 'R'], 0.0
            elif choice == 5: profile, difficulty_modifier = ['U1', 'R', 'R', 'R'], 0.3
            elif choice == 6: profile, difficulty_modifier = ['U1', 'U2', 'R', 'R'], 0.7
            elif choice == 7: profile, difficulty_modifier = ['U1', 'U2', 'U3', 'R'], 1.2
            elif choice == 8: profile, difficulty_modifier = ['U1+2', 'U3', 'R', 'R'], 1.5
            elif choice == 9: profile, difficulty_modifier = ['U1+2', 'U2+3', 'U1', 'R'], 1.8
            elif choice == 10: profile, difficulty_modifier = ['U1+2', 'U2+3', 'U1', 'U3'], 2.2

        # --- Populate Options Based on Selected Profile ---
        mutators = [mutate_pos, mutate_shape, mutate_scale_or_rot, mutate_compound]
        random.shuffle(mutators)
        mutator_idx = 0

        for item in profile:
            added_u = False
            if item.startswith('U'):
                cand = u_candidates.get(item)
                if cand is not None and is_visually_unique(cand):
                    options.append(cand)
                    added_u = True
            
            if not added_u: # Fallback to Random ('R') if U fails or profile dictates 'R'
                func = mutators[mutator_idx % len(mutators)]
                options.append(get_unique_distractor(func))
                mutator_idx += 1

        random.shuffle(options)
        correct_index = options.index(correct_cell)
        labels = ["A", "B", "C", "D", "E"]
        return options, labels[correct_index], difficulty_modifier

    # ═══════════════════════════════════════════════════════════════════════════
    # DRAWING ROUTINES (6x6 Grid Mapping)
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_cell(self, target_img, cx, cy, cell_objects, fit_factor=1.0, cell_size=None):
        if cell_objects is None: return
        if cell_size is None: cell_size = self.cell_size_hd

        spacing = cell_size / 5
        base_r = (spacing * 0.38) * fit_factor 
        lw = self.outline_w_hd

        for obj in cell_objects:
            grid_x, grid_y = obj["pos"]
            
            offset_x = (grid_x - 2.5) * spacing
            offset_y = (grid_y - 2.5) * spacing
            
            obj_cx = cx + offset_x
            obj_cy = cy + offset_y
            r = base_r * obj["scale"]

            temp_size = int(cell_size)
            temp_img = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            tcx, tcy = temp_size // 2, temp_size // 2

            points = []
            for i in range(obj["sides"]):
                angle = math.radians(obj["rot"] + (i * 360 / obj["sides"]) - 90)
                px = r * math.cos(angle)
                py = r * math.sin(angle)
                if obj.get("flip") == "h": px = -px
                elif obj.get("flip") == "v": py = -py
                points.append((tcx + px, tcy + py))
            
            if obj["fill"] == "solid": temp_draw.polygon(points, fill="black")
            else:
                points.append(points[0]) 
                temp_draw.line(points, fill="black", width=lw, joint="curve")

            paste_x = int(obj_cx - tcx)
            paste_y = int(obj_cy - tcy)
            target_img.paste(temp_img, (paste_x, paste_y), temp_img)

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
        target_cell = puzzle_data["target_cell"]

        cs = self.cell_size_hd
        lw = self.grid_line_hd
        bw = self.border_hd
        grid_span = 2 * cs + lw

        grid_canvas_w = 2 * self.outer_pad_hd + 2 * bw + grid_span
        grid_canvas = Image.new("RGBA", (grid_canvas_w, grid_canvas_w), "white")
        draw_grid = ImageDraw.Draw(grid_canvas)

        grid_x = self.outer_pad_hd
        grid_y = self.outer_pad_hd

        draw_grid.rectangle([grid_x, grid_y, grid_x + 2*bw + grid_span, grid_y + 2*bw + grid_span], outline="black", width=bw)
        ix = grid_x + bw + cs
        iy = grid_y + bw + cs
        draw_grid.rectangle([ix, grid_y + bw, ix + lw, grid_y + bw + grid_span], fill="black")
        draw_grid.rectangle([grid_x + bw, iy, grid_x + bw + grid_span, iy + lw], fill="black")

        coords = {
            "A1": (grid_x + bw + cs//2,           grid_y + bw + cs//2),
            "B1": (grid_x + bw + cs + lw + cs//2, grid_y + bw + cs//2),
            "A2": (grid_x + bw + cs//2,           grid_y + bw + cs + lw + cs//2),
            "B2": (grid_x + bw + cs + lw + cs//2, grid_y + bw + cs + lw + cs//2),
        }

        for cell_name, cell_data in cells.items():
            if cell_name != target_cell:
                self.draw_cell(grid_canvas, coords[cell_name][0], coords[cell_name][1], cell_data, fit_factor)

        ans_cs = cs 
        ans_spacing = int(40 * self.sf)
        ans_strip_w = 5 * ans_cs + 4 * ans_spacing
        ans_canvas_h = ans_cs + int(150 * self.sf)
        
        ans_canvas = Image.new("RGBA", (ans_strip_w + 2 * self.outer_pad_hd, ans_canvas_h + 2 * self.outer_pad_hd), "white")
        draw_ans = ImageDraw.Draw(ans_canvas)

        ans_start_x = self.outer_pad_hd
        ans_start_y = self.outer_pad_hd
        option_labels = ["A", "B", "C", "D", "E"]
        
        for idx, opt_cell in enumerate(ans_options):
            box_x = ans_start_x + idx * (ans_cs + ans_spacing)
            box_y = ans_start_y
            
            draw_ans.rectangle([box_x, box_y, box_x + ans_cs, box_y + ans_cs], outline="black", width=bw)
            self.draw_cell(ans_canvas, box_x + ans_cs // 2, box_y + ans_cs // 2, opt_cell, fit_factor, cell_size=ans_cs)
            
            lbl_y = box_y + ans_cs + int(50 * self.sf)
            self.draw_text_centered(draw_ans, box_x + ans_cs // 2, lbl_y, option_labels[idx])

        grid_bd = ImageOps.invert(grid_canvas.convert("RGB")).getbbox()
        ans_bd = ImageOps.invert(ans_canvas.convert("RGB")).getbbox()

        top_pad = int(10 * self.sf)    
        bottom_pad = int(10 * self.sf) 

        grid_top = max(0, grid_bd[1] - top_pad)
        grid_bottom = min(grid_canvas.height, grid_bd[3] + bottom_pad)
        grid_tight_h = grid_bottom - grid_top

        ans_top = max(0, ans_bd[1] - top_pad)
        ans_bottom = min(ans_canvas.height, ans_bd[3] + bottom_pad)
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

        final_grid.save(os.path.join(OUTPUT_FOLDER, f"{base_filename}_grid.png"))
        final_ans.save(os.path.join(OUTPUT_FOLDER, f"{base_filename}_answers.png"))

if __name__ == "__main__":
    import csv
    import shutil

    print("=" * 40)
    print("Design 4 NVR Grid Generator")
    print("=" * 40)
    
    try:
        user_input = input("How many puzzles would you like to generate? ")
        num_puzzles = int(user_input)
        if num_puzzles <= 0: raise ValueError
    except ValueError:
        print("Invalid number. Defaulting to 1.")
        num_puzzles = 1

    generator = HDDesign4NVRGenerator()
    puzzles_meta = []

    print("\nGenerating...")
    for i in range(1, num_puzzles + 1):
        temp_base = f"temp_{i:05d}"
        cells, logic_type, rules, score, target_cell, grid_raw_rules = generator.generate_logic()
        ans_options, correct_ans_label, diff_mod = generator.generate_options(cells[target_cell], grid_raw_rules, cells)
        score += diff_mod
        
        puzzle_data = {
            "cells": cells,
            "ans_options": ans_options,
            "fit_factor": 1.0,
            "target_cell": target_cell
        }
        
        generator.render_item(temp_base, puzzle_data)

        puzzles_meta.append({
            "temp_name": temp_base,
            "score": score,
            "logic_type": logic_type,
            "rules": rules,
            "target_cell": target_cell,
            "correct_ans_label": correct_ans_label
        })

    print("\nSorting and Manifesting...")
    puzzles_meta.sort(key=lambda x: x["score"])

    manifest_path = os.path.join(OUTPUT_FOLDER, "Puzzle_Manifest.csv")
    with open(manifest_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Difficulty_Score", "Logic_Type", "Target_Cell", "Rule_1", "Rule_2", "Correct_Answer"])
        
        for i, meta in enumerate(puzzles_meta):
            final_base = f"Puzzle_{i+1:03d}"
            temp_grid = os.path.join(OUTPUT_FOLDER, f"{meta['temp_name']}_grid.png")
            temp_ans  = os.path.join(OUTPUT_FOLDER, f"{meta['temp_name']}_answers.png")
            final_grid = os.path.join(OUTPUT_FOLDER, f"{final_base}_grid.png")
            final_ans  = os.path.join(OUTPUT_FOLDER, f"{final_base}_answers.png")
            
            if os.path.exists(temp_grid): shutil.move(temp_grid, final_grid)
            if os.path.exists(temp_ans):  shutil.move(temp_ans, final_ans)
            
            l_type = meta["logic_type"]
            rule1 = meta["rules"].get("Rule 1", "N/A")
            rule2 = meta["rules"].get("Rule 2", "N/A")
                
            writer.writerow([final_base, meta["score"], l_type, meta["target_cell"], rule1, rule2, meta["correct_ans_label"]])

    print(f"\nDone! Processed {num_puzzles} puzzles.")
