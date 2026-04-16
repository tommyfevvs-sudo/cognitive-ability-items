import os
import random
import math
import csv
import shutil
import copy
import itertools
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_grids_d")
ASSETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
TEMP_FOLDER   = os.path.join(OUTPUT_FOLDER, "temp")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(ASSETS_FOLDER, exist_ok=True)

# ── Font search paths ──────────────────────────────────────────────────────────
FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental", "C:/Windows/Fonts", "/usr/share/fonts/truetype",
    "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu",
]
FALLBACK_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

class GridDGenerator:
    def __init__(self):
        self.sf = 4 
        self.quad_size = 180 * self.sf 
        self.grid_line_w = int(4 * self.sf)
        self.border_w = int(6 * self.sf)
        self.pad = int(40 * self.sf)
        self.fps = 15
        self.frames = 60 
        
        self.cells = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
        self.polygons = ["Triangle", "Square", "Pentagon", "Hexagon", "Star", "Plus", "Irregular"]
        self.fills = ["Solid Black", "Solid Dark Grey", "White", "Lines", "Grid", "Honeycomb", "Basket Weave"]
        
        self.external_assets = [f for f in os.listdir(ASSETS_FOLDER) if f.lower().endswith('.png')]
        self.asset_cache = {} 
        self.current_puzzle_context = {}

        # ── Font Loading ───────────────────────────────────────────────────────
        self.font_hd = None
        found = False
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
                            found = True
                            break
                        except Exception: continue
                if found: break
            except Exception: continue

        if not found:
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd = ImageFont.truetype(fp, 44 * self.sf)
                        found = True
                        break
                    except Exception: continue
        if not found:
            self.font_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════
    # DRAWING ROUTINES
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_text_centered(self, draw, x, y, text):
        bbox = draw.textbbox((0, 0), text, font=self.font_hd)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x - tw // 2, y - th // 2), text, font=self.font_hd, fill="black")

    def draw_pattern(self, draw, bbox, fill_style):
        step = int(12 * self.sf)
        x_min, y_min, x_max, y_max = [int(v) for v in bbox]
        
        if fill_style == "Lines":
            for y in range(y_min, y_max, step):
                draw.line([(x_min, y), (x_max, y)], fill="black", width=int(1.5*self.sf))
        elif fill_style == "Grid":
            for y in range(y_min, y_max, step):
                draw.line([(x_min, y), (x_max, y)], fill="black", width=int(1.5*self.sf))
            for x in range(x_min, x_max, step):
                draw.line([(x, y_min), (x, y_max)], fill="black", width=int(1.5*self.sf))
        elif fill_style == "Basket Weave":
            step = int(16 * self.sf)
            for y in range(y_min, y_max, step):
                for x in range(x_min, x_max, step):
                    if (x // step + y // step) % 2 == 0:
                        for offset in range(0, step, int(4*self.sf)):
                            draw.line([(x, y+offset), (x+step, y+offset)], fill="black", width=max(1, int(1*self.sf)))
                    else:
                        for offset in range(0, step, int(4*self.sf)):
                            draw.line([(x+offset, y), (x+offset, y+step)], fill="black", width=max(1, int(1*self.sf)))
        elif fill_style == "Honeycomb":
            h_step = int(14 * self.sf)
            v_step = int(12 * self.sf)
            for row, y in enumerate(range(y_min, y_max, v_step)):
                offset = (h_step // 2) if row % 2 != 0 else 0
                for x in range(x_min - offset, x_max, h_step):
                    draw.regular_polygon((x, y, max(3, int(8*self.sf))), 6, outline="black", fill=None)

    def draw_polygon(self, target_img, cx, cy, radius, shape_type, fill_style, rot=0, custom_pts=None):
        temp_size = int(radius * 3)
        temp_img = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(temp_img)
        tcx, tcy = temp_size // 2, temp_size // 2

        points = []
        if shape_type in ["Triangle", "Square", "Pentagon", "Hexagon"]:
            sides = {"Triangle": 3, "Square": 4, "Pentagon": 5, "Hexagon": 6}[shape_type]
            for i in range(sides):
                angle = math.radians(rot + (i * 360 / sides) - 90)
                if shape_type == "Square": angle += math.radians(45)
                points.append((tcx + radius * math.cos(angle), tcy + radius * math.sin(angle)))
        elif shape_type == "Star":
            for i in range(10):
                angle = math.radians(rot + (i * 360 / 10) - 90)
                r = radius if i % 2 == 0 else radius * 0.4
                points.append((tcx + r * math.cos(angle), tcy + r * math.sin(angle)))
        elif shape_type == "Plus":
            w, h = radius * 0.3, radius
            base_pts = [(-w,-h), (w,-h), (w,-w), (h,-w), (h,w), (w,w), (w,h), (-w,h), (-w,w), (-h,w), (-h,-w), (-w,-w)]
            for bx, by in base_pts:
                rad_rot = math.radians(rot)
                rx = bx * math.cos(rad_rot) - by * math.sin(rad_rot)
                ry = bx * math.sin(rad_rot) + by * math.cos(rad_rot)
                points.append((tcx + rx, tcy + ry))
        elif shape_type == "Irregular" and custom_pts:
            for bx, by in custom_pts:
                bx, by = bx * radius, by * radius
                rad_rot = math.radians(rot)
                rx = bx * math.cos(rad_rot) - by * math.sin(rad_rot)
                ry = bx * math.sin(rad_rot) + by * math.cos(rad_rot)
                points.append((tcx + rx, tcy + ry))
        else: 
            sides = max(3, int(shape_type)) if str(shape_type).isdigit() else 3
            for i in range(sides):
                angle = math.radians(rot + (i * 360 / sides) - 90)
                points.append((tcx + radius * math.cos(angle), tcy + radius * math.sin(angle)))

        color = "black" if fill_style == "Solid Black" else "#555555" if fill_style == "Solid Dark Grey" else "white"
        outline_w = max(1, int(2.5*self.sf))
        poly_fill = "white" if fill_style not in ["Solid Black", "Solid Dark Grey"] else color
        
        draw.polygon(points, fill=poly_fill)
        line_points = points + [points[0]]
        draw.line(line_points, fill="black", width=outline_w, joint="curve")
        
        if fill_style not in ["Solid Black", "Solid Dark Grey", "White"]:
            bbox = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.polygon(points, fill=255)
            
            pattern_layer = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
            pat_draw = ImageDraw.Draw(pattern_layer)
            self.draw_pattern(pat_draw, bbox, fill_style)
            temp_img.paste(pattern_layer, (0,0), mask)
            draw.line(line_points, fill="black", width=outline_w, joint="curve")

        target_img.paste(temp_img, (int(cx - tcx), int(cy - tcy)), temp_img)

    def draw_asymmetric(self, target_img, cx, cy, radius, rot=0, flip_h=False, flip_v=False, asset_name=None):
        temp_size = int(radius * 3)
        temp_img = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(temp_img)
        tcx, tcy = temp_size // 2, temp_size // 2
        
        asset_loaded = False
        if asset_name and os.path.exists(os.path.join(ASSETS_FOLDER, asset_name)):
            try:
                if asset_name not in self.asset_cache:
                    asset_path = os.path.join(ASSETS_FOLDER, asset_name)
                    img = Image.open(asset_path).convert("RGBA")
                    pixels = img.load()
                    for y in range(img.height):
                        for x in range(img.width):
                            r, g, b, a = pixels[x, y]
                            if a < 20 or (r > 220 and g > 220 and b > 220): pixels[x, y] = (0, 0, 0, 0)
                            else: pixels[x, y] = (0, 0, 0, 255)
                    bbox = img.getbbox()
                    if bbox: img = img.crop(bbox)
                    self.asset_cache[asset_name] = img
                
                img = self.asset_cache[asset_name].copy()
                target_dim = max(1, int(radius * 2))
                img.thumbnail((target_dim, target_dim), Image.Resampling.LANCZOS)
                
                if flip_h: img = ImageOps.mirror(img)
                if flip_v: img = ImageOps.flip(img)
                if rot != 0: img = img.rotate(-rot, resample=Image.Resampling.BICUBIC, expand=True)
                
                paste_x, paste_y = tcx - img.width // 2, tcy - img.height // 2
                temp_img.paste(img, (paste_x, paste_y), img)
                asset_loaded = True
            except Exception as e:
                pass

        if not asset_loaded:
            pts = [(-radius*0.8, -radius), (-radius*0.2, -radius), (-radius*0.2, radius*0.4), (radius*0.8, radius*0.4), (radius*0.8, radius), (-radius*0.8, radius)]
            points = []
            for bx, by in pts:
                if flip_h: bx = -bx
                if flip_v: by = -by
                rad_rot = math.radians(rot)
                rx = bx * math.cos(rad_rot) - by * math.sin(rad_rot)
                ry = bx * math.sin(rad_rot) + by * math.cos(rad_rot)
                points.append((tcx + rx, tcy + ry))
            
            draw.polygon(points, fill="black")
            line_points = points + [points[0]]
            draw.line(line_points, fill="black", width=max(1, int(2.5*self.sf)), joint="curve")
            
        target_img.paste(temp_img, (int(cx - tcx), int(cy - tcy)), temp_img)

    def draw_cell_master(self, target_img, dx, dy, cell_data, frame_idx=0):
        if not cell_data: return
        
        # Create a bounding layer for this specific cell to act as a clipping mask
        cell_layer = Image.new("RGBA", (self.quad_size, self.quad_size), (255, 255, 255, 0))
        
        # Center of our local clipping layer
        cx, cy = self.quad_size // 2, self.quad_size // 2
        
        safe_factor = 0.60
        
        for obj in cell_data["objects"]:
            ox = cx + (obj["rel_x"] * self.quad_size * safe_factor)
            oy = cy + (obj["rel_y"] * self.quad_size * safe_factor)
            radius = (self.quad_size * obj["rel_size"] * obj["scale"] * safe_factor) / 2
            
            spin_offset = (frame_idx / self.frames) * 360 * obj.get("spin", 0)
            final_rot = obj["rot"] + spin_offset

            if obj["type"] == "poly":
                self.draw_polygon(cell_layer, ox, oy, radius, obj["shape"], obj["fill"], final_rot, obj.get("custom_pts"))
            else:
                self.draw_asymmetric(cell_layer, ox, oy, radius, final_rot, obj.get("flip_h"), obj.get("flip_v"), obj.get("asset"))

        # Paste the safely clipped cell layer onto the main target image
        target_img.paste(cell_layer, (int(dx), int(dy)), cell_layer)

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE MATH AND POSITIONS
    # ═══════════════════════════════════════════════════════════════════════════
    def quads_are_identical(self, q1, q2, has_spin):
        if not q1 or not q2: return False
        if len(q1["objects"]) != len(q2["objects"]): return False
        
        def get_visual_rot(obj):
            if obj["type"] != "poly": return obj["rot"] % 360
            shape = obj["shape"]
            sym = {"Triangle": 120, "Square": 90, "Pentagon": 72, "Hexagon": 60, "Star": 72, "Plus": 90}.get(shape, 360)
            if str(shape).isdigit(): sym = 360 / max(3, int(shape))
            return obj["rot"] % sym

        for o1, o2 in zip(q1["objects"], q2["objects"]):
            exact_checks = ["type", "shape", "fill", "flip_h", "flip_v", "asset"]
            if has_spin: exact_checks.append("spin")
            
            if any(o1.get(k) != o2.get(k) for k in exact_checks): return False
            
            float_checks = ["scale", "rel_x", "rel_y"]
            for k in float_checks:
                v1, v2 = o1.get(k, 0), o2.get(k, 0)
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    if abs(v1 - v2) > 0.01: return False
                elif v1 != v2: return False
            
            if abs(get_visual_rot(o1) - get_visual_rot(o2)) > 0.1: return False
        return True

    def get_grid_positions(self, count):
        if count <= 1: return [(0,0)], 0.8
        elif count == 2: return [(-0.25,0), (0.25,0)], 0.4
        elif count == 3: return [(-0.25,-0.25), (0,0), (0.25,0.25)], 0.35
        elif count == 4: return [(-0.25,-0.25), (0.25,-0.25), (-0.25,0.25), (0.25,0.25)], 0.35
        elif count == 5: return [(-0.25,-0.25), (0.25,-0.25), (0,0), (-0.25,0.25), (0.25,0.25)], 0.3
        elif count == 6: return [(-0.25,-0.25), (0,-0.25), (0.25,-0.25), (-0.25,0.25), (0,0.25), (0.25,0.25)], 0.28
        elif count == 7: return [(-0.3,-0.3), (0,-0.3), (0.3,-0.3), (0,0), (-0.3,0.3), (0,0.3), (0.3,0.3)], 0.25
        elif count == 8: return [(-0.3,-0.3), (0,-0.3), (0.3,-0.3), (-0.3,0), (0.3,0), (-0.3,0.3), (0,0.3), (0.3,0.3)], 0.25
        else: return [(-0.3,-0.3), (0,-0.3), (0.3,-0.3), (-0.3,0), (0,0), (0.3,0), (-0.3,0.3), (0,0.3), (0.3,0.3)], 0.25

    def generate_irregular_points(self):
        pts = []
        for i in range(6):
            angle = math.radians(i * 60 + random.randint(-15, 15))
            r = random.uniform(0.6, 1.0)
            pts.append((r * math.cos(angle), r * math.sin(angle)))
        return pts

    def get_step_map(self, structure):
        s_map = {}
        path1 = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
        path2 = ["A1", "A2", "A3", "B3", "B2", "B1", "C1", "C2", "C3"]
        col_path = ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]
        lat = [[0,1,2],[1,2,0],[2,0,1]]
        lat2 = [[1,2,0],[2,0,1],[0,1,2]]
        
        for r in range(3):
            for c in range(3):
                cell = f"{chr(65+c)}{r+1}"
                if structure == "path1": s_map[cell] = path1.index(cell)
                elif structure == "path2": s_map[cell] = path2.index(cell)
                elif structure == "col_path": s_map[cell] = col_path.index(cell)
                elif structure == "col_matrix": s_map[cell] = c
                elif structure == "row_matrix": s_map[cell] = r
                elif structure == "latin_sq": s_map[cell] = lat[r][c]
                elif structure == "latin_sq_2": s_map[cell] = lat2[r][c]
        return s_map

    # ═══════════════════════════════════════════════════════════════════════════
    # DYNAMIC LAYERING ENGINE WITH STRUCTURAL DECOUPLING
    # ═══════════════════════════════════════════════════════════════════════════
    def _generate_base(self, args):
        otype = "poly"
        shape = None
        
        must_be_poly = args.get("force_triangle") or args.get("force_poly")
        
        if not must_be_poly and self.external_assets and random.random() < 0.75:
            otype = "asym"
        else:
            otype = "poly"
            
        if otype == "poly":
            if args.get("force_triangle"):
                shape = "Triangle"
            elif args.get("requires_asymmetry"):
                shape = random.choice(["Triangle", "Pentagon", "Star", "Irregular"])
            else:
                shape = random.choice(self.polygons)
            
        spin = 0 
        rot = random.choice([0, 90, 180, 270])
        
        obj = {"type": otype, "scale": 1.0, "spin": spin, "rot": rot, "rel_x": 0, "rel_y": 0, "rel_size": 0.8}
        
        if args.get("is_corner"):
            obj["rel_size"] = 0.35
            obj["rel_x"] = -0.25
            obj["rel_y"] = -0.25
            
        if args.get("is_count"):
            obj["rel_size"] = 0.4
            
        if args.get("size_mod") == "inc": obj["scale"] = 0.4
        elif args.get("size_mod") == "dec": obj["scale"] = 1.2
            
        if otype == "poly":
            obj["shape"] = shape
            obj["fill"] = random.choice(self.fills)
            if obj["shape"] == "Irregular": 
                obj["custom_pts"] = self.generate_irregular_points()
        else:
            obj["asset"] = random.choice(self.external_assets) if self.external_assets else None
            obj["flip_h"] = random.choice([True, False])
            obj["flip_v"] = random.choice([True, False])
            obj["fill"] = "Solid Black" 
            
        return obj

    def get_effective_step(self, structure, step, rule):
        if structure in ["col_matrix", "row_matrix", "latin_sq", "latin_sq_2"]:
            if rule in ["size_inc", "size_dec"]:
                return step * 3
        return step

    def apply_transform(self, cell_data, t_type, step=1):
        new_data = copy.deepcopy(cell_data)
        for obj in new_data["objects"]:
            if t_type == "90_CW": obj["rot"] = (obj["rot"] + 90 * step) % 360
            elif t_type == "90_ACW": obj["rot"] = (obj["rot"] - 90 * step) % 360
            elif t_type == "180": obj["rot"] = (obj["rot"] + 180 * step) % 360
            elif t_type == "size_inc": obj["scale"] = min(1.2, obj["scale"] + 0.1 * step) 
            elif t_type == "size_dec": obj["scale"] = max(0.3, obj["scale"] - 0.1 * step) 
            elif t_type == "size_cycle_3":
                scales = [0.5, 0.8, 1.1]
                try: curr_idx = scales.index(obj["scale"])
                except ValueError: curr_idx = min(range(len(scales)), key=lambda i: abs(scales[i] - obj["scale"]))
                obj["scale"] = scales[(curr_idx + step) % 3]
            elif t_type == "spin_alt":
                if obj["spin"] == 0: obj["spin"] = 1 
                obj["spin"] = obj["spin"] * (-1 if step % 2 != 0 else 1)
            elif t_type in ["fill_alt", "fill_cycle_3", "fill_cycle_4"]:
                if obj["type"] == "poly":
                    try: idx = self.fills.index(obj["fill"])
                    except ValueError: idx = 0
                    mod_val = 2 if t_type == "fill_alt" else (4 if t_type == "fill_cycle_4" else 3)
                    obj["fill"] = self.fills[(idx + (step % mod_val)) % len(self.fills)]
            elif t_type == "sides_inc":
                if obj["type"] == "poly":
                    base_sides = {"Triangle": 3, "Square": 4, "Pentagon": 5, "Hexagon": 6}.get(obj["shape"])
                    if base_sides is None:
                        if str(obj["shape"]).isdigit(): base_sides = int(obj["shape"])
                        else: base_sides = 3 
                    new_sides = 3 + ((base_sides - 3 + step) % 4)
                    shape_map = {3: "Triangle", 4: "Square", 5: "Pentagon", 6: "Hexagon"}
                    obj["shape"] = shape_map.get(new_sides, str(new_sides))
            elif t_type == "sides_dec":
                if obj["type"] == "poly":
                    base_sides = {"Triangle": 3, "Square": 4, "Pentagon": 5, "Hexagon": 6}.get(obj["shape"])
                    if base_sides is None:
                        if str(obj["shape"]).isdigit(): base_sides = int(obj["shape"])
                        else: base_sides = 3 
                    new_sides = 3 + ((base_sides - 3 - step) % 4)
                    shape_map = {3: "Triangle", 4: "Square", 5: "Pentagon", 6: "Hexagon"}
                    obj["shape"] = shape_map.get(new_sides, str(new_sides))
            elif t_type == "corners_cw":
                corners = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]
                try: idx = corners.index((obj["rel_x"], obj["rel_y"]))
                except ValueError: idx = 0
                nx, ny = corners[(idx + step) % 4]
                obj["rel_x"], obj["rel_y"] = nx, ny
        return new_data

    def _generate_cell(self, cell_id, c, ignore_extra=False):
        base_pool = c["base_pool"]
        base_val = c["base_val"]
        extra_rules = c["extra_rules"] if not ignore_extra else []
        
        base_struct = c["rule_structs"]["base"]
        base_step = self.get_step_map(base_struct)[cell_id]
        
        cell_data = {"objects": []}
        
        if base_pool == "fill" and isinstance(base_val, list):
            obj = copy.deepcopy(c["base_obj"])
            obj["fill"] = base_val[base_step % len(base_val)]
            cell_data["objects"] = [obj]
        elif base_val in ["3_diff_shape", "3_diff_size"]:
            obj = copy.deepcopy(c["bases"][base_step % 3])
            cell_data["objects"] = [obj]
        elif base_pool == "count":
            base_key = str(base_val)
            eff_step = self.get_effective_step(base_struct, base_step, base_val) * c["strides"].get(base_key, 1)
            
            if base_val == "count_inc":
                cnt = c["start_n"] + eff_step
            else:
                cnt = c["start_n"] - eff_step
                
            cnt = max(1, min(9, cnt))
            
            positions, scale = self.get_grid_positions(cnt)
            for p in positions:
                obj = copy.deepcopy(c["base_obj"])
                obj["rel_x"], obj["rel_y"] = p
                obj["rel_size"] = scale
                cell_data["objects"].append(obj)
        else:
            base_key = str(base_val)
            eff_step = self.get_effective_step(base_struct, base_step, base_val) * c["strides"].get(base_key, 1)
            temp_quad = {"objects": [copy.deepcopy(c["base_obj"])]}
            temp_quad = self.apply_transform(temp_quad, base_val, eff_step)
            cell_data = temp_quad
            
        for r in extra_rules:
            r_struct = c["rule_structs"][r]
            r_step = self.get_step_map(r_struct)[cell_id]
            eff_step = (self.get_effective_step(r_struct, r_step, r) * c["strides"][r]) + c["offsets"][r]
            cell_data = self.apply_transform(cell_data, r, eff_step)
            
        return cell_data

    def build_grid_logic(self):
        BASE_LOGICS = [
            ("90 degree Clockwise rotation Path 1", "orientation", "path1", "90_CW", 3),
            ("90 degree Clockwise rotation Path 2", "orientation", "path2", "90_CW", 3),
            ("90 degree anticlockwise rotation Path 1", "orientation", "path1", "90_ACW", 3),
            ("90 degree anticlockwise rotation Path 2", "orientation", "path2", "90_ACW", 3),
            ("180 degree Clockwise rotation Path 1", "orientation", "path1", "180", 2),
            ("180 degree Clockwise rotation Path 2", "orientation", "path2", "180", 2),
            ("180 degree anticlockwise rotation Path 1", "orientation", "path1", "180", 2),
            ("180 degree anticlockwise rotation Path 2", "orientation", "path2", "180", 2),
            ("Alternating Spin Path 1", "orientation", "path1", "spin_alt", 5),
            ("Alternating Spin Path 2", "orientation", "path2", "spin_alt", 5),
            
            ("Col A grey, Col B white, Col C black", "fill", "col_matrix", ["Solid Dark Grey", "White", "Solid Black"], 2),
            ("Col C grey, Col B white, Col A black", "fill", "col_matrix", ["Solid Black", "White", "Solid Dark Grey"], 2),
            ("Col A white, Col B black, Col C grey", "fill", "col_matrix", ["White", "Solid Black", "Solid Dark Grey"], 2),
            ("Col A black, Col B grey, Col C white", "fill", "col_matrix", ["Solid Black", "Solid Dark Grey", "White"], 2),
            ("Row 1 grey, Row 2 white, Row 3 black", "fill", "row_matrix", ["Solid Dark Grey", "White", "Solid Black"], 2),
            ("Row 2 grey, Row 1 white, Row 3 black", "fill", "row_matrix", ["White", "Solid Dark Grey", "Solid Black"], 2),
            ("Row 2 grey, Row 3 white, Row 1 black", "fill", "row_matrix", ["Solid Black", "Solid Dark Grey", "White"], 2),
            ("Latin square of fills 1", "fill", "latin_sq", ["Solid Black", "White", "Solid Dark Grey"], 6),
            ("Latin square of fills 2", "fill", "latin_sq_2", ["White", "Solid Black", "Solid Dark Grey"], 6),
            ("Latin square of fills 3", "fill", "latin_sq", ["Solid Dark Grey", "Solid Black", "White"], 6),
            ("Latin square of fills 4", "fill", "latin_sq_2", ["White", "Solid Dark Grey", "Solid Black"], 6),
            
            ("Size increase Path 1", "size", "path1", "size_inc", 4),
            ("Size increase Path 2", "size", "path2", "size_inc", 4),
            ("Size increase Col A -> Col B -> Col C", "size", "col_matrix", "size_inc", 5),
            ("Size increase Row 1 -> Row 2 -> Row 3", "size", "row_matrix", "size_inc", 5),
            ("Size inc Latin Square", "size", "latin_sq", "size_inc", 7),
            ("Size dec Latin Square", "size", "latin_sq", "size_dec", 7),
            ("3 Diff anchor size A1, B1, C1 -> Latin sq", "size", "latin_sq", "3_diff_size", 7),
            
            ("3 Diff anchor objects A1, B1, C1 -> Latin Sq", "shape", "latin_sq", "3_diff_shape", 8),
            ("Shape Sides Inc Cols", "shape", "col_matrix", "sides_inc", 4),
            ("Shape Sides Dec Cols", "shape", "col_matrix", "sides_dec", 4),
            ("Shape Sides Inc Rows", "shape", "row_matrix", "sides_inc", 4),
            ("Shape Sides Dec Rows", "shape", "row_matrix", "sides_dec", 4),
            
            ("Count inc Col Path", "count", "col_path", "count_inc", 6),
            ("Count dec Col Path", "count", "col_path", "count_dec", 6),
            ("Count inc Row Path", "count", "path1", "count_inc", 6),
            ("Count dec Row Path", "count", "path1", "count_dec", 6),
            ("Count inc Latin Sq", "count", "latin_sq", "count_inc", 8),
            ("Count dec Latin Sq", "count", "latin_sq", "count_dec", 8),
            
            ("Corner Move CW Path 2", "corner", "path2", "corners_cw", 7),
            ("Corner Move CW Path 1", "corner", "path1", "corners_cw", 7)
        ]

        base_name, base_pool, structure, base_val, base_score = random.choice(BASE_LOGICS)
        
        available_layer_rules = {
            "orientation": ["90_CW", "90_ACW", "180", "spin_alt"],
            "fill": ["fill_alt", "fill_cycle_3", "fill_cycle_4"],
            "size": ["size_cycle_3"], 
            "shape": ["sides_inc", "sides_dec"],
            "corner": ["corners_cw"]
        }
        
        used_pools = {base_pool}
        extra_rules = []
        num_layers = random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0] 
        
        for _ in range(num_layers):
            possible_pools = []
            for p, rules in available_layer_rules.items():
                if p in used_pools: continue
                if base_pool == "count" and p in ["size", "corner"]: continue
                if "count" in used_pools and p in ["size", "corner"]: continue
                if "orientation" in used_pools and p == "shape": continue
                if "shape" in used_pools and p == "orientation": continue
                possible_pools.append(p)
                
            if not possible_pools: break
            chosen_pool = random.choice(possible_pools)
            chosen_rule = random.choice(available_layer_rules[chosen_pool])
            extra_rules.append(chosen_rule)
            used_pools.add(chosen_pool)

        has_sides_rule = "sides_inc" in extra_rules or "sides_dec" in extra_rules or base_val in ["sides_inc", "sides_dec"]

        base_obj_args = {
            "allow_spin": False,
            "requires_asymmetry": "orientation" in used_pools,
            "force_triangle": has_sides_rule,
            "force_poly": "fill" in used_pools,
            "is_corner": "corner" in used_pools,
            "is_count": "count" in used_pools,
            "size_mod": None
        }
        
        if "size_inc" in extra_rules or base_val == "size_inc": base_obj_args["size_mod"] = "inc"
        if "size_dec" in extra_rules or base_val == "size_dec": base_obj_args["size_mod"] = "dec"
        
        base_obj = None
        bases = []
        start_n = 0
        
        if base_val == "3_diff_shape":
            use_assets = False
            if not base_obj_args.get("force_poly") and self.external_assets and len(self.external_assets) >= 3 and random.random() < 0.5:
                use_assets = True
                
            bases = []
            if use_assets:
                chosen_assets = random.sample(self.external_assets, 3)
                for i in range(3):
                    b = self._generate_base(base_obj_args)
                    b["type"] = "asym"
                    b["asset"] = chosen_assets[i]
                    bases.append(b)
            else:
                chosen_shapes = random.sample(self.polygons, 3)
                for i in range(3):
                    b = self._generate_base(base_obj_args)
                    b["type"] = "poly"
                    b["shape"] = chosen_shapes[i]
                    bases.append(b)
        elif base_val == "3_diff_size":
            b = self._generate_base(base_obj_args)
            bases = [copy.deepcopy(b) for _ in range(3)]
            bases[0]["scale"], bases[1]["scale"], bases[2]["scale"] = 0.5, 0.8, 1.2
        elif base_pool == "count":
            base_obj = self._generate_base(base_obj_args)
            if structure in ["path1", "path2", "col_path"]:
                if base_val == "count_inc": start_n = 1
                else: start_n = 9
            else:
                if base_val == "count_inc": start_n = random.randint(1, 7)
                else: start_n = random.randint(3, 9)
        else:
            base_obj = self._generate_base(base_obj_args)
            
        c = {
            "base_obj": base_obj, "bases": bases, "start_n": start_n,
            "base_pool": base_pool, "base_val": base_val, "extra_rules": extra_rules,
            "structure": structure, "used_pools": list(used_pools)
        }
        
        c["rule_structs"] = {}
        c["strides"] = {"base": 1}
        c["offsets"] = {"base": 0}
        
        if structure in ["col_matrix", "row_matrix", "latin_sq"]:
            struct_options = ["col_matrix", "row_matrix", "latin_sq", "latin_sq_2"]
            if structure in struct_options: struct_options.remove(structure)
            random.shuffle(struct_options)
            
            c["rule_structs"]["base"] = structure
            for r in extra_rules:
                c["rule_structs"][r] = struct_options.pop() if struct_options else random.choice(["col_matrix", "row_matrix"])
                c["strides"][r] = 1 
                c["offsets"][r] = 0 
        else:
            c["rule_structs"]["base"] = structure
            strides = [1, -1, 5, -5]
            random.shuffle(strides)
            for r in extra_rules:
                c["rule_structs"][r] = structure
                c["strides"][r] = strides.pop()
                c["offsets"][r] = random.randint(1, 3)

        self.current_puzzle_context = c

        quads = {cell: {"objects": []} for cell in self.cells}
        
        for cell in self.cells:
            quads[cell] = self._generate_cell(cell, c)
            
        r1 = base_name
        r2 = extra_rules[0] if len(extra_rules) > 0 else "N/A"
        r3 = extra_rules[1] if len(extra_rules) > 1 else "N/A"
        
        final_score = base_score + (len(extra_rules) * 3)
        has_spin = any(o.get("spin", 0) != 0 for cell_data in quads.values() for o in cell_data["objects"])
        context_out = {"r1": r1, "r2": r2, "r3": r3, "path": structure}
        
        return quads, r1, final_score, has_spin, context_out

    # ═══════════════════════════════════════════════════════════════════════════
    # DISTRACTOR OPTIONS - SELF AWARE & TARGETED
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_options(self, target_cell, quads, context, has_spin):
        target_quad = quads[target_cell]
        options = [copy.deepcopy(target_quad)]
        distractors = []
        labels = ["A", "B", "C", "D", "E"]
        
        def add_distractor(candidate):
            # ONLY check against other options to ensure the answer strip has 5 unique choices.
            if any(self.quads_are_identical(candidate, opt, has_spin) for opt in options + distractors):
                return False
            distractors.append(candidate)
            return True

        c = self.current_puzzle_context
        active_pools = c.get("used_pools", [])
        is_complex = len(c.get("extra_rules", [])) > 0
        
        # Catalog exactly what exists in the grid to enforce variable consistency
        grid_fills = set()
        grid_shapes = set()
        grid_counts = set()
        grid_assets = set()
        grid_scales = set()
        grid_rots = set()
        grid_corners = set()
        
        for cell_id, cell_data in quads.items():
            grid_counts.add(len(cell_data["objects"]))
            for o in cell_data["objects"]:
                if "fill" in o: grid_fills.add(o["fill"])
                if "shape" in o: grid_shapes.add(str(o["shape"]))
                if "asset" in o and o["asset"] is not None: grid_assets.add(o["asset"])
                if "scale" in o: grid_scales.add(o["scale"])
                if "rot" in o: grid_rots.add(o["rot"] % 360)
                grid_corners.add((o.get("rel_x", 0), o.get("rel_y", 0)))

        # 1. Step Errors (Always Safe)
        if c["structure"] in ["path1", "path2", "col_path"]:
            path_map = {
                "path1": ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"],
                "path2": ["A1", "A2", "A3", "B3", "B2", "B1", "C1", "C2", "C3"],
                "col_path": ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]
            }
            path_list = path_map[c["structure"]]
            idx = path_list.index(target_cell)
            if idx > 0: add_distractor(self._generate_cell(path_list[idx - 1], c))
            if idx < 8: add_distractor(self._generate_cell(path_list[idx + 1], c))
            
        if len(c.get("extra_rules", [])) > 0:
            d_partial = self._generate_cell(target_cell, c, ignore_extra=True)
            add_distractor(d_partial)

        # 2. Targeted Dimension Errors (Strictly Curated)
        active_mutators = []

        def break_orientation(q):
            nq = copy.deepcopy(q)
            for o in nq["objects"]: 
                o["rot"] = (o["rot"] + random.choice([90, 180, 270])) % 360
            return nq
        if len(grid_rots) > 1 or "orientation" in active_pools:
            active_mutators.append(break_orientation)
            
        def break_spin(q):
            nq = copy.deepcopy(q)
            for o in nq["objects"]: 
                o["spin"] = o.get("spin", 1) * -1
            return nq
        if has_spin:
            active_mutators.append(break_spin)
            
        def break_size(q):
            nq = copy.deepcopy(q)
            for o in nq["objects"]: 
                avail = list(grid_scales - {o["scale"]})
                if avail: o["scale"] = random.choice(avail)
                else: o["scale"] = 1.1 if o["scale"] < 1.0 else 0.5
            return nq
        if len(grid_scales) > 1 or "size" in active_pools:
            active_mutators.append(break_size)
            
        def break_fill(q):
            nq = copy.deepcopy(q)
            for o in nq["objects"]:
                if o["type"] == "poly":
                    avail = list(grid_fills - {o["fill"]})
                    if avail: o["fill"] = random.choice(avail)
                elif o["type"] == "asym":
                    o["flip_v"] = not o.get("flip_v", False)
            return nq
        if len(grid_fills) > 1 or "fill" in active_pools:
            active_mutators.append(break_fill)
            
        def break_shape(q):
            nq = copy.deepcopy(q)
            for o in nq["objects"]:
                if o["type"] == "poly":
                    avail = list(grid_shapes - {str(o["shape"])})
                    if avail:
                        new_shape = random.choice(avail)
                        o["shape"] = new_shape
                        if new_shape == "Irregular": o["custom_pts"] = self.generate_irregular_points()
                elif o["type"] == "asym":
                    avail = list(grid_assets - {o.get("asset")})
                    if avail: o["asset"] = random.choice(avail)
            return nq
        if len(grid_shapes) > 1 or len(grid_assets) > 1 or "shape" in active_pools:
            active_mutators.append(break_shape)
            
        def break_corner(q):
            nq = copy.deepcopy(q)
            corners = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]
            for o in nq["objects"]:
                try: idx = corners.index((o["rel_x"], o["rel_y"]))
                except ValueError: idx = 0
                nx, ny = corners[(idx + random.choice([1, 2, 3])) % 4]
                o["rel_x"], o["rel_y"] = nx, ny
            return nq
        if len(grid_corners) > 1 or "corner" in active_pools:
            active_mutators.append(break_corner)

        def break_count(q):
            nq = copy.deepcopy(q)
            if not nq["objects"]: return nq
            current_count = len(nq["objects"])
            avail = list(grid_counts - {current_count})
            if avail:
                new_count = random.choice(avail)
                positions, scale = self.get_grid_positions(new_count)
                base_o = nq["objects"][0]
                nq["objects"] = []
                for p in positions:
                    o = copy.deepcopy(base_o)
                    o["rel_x"], o["rel_y"] = p
                    o["rel_size"] = scale
                    nq["objects"].append(o)
            return nq
        if len(grid_counts) > 1 or "count" in active_pools:
            active_mutators.append(break_count)

        # Extreme edge case failsafe if no valid mutators match the grid setup
        if not active_mutators:
            active_mutators.append(break_orientation)

        # ── SYSTEMATIC LOGIC ERROR BLUEPRINTS ──
        num_mutators = len(active_mutators)
        blueprints = []
        
        if num_mutators == 1:
            # If 1 rule changes, just repeatedly break that 1 rule
            blueprints = [[active_mutators[0]]] * 4
        elif num_mutators == 2:
            # If 2 rules change, break A, break B, break both, and break a random one
            blueprints = [
                [active_mutators[0]], 
                [active_mutators[1]], 
                [active_mutators[0], active_mutators[1]], 
                [random.choice(active_mutators)]
            ]
        else:
            # If 3 (or more) rules change, ensure we get single logic errors and paired logic errors
            blueprints = [
                [active_mutators[0]],
                [active_mutators[1]],
                [active_mutators[0], active_mutators[1]],
                [active_mutators[1], active_mutators[2]]
            ]
        
        random.shuffle(blueprints)
        
        failsafe_counter = 0
        for bp in blueprints:
            valid = False
            attempts = 0
            while not valid and attempts < 100:
                candidate = copy.deepcopy(target_quad)
                # Apply the specific combination of mutators required by this blueprint
                for mutator in bp:
                    candidate = mutator(candidate)
                    
                if add_distractor(candidate): 
                    valid = True
                attempts += 1
                
            if not valid:
                failsafe_counter += 1
                fb = copy.deepcopy(target_quad)
                for o in fb["objects"]:
                    if len(grid_rots) > 1 or "orientation" in active_pools:
                        o["rot"] = (o["rot"] + 45 + (17 * failsafe_counter)) % 360
                    elif len(grid_scales) > 1 or "size" in active_pools:
                        o["scale"] = o["scale"] * max(0.4, (0.85 - (0.05 * (failsafe_counter % 10))))
                    elif has_spin:
                        o["spin"] = o.get("spin", 1) * -1 if failsafe_counter % 2 == 1 else 1
                    else:
                        o["rot"] = (o["rot"] + 15 + (15 * failsafe_counter)) % 360
                add_distractor(fb)

        distractors = distractors[:4]
        options.extend(distractors)
        random.shuffle(options)
        return options, labels[options.index(target_quad)]

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDERING ENGINE
    # ═══════════════════════════════════════════════════════════════════════════
    def render_puzzle(self, filename_base, quads, options, target_cell, has_spin):
        grid_dim = self.quad_size * 3 + self.grid_line_w * 2 + self.border_w * 2 + self.pad * 2
        ans_w = self.quad_size * 5 + self.pad * 6
        ans_h = self.quad_size + self.pad * 4 + int(100 * self.sf) 
        
        frames_grid = []
        frames_ans = []
        total_frames = self.frames if has_spin else 1
        
        coords = {}
        for r in range(3):
            for c in range(3):
                cell = f"{chr(65+c)}{r+1}"
                cx = self.pad + self.border_w + c * (self.quad_size + self.grid_line_w)
                cy = self.pad + self.border_w + r * (self.quad_size + self.grid_line_w)
                coords[cell] = (cx, cy)

        for f in range(total_frames):
            g_img = Image.new("RGBA", (grid_dim, grid_dim), "white")
            g_draw = ImageDraw.Draw(g_img)
            
            g_draw.rectangle([self.pad, self.pad, grid_dim - self.pad, grid_dim - self.pad], outline="black", width=self.border_w)
            
            for i in range(1, 3):
                vx = self.pad + self.border_w + i * self.quad_size + (i - 1) * self.grid_line_w
                g_draw.rectangle([vx, self.pad, vx + self.grid_line_w, grid_dim - self.pad], fill="black")
                hy = self.pad + self.border_w + i * self.quad_size + (i - 1) * self.grid_line_w
                g_draw.rectangle([self.pad, hy, grid_dim - self.pad, hy + self.grid_line_w], fill="black")

            for cell, q_data in quads.items():
                if cell != target_cell:
                    self.draw_cell_master(g_img, coords[cell][0], coords[cell][1], q_data, frame_idx=f)
            
            a_img = Image.new("RGBA", (ans_w, ans_h), "white")
            a_draw = ImageDraw.Draw(a_img)
            labels = ["A", "B", "C", "D", "E"]
            
            for idx, opt in enumerate(options):
                ox = self.pad + idx * (self.quad_size + self.pad)
                oy = self.pad
                
                self.draw_cell_master(a_img, ox, oy, opt, frame_idx=f)
                a_draw.rectangle([ox, oy, ox + self.quad_size, oy + self.quad_size], outline="black", width=self.border_w)
                
                lbl_y = oy + self.quad_size + int(60 * self.sf)
                self.draw_text_centered(a_draw, ox + self.quad_size // 2, lbl_y, labels[idx])

            grid_bd = ImageOps.invert(g_img.convert("RGB")).getbbox()
            ans_bd = ImageOps.invert(a_img.convert("RGB")).getbbox()

            top_pad, bottom_pad = int(10 * self.sf), int(10 * self.sf) 

            grid_top, grid_bottom = max(0, grid_bd[1] - top_pad), min(g_img.height, grid_bd[3] + bottom_pad)
            grid_tight_h = grid_bottom - grid_top

            ans_top, ans_bottom = max(0, ans_bd[1] - top_pad), min(a_img.height, ans_bd[3] + bottom_pad)
            ans_tight_h = ans_bottom - ans_top

            grid_content_w = grid_bd[2] - grid_bd[0]
            ans_content_w = ans_bd[2] - ans_bd[0]

            grid_169_w = int(grid_tight_h * (16 / 9))
            master_w = max(grid_169_w, ans_content_w)

            final_grid_hd = Image.new("RGBA", (master_w, grid_tight_h), "white")
            grid_content = g_img.crop((grid_bd[0], grid_top, grid_bd[2], grid_bottom))
            
            final_ans_hd = Image.new("RGBA", (master_w, ans_tight_h), "white")
            ans_content = a_img.crop((ans_bd[0], ans_top, ans_bd[2], ans_bottom))

            final_grid_hd.paste(grid_content, ((master_w - grid_content_w) // 2, 0))
            final_ans_hd.paste(ans_content, ((master_w - ans_content_w) // 2, 0))

            final_grid = final_grid_hd.resize((final_grid_hd.width // self.sf, final_grid_hd.height // self.sf), Image.Resampling.LANCZOS)
            final_ans = final_ans_hd.resize((final_ans_hd.width // self.sf, final_ans_hd.height // self.sf), Image.Resampling.LANCZOS)

            frames_grid.append(final_grid)
            frames_ans.append(final_ans)

        ext = "gif" if has_spin else "png"
        g_path = os.path.join(TEMP_FOLDER, f"{filename_base}_grid.{ext}")
        a_path = os.path.join(TEMP_FOLDER, f"{filename_base}_ans.{ext}")
        
        if has_spin:
            frames_grid[0].save(g_path, save_all=True, append_images=frames_grid[1:], duration=1000//self.fps, loop=0)
            frames_ans[0].save(a_path, save_all=True, append_images=frames_ans[1:], duration=1000//self.fps, loop=0)
        else:
            frames_grid[0].save(g_path)
            frames_ans[0].save(a_path)


if __name__ == "__main__":
    print("=" * 40)
    print("Design Grid D Generator (3x3 NVR)")
    print("=" * 40)

    try:
        user_input = input("How many puzzles to generate? ")
        num_puzzles = int(user_input)
    except ValueError:
        num_puzzles = 1

    generator = GridDGenerator()
    puzzles_meta = []
    
    print("\nGenerating...")
    for i in range(num_puzzles):
        target_cell = random.choice(generator.cells)
        
        quads, logic_name, diff_score, has_spin, context = generator.build_grid_logic()
        options, correct_ans = generator.generate_options(target_cell, quads, context, has_spin)
        
        temp_base = f"temp_{i:04d}"
        generator.render_puzzle(temp_base, quads, options, target_cell, has_spin)
        
        puzzles_meta.append({
            "temp": temp_base, "score": diff_score, "logic": logic_name, 
            "target": target_cell, "ans": correct_ans, "ext": "gif" if has_spin else "png",
            "r1": context.get("r1", "N/A"), "r2": context.get("r2", "N/A"), "r3": context.get("r3", "N/A"), 
            "path": context.get("path", "N/A")
        })

    print("Sorting & Saving Manifest...")
    puzzles_meta.sort(key=lambda x: (x["score"], x["logic"])) 
    
    manifest_path = os.path.join(OUTPUT_FOLDER, "Puzzle_Manifest.csv")
    with open(manifest_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Difficulty_Score", "Target_Cell", "Answer", "Rule_1", "Rule_2", "Rule_3", "Grid_Path_Sequence"])
        
        for i, meta in enumerate(puzzles_meta):
            final_base = f"Puzzle_{i+1:03d}"
            
            shutil.move(os.path.join(TEMP_FOLDER, f"{meta['temp']}_grid.{meta['ext']}"), 
                        os.path.join(OUTPUT_FOLDER, f"{final_base}_grid.{meta['ext']}"))
            shutil.move(os.path.join(TEMP_FOLDER, f"{meta['temp']}_ans.{meta['ext']}"), 
                        os.path.join(OUTPUT_FOLDER, f"{final_base}_answers.{meta['ext']}"))
                        
            writer.writerow([final_base, meta["score"], meta["target"], meta["ans"], meta["r1"], meta["r2"], meta["r3"], meta["path"]])
            
    shutil.rmtree(TEMP_FOLDER)
    print(f"\nDone! Processed {num_puzzles} puzzles into 'NVR_grids_d' folder on your Desktop.")
