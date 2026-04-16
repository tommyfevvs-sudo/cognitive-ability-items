import os
import random
import math
import csv
import shutil
import copy
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_grids_c")
ASSETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
TEMP_FOLDER   = os.path.join(OUTPUT_FOLDER, "temp")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(ASSETS_FOLDER, exist_ok=True)

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

class GridCGenerator:
    def __init__(self):
        self.sf = 4 # Supersampling factor for pristine rendering
        self.quad_size = 200 * self.sf
        self.grid_line_w = int(4 * self.sf)
        self.border_w = int(6 * self.sf)
        self.pad = int(40 * self.sf)
        self.fps = 15
        self.frames = 30 # 2-second loop for GIFs
        
        self.polygons = ["Triangle", "Square", "Pentagon", "Hexagon", "Star", "Plus"]
        self.fills = ["Solid Black", "Solid Dark Grey", "White", "Lines", "Grid", "Honeycomb", "Basket Weave"]
        
        self.external_assets = [f for f in os.listdir(ASSETS_FOLDER) if f.lower().endswith('.png')]
        self.asset_cache = {} # Caches processed PNGs to prevent disk-read hang

        # ── Font Loading ───────────────────────────────────────────────────────
        self.font_hd = None
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

    def draw_polygon(self, target_img, cx, cy, radius, shape_type, fill_style, rot=0):
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

        color = "black" if fill_style == "Solid Black" else "#555555" if fill_style == "Solid Dark Grey" else "white"
        
        draw.polygon(points, fill="white" if fill_style not in ["Solid Black", "Solid Dark Grey"] else color, outline="black", width=max(1, int(2.5*self.sf)))
        
        if fill_style not in ["Solid Black", "Solid Dark Grey", "White"]:
            bbox = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.polygon(points, fill=255)
            
            pattern_layer = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
            pat_draw = ImageDraw.Draw(pattern_layer)
            self.draw_pattern(pat_draw, bbox, fill_style)
            temp_img.paste(pattern_layer, (0,0), mask)
            draw.polygon(points, fill=None, outline="black", width=max(1, int(2.5*self.sf)))

        target_img.paste(temp_img, (int(cx - tcx), int(cy - tcy)), temp_img)

    def draw_asymmetric(self, target_img, cx, cy, radius, rot=0, flip_h=False, flip_v=False, asset_name=None):
        temp_size = int(radius * 3)
        temp_img = Image.new("RGBA", (temp_size, temp_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(temp_img)
        tcx, tcy = temp_size // 2, temp_size // 2
        
        asset_loaded = False
        if asset_name and os.path.exists(os.path.join(ASSETS_FOLDER, asset_name)):
            try:
                # Optimized disk-read caching
                if asset_name not in self.asset_cache:
                    asset_path = os.path.join(ASSETS_FOLDER, asset_name)
                    img = Image.open(asset_path).convert("RGBA")
                    
                    pixels = img.load()
                    for y in range(img.height):
                        for x in range(img.width):
                            r, g, b, a = pixels[x, y]
                            if a < 20 or (r > 220 and g > 220 and b > 220):
                                pixels[x, y] = (0, 0, 0, 0)
                            else:
                                pixels[x, y] = (0, 0, 0, 255)
                    
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)
                    
                    self.asset_cache[asset_name] = img
                
                img = self.asset_cache[asset_name].copy()
                target_dim = max(1, int(radius * 2))
                img.thumbnail((target_dim, target_dim), Image.Resampling.LANCZOS)
                
                if flip_h: img = ImageOps.mirror(img)
                if flip_v: img = ImageOps.flip(img)
                if rot != 0: img = img.rotate(-rot, resample=Image.Resampling.BICUBIC, expand=True)
                
                paste_x = tcx - img.width // 2
                paste_y = tcy - img.height // 2
                temp_img.paste(img, (paste_x, paste_y), img)
                asset_loaded = True
            except Exception as e:
                print(f"Error loading asset {asset_name}: {e}")

        if not asset_loaded:
            # Fallback L-Shape flag
            pts = [(-radius*0.8, -radius), (-radius*0.2, -radius), (-radius*0.2, radius*0.4), (radius*0.8, radius*0.4), (radius*0.8, radius), (-radius*0.8, radius)]
            points = []
            for bx, by in pts:
                if flip_h: bx = -bx
                if flip_v: by = -by
                rad_rot = math.radians(rot)
                rx = bx * math.cos(rad_rot) - by * math.sin(rad_rot)
                ry = bx * math.sin(rad_rot) + by * math.cos(rad_rot)
                points.append((tcx + rx, tcy + ry))
                
            draw.polygon(points, fill="black", outline="black", width=max(1, int(2.5*self.sf)))
            
        target_img.paste(temp_img, (int(cx - tcx), int(cy - tcy)), temp_img)

    def draw_quadrant_master(self, target_img, dx, dy, quad, frame_idx=0):
        if not quad: return
        cx, cy = dx + self.quad_size // 2, dy + self.quad_size // 2
        
        for obj in quad["objects"]:
            ox = cx + (obj["rel_x"] * self.quad_size)
            oy = cy + (obj["rel_y"] * self.quad_size)
            radius = (self.quad_size * obj["rel_size"] * obj["scale"]) / 2
            
            spin_offset = (frame_idx / self.frames) * 360 * obj.get("spin", 0)
            final_rot = obj["rot"] + spin_offset

            if obj["type"] == "poly":
                self.draw_polygon(target_img, ox, oy, radius, obj["shape"], obj["fill"], final_rot)
            else:
                self.draw_asymmetric(target_img, ox, oy, radius, final_rot, obj.get("flip_h"), obj.get("flip_v"), obj.get("asset"))

    # ═══════════════════════════════════════════════════════════════════════════
    # FAST MATH UNIQUENESS CHECKER
    # ═══════════════════════════════════════════════════════════════════════════
    def quads_are_identical(self, q1, q2):
        if not q1 or not q2: return False
        if len(q1["objects"]) != len(q2["objects"]): return False
        for o1, o2 in zip(q1["objects"], q2["objects"]):
            checks = ["type", "shape", "fill", "scale", "flip_h", "flip_v", "spin", "asset", "rel_x", "rel_y"]
            if any(o1.get(k) != o2.get(k) for k in checks): return False
            if o1["type"] == "poly" and (o1["rot"] % 360) != (o2["rot"] % 360): return False
            if o1["type"] == "asym" and (o1["rot"] % 360) != (o2["rot"] % 360): return False
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # QUADRANT GENERATION & MACRO LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_seed_quadrant(self, num_subs):
        quad = {"layout": num_subs, "objects": []}
        
        scale1 = random.choice([1.0, 0.5])
        chosen_asset = random.choice(self.external_assets) if self.external_assets else None
        
        # Primary Anchor Object
        quad["objects"].append({
            "type": "asym", "fill": "Solid Black", "scale": scale1, "spin": 0, "rot": 0, "flip_h": False, "flip_v": False,
            "rel_x": 0, "rel_y": 0, "rel_size": 0.8, "asset": chosen_asset
        })
        
        if num_subs == 1:
            quad["split_type"] = "Whole"
            quad["objects"][0]["rel_size"] = 0.6
            
        elif num_subs == 2:
            quad["split_type"] = random.choice(["Vertical", "Horizontal", "Diagonal TL-BR", "Diagonal TR-BL"])
            quad["objects"].append({"type": "poly", "shape": random.choice(self.polygons), "fill": random.choice(self.fills), "scale": random.choice([1.0, 0.5]), "spin": random.choice([0, 1, -1]), "rot": 0})
            
            if quad["split_type"] == "Vertical":
                quad["objects"][0].update({"rel_x": -0.25, "rel_y": 0, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": 0.25, "rel_y": 0, "rel_size": 0.45})
            elif quad["split_type"] == "Horizontal":
                quad["objects"][0].update({"rel_x": 0, "rel_y": -0.25, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": 0, "rel_y": 0.25, "rel_size": 0.45})
            else:
                s = 0.25
                quad["objects"][0].update({"rel_x": -s, "rel_y": -s, "rel_size": 0.4})
                quad["objects"][1].update({"rel_x": s, "rel_y": s, "rel_size": 0.4})

        elif num_subs == 3:
            # 8 possible orientations: 4 Orthogonal (T-Splits) and 4 Diagonal splits
            quad["split_type"] = random.choice([
                "Half Left, Quarters Right", "Half Right, Quarters Left", 
                "Half Top, Quarters Bottom", "Half Bottom, Quarters Top",
                "Diag Half TL, Quarters BR", "Diag Half BR, Quarters TL",
                "Diag Half TR, Quarters BL", "Diag Half BL, Quarters TR"
            ])
            
            # Generate the two smaller polygons
            for _ in range(2):
                quad["objects"].append({
                    "type": "poly", "shape": random.choice(self.polygons), 
                    "fill": random.choice(self.fills), "scale": random.choice([1.0, 0.5]), 
                    "spin": random.choice([0, 1, -1]), "rot": 0
                })
            
            # Orthogonal Mappings
            if quad["split_type"] == "Half Left, Quarters Right":
                quad["objects"][0].update({"rel_x": -0.25, "rel_y": 0, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": 0.25, "rel_y": -0.25, "rel_size": 0.35})
                quad["objects"][2].update({"rel_x": 0.25, "rel_y": 0.25, "rel_size": 0.35})
            elif quad["split_type"] == "Half Right, Quarters Left":
                quad["objects"][0].update({"rel_x": 0.25, "rel_y": 0, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": -0.25, "rel_y": -0.25, "rel_size": 0.35})
                quad["objects"][2].update({"rel_x": -0.25, "rel_y": 0.25, "rel_size": 0.35})
            elif quad["split_type"] == "Half Top, Quarters Bottom":
                quad["objects"][0].update({"rel_x": 0, "rel_y": -0.25, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": -0.25, "rel_y": 0.25, "rel_size": 0.35})
                quad["objects"][2].update({"rel_x": 0.25, "rel_y": 0.25, "rel_size": 0.35})
            elif quad["split_type"] == "Half Bottom, Quarters Top":
                quad["objects"][0].update({"rel_x": 0, "rel_y": 0.25, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": -0.25, "rel_y": -0.25, "rel_size": 0.35})
                quad["objects"][2].update({"rel_x": 0.25, "rel_y": -0.25, "rel_size": 0.35})
                
            # Diagonal Mappings
            elif quad["split_type"] == "Diag Half TL, Quarters BR":
                quad["objects"][0].update({"rel_x": -0.2, "rel_y": -0.2, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": 0.25, "rel_y": 0.05, "rel_size": 0.3})
                quad["objects"][2].update({"rel_x": 0.05, "rel_y": 0.25, "rel_size": 0.3})
            elif quad["split_type"] == "Diag Half BR, Quarters TL":
                quad["objects"][0].update({"rel_x": 0.2, "rel_y": 0.2, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": -0.25, "rel_y": -0.05, "rel_size": 0.3})
                quad["objects"][2].update({"rel_x": -0.05, "rel_y": -0.25, "rel_size": 0.3})
            elif quad["split_type"] == "Diag Half TR, Quarters BL":
                quad["objects"][0].update({"rel_x": 0.2, "rel_y": -0.2, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": -0.25, "rel_y": 0.05, "rel_size": 0.3})
                quad["objects"][2].update({"rel_x": -0.05, "rel_y": 0.25, "rel_size": 0.3})
            elif quad["split_type"] == "Diag Half BL, Quarters TR":
                quad["objects"][0].update({"rel_x": -0.2, "rel_y": 0.2, "rel_size": 0.45})
                quad["objects"][1].update({"rel_x": 0.25, "rel_y": -0.05, "rel_size": 0.3})
                quad["objects"][2].update({"rel_x": 0.05, "rel_y": -0.25, "rel_size": 0.3})
                
        return quad

    def apply_quad_transformation(self, quad, transform_type):
        new_quad = copy.deepcopy(quad)
        for obj in new_quad["objects"]:
            if transform_type == "90_CW":
                obj["rot"] = (obj["rot"] + 90) % 360
                obj["rel_x"], obj["rel_y"] = -obj["rel_y"], obj["rel_x"]
            elif transform_type == "90_ACW":
                obj["rot"] = (obj["rot"] - 90) % 360
                obj["rel_x"], obj["rel_y"] = obj["rel_y"], -obj["rel_x"]
            elif transform_type == "Mirror_H":
                obj["flip_h"] = not obj.get("flip_h", False)
                if obj["type"] == "poly": obj["rot"] = (-obj["rot"]) % 360
                obj["rel_x"] = -obj["rel_x"]
                if obj.get("spin", 0) != 0: obj["spin"] *= -1 
            elif transform_type == "Mirror_V":
                obj["flip_v"] = not obj.get("flip_v", False)
                if obj["type"] == "poly": obj["rot"] = (180 - obj["rot"]) % 360
                obj["rel_y"] = -obj["rel_y"]
                if obj.get("spin", 0) != 0: obj["spin"] *= -1
            elif transform_type == "Mirror_D": 
                if obj["type"] == "poly":
                    obj["flip_h"] = not obj.get("flip_h", False)
                    obj["flip_v"] = not obj.get("flip_v", False)
                    obj["rot"] = (90 - obj["rot"]) % 360
                else:
                    obj["flip_v"] = not obj.get("flip_v", False)
                    obj["rot"] = (obj["rot"] + 90) % 360
                obj["rel_x"], obj["rel_y"] = obj["rel_y"], obj["rel_x"]
                if obj.get("spin", 0) != 0: obj["spin"] *= -1
        return new_quad

    def build_grid_logic(self, num_subs):
        logic_choices = [
            "Horizontal 90 CW", "Horizontal 90 ACW", "Horizontal Mirror", "Horizontal Translation",
            "Vertical 90 CW", "Vertical 90 ACW", "Vertical Mirror", "Vertical Translation",
            "Diagonal Mirror", "Diagonal Translation",
            "Compound: Horiz Trans & Vert Mirror", "Compound: Vert Trans & Horiz Mirror",
            "Compound: Horiz Mirror & Vert Mirror"
        ]
        
        while True:
            logic = random.choice(logic_choices)
            quads = {"A1": None, "B1": None, "A2": None, "B2": None}
            quads["A1"] = self.generate_seed_quadrant(num_subs)

            def get_cohesive_seed(base_q):
                """Creates a second anchor using the exact same objects, but mutates their starting states."""
                q = copy.deepcopy(base_q)
                for obj in q["objects"]:
                    if obj["type"] == "poly":
                        avail_fills = [f for f in self.fills if f != obj["fill"]]
                        if avail_fills: obj["fill"] = random.choice(avail_fills)
                        obj["rot"] = (obj["rot"] + random.choice([90, 180, 270])) % 360
                    else:
                        obj["flip_h"] = not obj.get("flip_h", False)
                return q

            # Pathway 1: Single-Seed Compound Logic (Layering)
            if "Compound" in logic:
                if logic == "Compound: Horiz Trans & Vert Mirror":
                    quads["B1"] = copy.deepcopy(quads["A1"])
                    quads["A2"] = self.apply_quad_transformation(quads["A1"], "Mirror_V")
                    quads["B2"] = self.apply_quad_transformation(quads["B1"], "Mirror_V")
                elif logic == "Compound: Vert Trans & Horiz Mirror":
                    quads["A2"] = copy.deepcopy(quads["A1"])
                    quads["B1"] = self.apply_quad_transformation(quads["A1"], "Mirror_H")
                    quads["B2"] = self.apply_quad_transformation(quads["A2"], "Mirror_H")
                elif logic == "Compound: Horiz Mirror & Vert Mirror":
                    quads["B1"] = self.apply_quad_transformation(quads["A1"], "Mirror_H")
                    quads["A2"] = self.apply_quad_transformation(quads["A1"], "Mirror_V")
                    quads["B2"] = self.apply_quad_transformation(quads["B1"], "Mirror_V")
            
            # Pathway 2: Two-Seed Single-Axis Logic
            elif "Horizontal" in logic:
                quads["A2"] = get_cohesive_seed(quads["A1"])
                if "Translation" in logic:
                    quads["B1"] = copy.deepcopy(quads["A1"])
                    quads["B2"] = copy.deepcopy(quads["A2"])
                else:
                    t_type = "90_CW" if "90 CW" in logic else "90_ACW" if "90 ACW" in logic else "Mirror_H"
                    quads["B1"] = self.apply_quad_transformation(quads["A1"], t_type)
                    quads["B2"] = self.apply_quad_transformation(quads["A2"], t_type)
                    
            elif "Vertical" in logic:
                quads["B1"] = get_cohesive_seed(quads["A1"])
                if "Translation" in logic:
                    quads["A2"] = copy.deepcopy(quads["A1"])
                    quads["B2"] = copy.deepcopy(quads["B1"])
                else:
                    t_type = "90_CW" if "90 CW" in logic else "90_ACW" if "90 ACW" in logic else "Mirror_V"
                    quads["A2"] = self.apply_quad_transformation(quads["A1"], t_type)
                    quads["B2"] = self.apply_quad_transformation(quads["B1"], t_type)
                    
            elif "Diagonal" in logic:
                quads["B1"] = get_cohesive_seed(quads["A1"])
                if "Translation" in logic:
                    quads["B2"] = copy.deepcopy(quads["A1"])
                    quads["A2"] = copy.deepcopy(quads["B1"])
                else:
                    quads["B2"] = self.apply_quad_transformation(quads["A1"], "Mirror_D")
                    quads["A2"] = self.apply_quad_transformation(quads["B1"], "Mirror_D")

            # Failsafe validity check
            valid = True
            if self.quads_are_identical(quads["A1"], quads["B1"]) and \
               self.quads_are_identical(quads["A1"], quads["A2"]) and \
               self.quads_are_identical(quads["A1"], quads["B2"]):
                valid = False
            
            if valid:
                break

        # Calculate Difficulty Score
        score = 0.0
        if num_subs == 1: score += 1.0
        elif num_subs == 2: score += 2.0
        elif num_subs == 3: score += 3.5

        variants_used = 0
        if any(o.get("spin", 0) != 0 for o in quads["A1"]["objects"]): variants_used += 1
        if any(o["scale"] != 1.0 for o in quads["A1"]["objects"]): variants_used += 1
        if any(o.get("fill", "Solid Black") not in ["Solid Black", "Solid Dark Grey", "White"] for o in quads["A1"]["objects"]): variants_used += 1
        
        if variants_used == 1: score += 1.0
        elif variants_used == 2: score += 2.5
        elif variants_used == 3: score += 4.5

        if "Translation" in logic and not "Compound" in logic: score += 1.5
        elif "Mirror" in logic and not "Compound" in logic:
            score += 3.5 if "Diagonal" in logic else 2.5
        elif "90" in logic: score += 4.0
        elif "Compound" in logic: score += 2.0 

        is_mirror_logic = "Mirror" in logic
        has_spin_seed1 = any(o.get("spin", 0) != 0 for o in quads["A1"]["objects"])
        has_spin_seed2 = False
        if quads.get("A2") and "Horizontal" in logic:
            has_spin_seed2 = any(o.get("spin", 0) != 0 for o in quads["A2"]["objects"])
        elif quads.get("B1") and ("Vertical" in logic or "Diagonal" in logic):
            has_spin_seed2 = any(o.get("spin", 0) != 0 for o in quads["B1"]["objects"])

        if is_mirror_logic and (has_spin_seed1 or has_spin_seed2): score += 2.0  
        has_spin = (has_spin_seed1 or has_spin_seed2)
        
        split_type = quads["A1"]["split_type"]
        return quads, logic, score, has_spin, split_type

    def generate_options(self, target_quad, has_spin):
        options = [target_quad]
        labels = ["A", "B", "C", "D", "E"]
        
        def mutate_wrong_axis(q): return self.apply_quad_transformation(q, "Mirror_V" if random.choice([True, False]) else "Mirror_H")
        def mutate_wrong_dir(q): return self.apply_quad_transformation(q, "90_CW" if random.choice([True, False]) else "90_ACW")
        def mutate_scale(q):
            new_q = copy.deepcopy(q)
            tgt = random.choice(new_q["objects"])
            tgt["scale"] = 0.5 if tgt["scale"] == 1.0 else 1.0
            return new_q
        def mutate_fill(q):
            new_q = copy.deepcopy(q)
            polys = [o for o in new_q["objects"] if o["type"] == "poly"]
            if polys:
                tgt = random.choice(polys)
                avail = [f for f in self.fills if f != tgt["fill"]]
                tgt["fill"] = random.choice(avail)
            else:
                new_q = self.apply_quad_transformation(new_q, "Mirror_D")
            return new_q
        def mutate_shape(q):
            new_q = copy.deepcopy(q)
            polys = [o for o in new_q["objects"] if o["type"] == "poly"]
            if polys:
                tgt = random.choice(polys)
                avail = [s for s in self.polygons if s != tgt["shape"]]
                tgt["shape"] = random.choice(avail)
            else:
                new_q = self.apply_quad_transformation(new_q, "90_CW")
            return new_q

        mutators = [mutate_wrong_axis, mutate_wrong_dir, mutate_scale, mutate_fill, mutate_shape]
        random.shuffle(mutators)

        for i in range(4):
            valid = False
            attempts = 0
            while not valid and attempts < 50:
                mutator = mutators[i % len(mutators)] if attempts < 10 else random.choice(mutators)
                candidate = mutator(target_quad)
                
                if not any(self.quads_are_identical(candidate, opt) for opt in options):
                    options.append(candidate)
                    valid = True
                attempts += 1
            
            if not valid:
                fb = self.generate_seed_quadrant(random.choice([1, 2, 3]))
                while any(self.quads_are_identical(fb, opt) for opt in options):
                    fb = self.generate_seed_quadrant(random.choice([1, 2, 3]))
                options.append(fb)

        random.shuffle(options)
        correct_index = options.index(target_quad)
        return options, labels[correct_index]

    def render_puzzle(self, filename_base, quads, options, target_cell, has_spin):
        grid_w = self.quad_size * 2 + self.grid_line_w + self.border_w * 2 + self.pad * 2
        ans_w = self.quad_size * 5 + self.pad * 6
        # Increased initial height slightly to guarantee text labels aren't clipped before tight crop
        ans_h = self.quad_size + self.pad * 4 + int(100 * self.sf) 
        
        frames_grid = []
        frames_ans = []
        total_frames = self.frames if has_spin else 1
        
        coords = {
            "A1": (self.pad + self.border_w, self.pad + self.border_w),
            "B1": (self.pad + self.border_w + self.quad_size + self.grid_line_w, self.pad + self.border_w),
            "A2": (self.pad + self.border_w, self.pad + self.border_w + self.quad_size + self.grid_line_w),
            "B2": (self.pad + self.border_w + self.quad_size + self.grid_line_w, self.pad + self.border_w + self.quad_size + self.grid_line_w),
        }

        for f in range(total_frames):
            g_img = Image.new("RGBA", (grid_w, grid_w), "white")
            g_draw = ImageDraw.Draw(g_img)
            
            g_draw.rectangle([self.pad, self.pad, grid_w - self.pad, grid_w - self.pad], outline="black", width=self.border_w)
            g_draw.rectangle([self.pad + self.border_w + self.quad_size, self.pad, self.pad + self.border_w + self.quad_size + self.grid_line_w, grid_w - self.pad], fill="black")
            g_draw.rectangle([self.pad, self.pad + self.border_w + self.quad_size, grid_w - self.pad, self.pad + self.border_w + self.quad_size + self.grid_line_w], fill="black")

            for cell, q_data in quads.items():
                if cell != target_cell:
                    self.draw_quadrant_master(g_img, coords[cell][0], coords[cell][1], q_data, frame_idx=f)
            
            a_img = Image.new("RGBA", (ans_w, ans_h), "white")
            a_draw = ImageDraw.Draw(a_img)
            labels = ["A", "B", "C", "D", "E"]
            
            for idx, opt in enumerate(options):
                ox = self.pad + idx * (self.quad_size + self.pad)
                oy = self.pad
                a_draw.rectangle([ox, oy, ox + self.quad_size, oy + self.quad_size], outline="black", width=self.border_w)
                self.draw_quadrant_master(a_img, ox, oy, opt, frame_idx=f)
                
                lbl_y = oy + self.quad_size + int(60 * self.sf)
                self.draw_text_centered(a_draw, ox + self.quad_size // 2, lbl_y, labels[idx])
                
            # ── MASTER WIDTH CROPPING & CENTERING LOGIC ──
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
    print("Design Grid C Generator (NVR)")
    print("=" * 40)
    
    try:
        user_input = input("How many puzzles to generate? ")
        num_puzzles = int(user_input)
    except ValueError:
        num_puzzles = 1
        
    try:
        sub_input = input("Number of sub-objects (1, 2, 3) or 0 for Random: ")
        forced_subs = int(sub_input)
    except ValueError:
        forced_subs = 0

    generator = GridCGenerator()
    puzzles_meta = []
    
    print("\nGenerating...")
    for i in range(num_puzzles):
        num_subs = random.choice([1, 2, 3]) if forced_subs not in [1, 2, 3] else forced_subs
        target_cell = random.choice(["A1", "B1", "A2", "B2"])
        
        quads, logic, score, has_spin, split_type = generator.build_grid_logic(num_subs)
        options, correct_ans = generator.generate_options(quads[target_cell], has_spin)
        
        temp_base = f"temp_{i:04d}"
        generator.render_puzzle(temp_base, quads, options, target_cell, has_spin)
        
        puzzles_meta.append({
            "temp": temp_base, "score": score, "logic": logic, 
            "subs": num_subs, "split_type": split_type, "target": target_cell, 
            "ans": correct_ans, "ext": "gif" if has_spin else "png"
        })

    print("Sorting & Saving Manifest...")
    puzzles_meta.sort(key=lambda x: x["score"])
    
    manifest_path = os.path.join(OUTPUT_FOLDER, "Puzzle_Manifest.csv")
    with open(manifest_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Difficulty_Score", "Logic", "Sub_Objects", "Split_Type", "Target_Cell", "Answer"])
        
        for i, meta in enumerate(puzzles_meta):
            final_base = f"Puzzle_{i+1:03d}"
            
            shutil.move(os.path.join(TEMP_FOLDER, f"{meta['temp']}_grid.{meta['ext']}"), 
                        os.path.join(OUTPUT_FOLDER, f"{final_base}_grid.{meta['ext']}"))
            shutil.move(os.path.join(TEMP_FOLDER, f"{meta['temp']}_ans.{meta['ext']}"), 
                        os.path.join(OUTPUT_FOLDER, f"{final_base}_answers.{meta['ext']}"))
                        
            writer.writerow([final_base, meta["score"], meta["logic"], meta["subs"], meta["split_type"], meta["target"], meta["ans"]])
            
    shutil.rmtree(TEMP_FOLDER)
    print(f"\nDone! Processed {num_puzzles} puzzles into 'NVR_grids_c'.")
