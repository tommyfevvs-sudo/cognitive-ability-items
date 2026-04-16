"""
NVR_sequences_overlapping_shapes.py
=========================
Non-Verbal Reasoning — Sequences Item Generator
Standalone Module: Overlapping Shapes (Hybrid 5-Axis Engine)
"""

import random, os, math, csv, copy, shutil
from PIL import Image, ImageDraw, ImageFont

# ── Target Configuration ───────────────────────────────────────────────────────
TARGET_SUBTYPE = "overlapping_shapes"

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, f"NVR_Sequences_{TARGET_SUBTYPE.title()}")
TEMP_FOLDER   = os.path.join(OUTPUT_FOLDER, "_temp")

# ── Kinetic Animation Constants ────────────────────────────────────────────────
N_GIF_FRAMES      = 180   # Increased to smoothly slow down top speeds
ANIM_FRAME_MS     = 40    # Increased to drag out the loop (7.2s per full loop)
ANSWER_OPTIONS    = 5
N_FRAMES_SHOWN    = 4

# ── Safeguard constants ────────────────────────────────────────────────────────
MAX_DEDUP_ATTEMPTS  = 50
MAX_GEN_RETRIES     = 10

SHAPE_SYMMETRIES = {
    "square": 90, "hexagon": 60, "cross_shape": 90,
    "pentagon": 72, "star": 72, "triangle": 120,
    "arrow": 360, "circle": 360,
    "diamond": 180, "octagon": 45, "trapezium": 360, 
    "parallelogram": 180
}

# ── Font search paths ──────────────────────────────────────────────────────────
FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts", "/usr/share/fonts/truetype",
    "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu",
]
FALLBACK_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# ═══════════════════════════════════════════════════════════════════════════════
# SAFEGUARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _state_key(state):
    state_copy = copy.deepcopy(state)
    # Normalize fake visual differences before comparing
    if isinstance(state_copy, dict) and "layers" in state_copy:
        for l in state_copy["layers"]:
            # If spin is 0, spin direction is visually meaningless
            if l.get("spin_mult", 0) == 0:
                l["spin_dir"] = 1
            # If it's a solid/hollow circle, spinning does not change visual appearance
            if l.get("shape") == "circle" and l.get("fill") in ["solid", "hollow"]:
                l["spin_mult"] = 0
                l["spin_dir"] = 1
                
    def _norm(v):
        if isinstance(v, dict):
            return tuple(sorted((k, _norm(w)) for k, w in v.items()))
        if isinstance(v, list):  return tuple(_norm(i) for i in v)
        # Round floats slightly wider to catch tiny math variations
        if isinstance(v, float): return round(v, 2) 
        return v
        
    return _norm(state_copy)

def _states_equal(a, b):
    return _state_key(a) == _state_key(b)

def _check_sequence_unique(frames):
    keys = [_state_key(f) for f in frames]
    return len(keys) == len(set(keys))

def _safe_gen(gen_fn, fallback_fn, *args):
    for _ in range(MAX_GEN_RETRIES):
        result = gen_fn(*args)
        if _check_sequence_unique(result["frames"]):
            return result
    return fallback_fn(*args)

# ═══════════════════════════════════════════════════════════════════════════════
class NVRSequenceGenerator:

    def __init__(self):
        self.sf           = 3  
        self.frame_hd     = 180 * self.sf
        self.frame_border = int(2  * self.sf)
        self.frame_sep    = int(6  * self.sf)
        self.strip_pad    = int(20 * self.sf)

        self.all_shapes       = ["circle","square","triangle","pentagon",
                                 "hexagon","arrow","star","cross_shape",
                                 "diamond", "octagon", "trapezium", "parallelogram"]
        
        self.rotatable_shapes = ["triangle","arrow","pentagon","star", "trapezium", 
                                 "parallelogram", "diamond", "square", "hexagon", "cross_shape", "octagon"]
        
        self.hatch_fills = [
            ("lines","vertical"), ("lines","diagonal_tl_br"),
            ("lines","diagonal_tr_bl"), ("grids","standard_large"),
            ("grids","standard_small"), ("wavy","wavy_v"), ("mini_tri","tri_up"),
        ]
        self.font_hd   = None
        self.qlabel_hd = None
        self._load_fonts()

    def _load_fonts(self):
        found = False
        for d in FONT_DIRS:
            if not os.path.isdir(d): continue
            try:
                for fname in os.listdir(d):
                    lf = fname.lower()
                    if "proxima" in lf and "soft" in lf:
                        if any(b in lf for b in ["italic", "light", "bold", "semibold", "medium", "thin", "black", "extrabold", "heavy"]): 
                            continue
                        try:
                            fp = os.path.join(d, fname)
                            self.font_hd   = ImageFont.truetype(fp, 44*self.sf)
                            self.qlabel_hd = ImageFont.truetype(fp, 28*self.sf)
                            found = True; break
                        except Exception: continue
                if found: break
            except Exception: continue
        if not found:
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd   = ImageFont.truetype(fp, 44*self.sf)
                        self.qlabel_hd = ImageFont.truetype(fp, 28*self.sf)
                        found = True; break
                    except Exception: continue
        if not found:
            self.font_hd = self.qlabel_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════════
    # SHAPE / DRAW HELPERS
    # ═══════════════════════════════════════════════════════════════════════════════
    def _shape_coords(self, shape, cx, cy, r, rotation=0):
        pts = []
        if shape == "circle": return [cx-r, cy-r, cx+r, cy+r]
        elif shape == "square":
            adj = r * 0.85
            pts = [(cx-adj,cy-adj),(cx+adj,cy-adj),(cx+adj,cy+adj),(cx-adj,cy+adj)]
        elif shape == "triangle":
            for i in range(3):
                a = math.radians(-90 + i*120)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        elif shape == "arrow":
            pts = [(cx+1.25*r,cy),(cx-0.75*r,cy-r),(cx-0.15*r,cy),(cx-0.75*r,cy+r)]
        elif shape == "star":
            for i in range(10):
                a  = math.radians(-90 + i*36)
                cr = r if i%2==0 else r*0.45
                pts.append((cx + cr*math.cos(a), cy + cr*math.sin(a)))
        elif shape == "cross_shape":
            w = r*0.35
            pts = [(cx-w,cy-r),(cx+w,cy-r),(cx+w,cy-w),(cx+r,cy-w),
                   (cx+r,cy+w),(cx+w,cy+w),(cx+w,cy+r),(cx-w,cy+r),
                   (cx-w,cy+w),(cx-r,cy+w),(cx-r,cy-w),(cx-w,cy-w)]
        elif shape == "pentagon":
            for i in range(5):
                a = math.radians(-90 + i*72)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        elif shape == "hexagon":
            for i in range(6):
                a = math.radians(-90 + i*60)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        elif shape == "diamond":
            pts = [(cx, cy-r), (cx+r*0.75, cy), (cx, cy+r), (cx-r*0.75, cy)]
        elif shape == "octagon":
            for i in range(8):
                a = math.radians(-90 + i*45)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        elif shape == "trapezium":
            pts = [(cx-r*0.5, cy-r*0.6), (cx+r*0.5, cy-r*0.6), (cx+r*0.9, cy+r*0.6), (cx-r*0.9, cy+r*0.6)]
        elif shape == "parallelogram":
            pts = [(cx-r*0.3, cy-r*0.6), (cx+r*0.8, cy-r*0.6), (cx+r*0.3, cy+r*0.6), (cx-r*0.8, cy+r*0.6)]

        if rotation != 0 and pts:
            rad = math.radians(rotation)
            return [(cx + (px-cx)*math.cos(rad) - (py-cy)*math.sin(rad),
                     cy + (px-cx)*math.sin(rad) + (py-cy)*math.cos(rad))
                    for px, py in pts]
        return pts

    def _draw_pattern(self, draw, fill_data, size):
        sf = self.sf
        category, variant = fill_data
        if category == "wavy":
            for i in range(-size, size*2, 14*sf):
                wpts = []
                for j in range(0, size+10, 4*sf):
                    off = math.sin(j*0.05) * (5*sf)
                    wpts.append((i+off, j) if variant=="wavy_v" else (j, i+off))
                if len(wpts) > 1: draw.line(wpts, fill="black", width=2*sf)
        elif category == "mini_tri":
            ts, gp = 5*sf, 18*sf
            for tx in range(0, size, gp):
                for ty in range(0, size, gp):
                    draw.polygon([(tx,ty-ts),(tx+ts,ty+ts),(tx-ts,ty+ts)], fill="black")
        elif category == "lines":
            for li in range(-size, size*2, 13*sf):
                if variant == "vertical": draw.line([(li,0),(li,size)], fill="black", width=2*sf)
                elif variant == "diagonal_tl_br": draw.line([(li,0),(li+size,size)], fill="black", width=2*sf)
                else: draw.line([(li,0),(li-size,size)], fill="black", width=2*sf)
        elif category == "grids":
            gs = 20*sf if "large" in variant else 9*sf
            for gx in range(0, size+10*sf, gs): draw.line([(gx,0),(gx,size)], fill="black", width=2*sf)
            for gy in range(0, size+10*sf, gs): draw.line([(0,gy),(size,gy)], fill="black", width=2*sf)

    def _draw_masked_shape(self, canvas, shape, pattern, cx, cy, r, rotation=0, ow=2.5):
        size  = int(r * 3.0)
        buf   = Image.new("RGBA", (size,size), (255,255,255,0))
        mask  = Image.new("L",   (size,size), 0)
        self._draw_pattern(ImageDraw.Draw(buf), pattern, size)
        loc_pts  = self._shape_coords(shape, size//2, size//2, r, rotation)
        glob_pts = self._shape_coords(shape, cx, cy, r, rotation)
        draw     = ImageDraw.Draw(canvas)
        weight   = int(ow * self.sf)
        if shape == "circle":
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx-size//2), int(cy-size//2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight)
        else:
            closed = glob_pts + [glob_pts[0], glob_pts[1]]
            draw.line(closed, fill="black", width=weight*2, joint="curve")
            draw.polygon(glob_pts, fill="black")
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx-size//2), int(cy-size//2)), mask)

    def _draw_shape(self, canvas, shape, fill, cx, cy, r, rotation=0, ow=2.5):
        draw   = ImageDraw.Draw(canvas)
        weight = int(ow * self.sf)
        coords = self._shape_coords(shape, cx, cy, r, rotation)
        if fill == "solid":
            if shape == "circle": draw.ellipse(coords, fill="black", outline="black", width=weight)
            else: draw.polygon(coords, fill="black", outline="black")
        elif fill == "hollow":
            if shape == "circle": draw.ellipse(coords, fill="white", outline="black", width=weight)
            else:
                draw.polygon(coords, fill="white", outline="black")
                closed = coords + [coords[0], coords[1]]
                draw.line(closed, fill="black", width=weight, joint="curve")
        else:
            self._draw_masked_shape(canvas, shape, fill, cx, cy, r, rotation, ow)

    def _draw_question_mark(self, canvas, cx, cy):
        draw = ImageDraw.Draw(canvas)
        txt  = "?"
        bbox = draw.textbbox((0,0), txt, font=self.font_hd)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((cx-tw//2, cy-th//2), txt, font=self.font_hd, fill="black")

    # ═══════════════════════════════════════════════════════════════════════════════
    # DECOUPLED KINETIC 5-AXIS MATRIX GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════════
    def _gen_overlapping_shapes(self, target_score=None):
        shape_count_pool = [
            ("1_shape", 1, 0),
            ("2_shapes", 2, 2),
            ("3_shapes", 3, 4)
        ]

        size_logic_pool = [
            ("static_size", 0),
            ("uniform_scale_grow", 1),
            ("uniform_scale_shrink", 1),
            ("bg_static_fg_scales", 2),
            ("opposing_trends", 3),
            ("different_rates", 4)
        ]

        spin_logic_pool = [
            ("0_static", 0),
            ("1_constant_spin", 1),
            ("2_alternating_spin", 3),
            ("3_accelerating_spin", 4),
            ("4_decelerating_spin", 4)
        ]

        fill_logic_pool = [
            ("fixed_by_layer", 0),         
            ("alternate_every_frame", 2),  
            ("cycle_independent", 4)       
        ]

        pos_logic_pool = [
            ("0_centered_static", 0),    
            ("1_offset_static", 1),    
            ("2_z_order_cycle", 3),      
            ("3_orbital_cycle", 4),
            ("4_separated_static", 0)
        ]

        valid_combos = []
        for shp in shape_count_pool:
            for sz in size_logic_pool:
                for rt in spin_logic_pool:
                    for fl in fill_logic_pool:
                        for ps in pos_logic_pool:
                            n = shp[1]
                            
                            if n == 1 and sz[0] in ["opposing_trends", "different_rates", "bg_static_fg_scales"]: continue
                            if n == 1 and rt[0] in ["2_alternating_spin", "3_accelerating_spin", "4_decelerating_spin"]: continue
                            if n == 1 and ps[0] in ["2_z_order_cycle", "4_separated_static"]: continue
                            if n == 1 and ps[0] in ["3_orbital_cycle", "1_offset_static"]: continue
                            if ps[0] == "0_centered_static" and sz[0] in ["opposing_trends", "different_rates"]: continue
                            
                            total_score = shp[2] + sz[1] + rt[1] + fl[1] + ps[1]
                            if total_score == 0: continue 
                            
                            if target_score is None or total_score == target_score:
                                valid_combos.append({
                                    "shape": shp, "size": sz, "rot": rt, 
                                    "fill": fl, "pos": ps, "score": total_score
                                })

        if not valid_combos and target_score is not None:
            return self._fallback_overlapping_shapes(target_score)

        anim_combos = [c for c in valid_combos if c["rot"][0] != "0_static"]
        static_combos = [c for c in valid_combos if c["rot"][0] == "0_static"]

        if anim_combos and static_combos:
            valid_combos = anim_combos if random.random() < 0.5 else static_combos
        elif anim_combos: valid_combos = anim_combos
        elif static_combos: valid_combos = static_combos

        chosen = random.choice(valid_combos)
        
        n_layers = chosen["shape"][1]
        sz_rule = chosen["size"][0]
        rt_rule = chosen["rot"][0]
        fl_rule = chosen["fill"][0]
        ps_rule = chosen["pos"][0]
        score = chosen["score"]

        # FORCED FIX: Always generate 5 total options (4 distractors)
        n_options = 5
        n_distractors_needed = 4

        if rt_rule == "0_static": shape_pool = self.all_shapes
        else: shape_pool = self.rotatable_shapes
        layer_shapes = random.sample(shape_pool, min(n_layers, len(shape_pool)))

        size_dirs = []
        fixed_sizes = []
        
        if sz_rule == "static_size":
            size_dirs = [0] * n_layers
            fixed_sizes = [True] * n_layers
        elif "uniform_scale" in sz_rule:
            u_dir = 1 if "grow" in sz_rule else -1
            size_dirs = [u_dir] * n_layers
            fixed_sizes = [False] * n_layers
        elif sz_rule == "bg_static_fg_scales":
            size_dirs = [0, random.choice([1, -1]), 1][:n_layers]
            fixed_sizes = [True, False, False][:n_layers]
        elif sz_rule == "opposing_trends":
            size_dirs = [1, -1, 1][:n_layers]
            fixed_sizes = [False] * n_layers
        elif sz_rule == "different_rates":
            size_dirs = [1, 1, 1][:n_layers]
            fixed_sizes = [False] * n_layers

        start_sizes = []
        size_steps = []
        
        # ── RESTORED ORIGINAL MINIMUM BOUNDS ──
        if n_layers == 1:
            size_bounds = [(0.20, 0.95)]
            base_positions = [(0, 0)]
        elif ps_rule == "0_centered_static":
            if n_layers == 2:
                size_bounds = [(0.45, 0.95), (0.20, 0.65)]
                base_positions = [(0, 0), (0, 0)]
            else:
                size_bounds = [(0.60, 0.95), (0.35, 0.70), (0.10, 0.45)]
                base_positions = [(0, 0), (0, 0), (0, 0)]
        elif ps_rule == "4_separated_static":
            size_bounds = [(0.20, 0.45), (0.20, 0.45), (0.20, 0.45)]
            if n_layers == 2: base_positions = [(-0.45, 0), (0.45, 0)]
            else: base_positions = [(-0.40, -0.40), (0.40, -0.40), (0, 0.40)]
        else:
            size_bounds = [(0.20, 0.55), (0.20, 0.55), (0.20, 0.55)]
            if n_layers == 2: base_positions = [(-0.25, -0.25), (0.25, 0.25), (0, 0)]
            else: base_positions = [(-0.25, -0.25), (0, 0), (0.25, 0.25)]

        for li in range(n_layers):
            min_b, max_b = size_bounds[li]
            if fixed_sizes[li]:
                start_sizes.append(random.uniform(min_b, max_b))
                size_steps.append(0.0)
            else:
                exact_step = (max_b - min_b) / N_FRAMES_SHOWN
                if sz_rule == "different_rates" and li == 0: exact_step *= 0.5 
                size_steps.append(exact_step)
                start_sizes.append(min_b if size_dirs[li] > 0 else max_b)

        # ── INDEPENDENT SPIN LOGIC SETUP ──
        layer_spin_dirs = []
        layer_base_mults = []
        
        if rt_rule == "0_static":
            layer_spin_dirs = [1] * n_layers
            layer_base_mults = [0] * n_layers
        else:
            max_mult = 1 if rt_rule in ["3_accelerating_spin", "4_decelerating_spin"] else 2
            for i in range(n_layers):
                layer_spin_dirs.append(random.choice([1, -1]))
                if i == 0:
                    layer_base_mults.append(random.choice([1, max_mult])) 
                else:
                    layer_base_mults.append(random.choice([0, 1, max_mult])) 
                    
            combined_spins = list(zip(layer_spin_dirs, layer_base_mults))
            random.shuffle(combined_spins)
            layer_spin_dirs, layer_base_mults = map(list, zip(*combined_spins))

        base_fills = ["solid", "hollow"]
        if n_layers >= 3 or fl_rule == "cycle_independent":
            base_fills.append(random.choice(self.hatch_fills))

        def _get_fill(li, fi):
            if fl_rule == "fixed_by_layer": return base_fills[li % len(base_fills)]
            elif fl_rule == "alternate_every_frame": return base_fills[(li + fi) % min(2, len(base_fills))]
            elif fl_rule == "cycle_independent": return base_fills[(li + fi) % len(base_fills)]

        def _layer_state(li, fi):
            shape = layer_shapes[li]
            
            if fixed_sizes[li]:
                sf_r = start_sizes[li]
            else:
                progression = fi * size_steps[li]
                sf_r = start_sizes[li] + progression if size_dirs[li] > 0 else start_sizes[li] - progression
            
            base_mult = layer_base_mults[li]
            base_dir  = layer_spin_dirs[li]
            
            spin_mult = 0
            spin_dir  = base_dir
            
            if rt_rule == "1_constant_spin": 
                spin_mult = base_mult
            elif rt_rule == "2_alternating_spin":
                spin_mult = base_mult
                spin_dir = base_dir if fi % 2 == 0 else -base_dir
            elif rt_rule == "3_accelerating_spin": 
                spin_mult = (fi + 1) * base_mult if base_mult > 0 else 0
            elif rt_rule == "4_decelerating_spin": 
                spin_mult = max(1, 5 - fi) * base_mult if base_mult > 0 else 0
            
            fill = _get_fill(li, fi)
            pos_idx = li
            z_idx = li
            
            if ps_rule == "2_z_order_cycle": z_idx = (li + fi) % n_layers
            elif ps_rule == "3_orbital_cycle": pos_idx = (li + fi) % n_layers
            
            return {
                "shape": shape, "size_frac": sf_r, 
                "spin_mult": spin_mult, "spin_dir": spin_dir, 
                "fill": fill, "offset_x": base_positions[pos_idx][0], "offset_y": base_positions[pos_idx][1],
                "z_idx": z_idx
            }

        def _make_frame(fi):
            return {"subtype": "overlapping_shapes",
                    "layers": [_layer_state(li, fi) for li in range(n_layers)]}

        frames = [_make_frame(fi) for fi in range(N_FRAMES_SHOWN + 1)]
        answer_state = frames[-1]
        shown_frames = frames[:-1]

        def _is_valid_distractor(cand):
            last_shown = shown_frames[-1]
            for l_idx in range(n_layers):
                c_lay = cand["layers"][l_idx]
                a_lay = answer_state["layers"][l_idx]
                ls_lay = last_shown["layers"][l_idx]
                
                if size_dirs[l_idx] > 0:
                    if c_lay["size_frac"] > ls_lay["size_frac"] and c_lay["size_frac"] != a_lay["size_frac"]: return False
                if size_dirs[l_idx] < 0:
                    if c_lay["size_frac"] < ls_lay["size_frac"] and c_lay["size_frac"] != a_lay["size_frac"]: return False
                
                if rt_rule == "3_accelerating_spin":
                    if c_lay["spin_mult"] > ls_lay["spin_mult"] and c_lay["spin_mult"] != a_lay["spin_mult"]: return False
                if rt_rule == "4_decelerating_spin":
                    if c_lay["spin_mult"] < ls_lay["spin_mult"] and c_lay["spin_mult"] != a_lay["spin_mult"]: return False
                    
            if any(_states_equal(cand, existing) for existing in [answer_state] + distractors): return False
            return True

        distractors = []
        candidate_pool = []
        
        # 1. Off-by-one (previous step)
        candidate_pool.append(_make_frame(max(0, N_FRAMES_SHOWN - 1)))
        
        # 2. Overshoot (skipped step)
        candidate_pool.append(_make_frame(N_FRAMES_SHOWN + 1))
        
        # 3. Wrong spin direction
        d_rev = copy.deepcopy(answer_state)
        d_rev["layers"][0]["spin_dir"] *= -1
        candidate_pool.append(d_rev)
            
        # 4. Wrong fill
        d_fill = copy.deepcopy(answer_state)
        l_idx = random.randint(0, n_layers-1)
        alt_fills = [f for f in self.hatch_fills + ["solid", "hollow"] if f != d_fill["layers"][l_idx]["fill"]]
        if alt_fills:
            d_fill["layers"][l_idx]["fill"] = random.choice(alt_fills)
        candidate_pool.append(d_fill)

        # 5. Wrong size (ONLY SCALE UP to prevent microscopic shapes in CMS)
        d_size = copy.deepcopy(answer_state)
        l_idx = random.randint(0, n_layers-1)
        d_size["layers"][l_idx]["size_frac"] = min(0.95, d_size["layers"][l_idx]["size_frac"] * random.uniform(1.3, 1.5))
        candidate_pool.append(d_size)
            
        for _ in range(250):
            d_rand = _make_frame(random.randint(0, N_FRAMES_SHOWN + 2))
            layer_rand = random.randint(0, n_layers-1)
            mb, mx = size_bounds[layer_rand] if n_layers > 1 else size_bounds[0]
            d_rand["layers"][layer_rand]["size_frac"] = random.uniform(mb, mx)
            d_rand["layers"][layer_rand]["spin_mult"] = random.choice([0, 1, 2, 3, 4])
            d_rand["layers"][layer_rand]["spin_dir"] = random.choice([1, -1])
            candidate_pool.append(d_rand)
            
        for cand in candidate_pool:
            if len(distractors) >= n_distractors_needed: break
            if _is_valid_distractor(cand): distractors.append(cand)

        # Ultimate fallback to guarantee uniqueness (ONLY SCALES UP)
        while len(distractors) < n_distractors_needed:
            emer = copy.deepcopy(answer_state)
            l_idx = random.randint(0, n_layers-1)
            emer["layers"][l_idx]["size_frac"] = min(0.95, emer["layers"][l_idx]["size_frac"] * random.uniform(1.2, 1.6))
            if not any(_states_equal(emer, e) for e in [answer_state] + distractors):
                distractors.append(emer)

        rule_desc = f"Shape:{chosen['shape'][0]}|Size:{sz_rule}|Spin:{rt_rule}|Fill:{fl_rule}|Pos:{ps_rule}"
        
        return {
            "subtype": "overlapping_shapes", "frames": shown_frames, "answer": answer_state,
            "distractors": distractors, "n_options": n_options,
            "distractor_strategy": "strict_kinetic_bounds",
            "score": score, "rule_axes": rule_desc,
            "shape_types": "|".join(layer_shapes),
            "rot_rule": rt_rule
        }

    def _fallback_overlapping_shapes(self, target_score):
        return self._gen_overlapping_shapes(target_score=None)

    # ═══════════════════════════════════════════════════════════════════════════════
    # RENDER ENGINE
    # ═══════════════════════════════════════════════════════════════════════════════
    def _render_overlap_frame_t(self, canvas, state, t):
        cx = canvas.width // 2
        cy = canvas.height // 2
        half = self.frame_hd // 2
        
        sorted_layers = sorted(state["layers"], key=lambda x: x.get("z_idx", 0))
        
        for layer in sorted_layers:
            r = int(layer["size_frac"] * half)
            dx = int(layer.get("offset_x", 0) * half)
            dy = int(layer.get("offset_y", 0) * half)
            
            sym = SHAPE_SYMMETRIES.get(layer["shape"], 360)
            base_step = sym / N_GIF_FRAMES
            current_rot = t * base_step * layer.get("spin_mult", 0) * layer.get("spin_dir", 1)
            
            self._draw_shape(canvas, layer["shape"], layer["fill"], cx + dx, cy + dy, r, current_rot)

    def render_frame_t(self, state, t, show_question_mark=False):
        canvas = Image.new("RGB", (self.frame_hd, self.frame_hd), "white")
        if show_question_mark:
            self._draw_question_mark(canvas, canvas.width//2, canvas.height//2)
            return canvas
        self._render_overlap_frame_t(canvas, state, t)
        return canvas

    def _render_sequence_strip_t(self, frames, t, show_answer, answer_state=None):
        n_frames  = len(frames) + 1
        fw, fh = self.frame_hd, self.frame_hd
        
        # 1. Matched line weight
        bw = int(2 * self.sf)
        
        # 2. Overlapping cartoon style
        sep = -bw 
        
        pad = self.strip_pad

        # 3. Removed bot_pad so the bottom cropping perfectly matches the baseline scripts
        strip_w = pad*2 + n_frames*fw + (n_frames-1)*sep
        strip_h = pad*2 + fh 
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i in range(n_frames):
            x0 = pad + i*(fw + sep)
            y0 = pad
            
            draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", fill="white", width=bw)
            
            if i < len(frames): 
                img = self.render_frame_t(frames[i], t)
            else: 
                img = (self.render_frame_t(answer_state, t) if show_answer and answer_state else self.render_frame_t(None, t, show_question_mark=True))
            
            strip.paste(img, (x0, y0))
            
            draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", width=bw)
            
        return strip

    def _render_answer_strip_t(self, options, t):
        fw, fh = self.frame_hd, self.frame_hd
        bw = int(2 * self.sf)
        gap = int(16 * self.sf)
        pad_x, pad_y = int(24 * self.sf), int(20 * self.sf)
        lbl_h = int(64 * self.sf)
        
        lbl_gap = int(27 * self.sf)
        n = len(options)

        strip_w = 2*pad_x + n*fw + (n-1)*gap
        strip_h = pad_y + fh + lbl_gap + lbl_h
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE"[:n])):
            x0 = pad_x + i*(fw + gap)
            y0 = pad_y
            cx = x0 + fw//2
            
            draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", fill="white", width=bw)
            
            strip.paste(self.render_frame_t(opt, t), (x0, y0))
            
            draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", width=bw)
            
            bbox = draw.textbbox((0,0), lbl, font=self.font_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, y0+fh+lbl_gap), lbl, font=self.font_hd, fill="black")
            
        return strip

    def save_temp_item(self, item_data, temp_id, out_root):
        sf = self.sf
        folder_name = f"temp_item_{temp_id:04d}"
        folder_path = os.path.join(out_root, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        is_animated = item_data.get("rot_rule", "0_static") != "0_static"

        if is_animated:
            q_file = f"{folder_name}_question.gif"
            c_file = f"{folder_name}_choices.gif"
        else:
            q_file = f"{folder_name}_question.png"
            c_file = f"{folder_name}_choices.png"

        q_path = os.path.join(folder_path, q_file)
        c_path = os.path.join(folder_path, c_file)

        frames, answer = item_data["frames"], item_data["answer"]
        n_options = 5
        
        # Grab the strictly deduplicated distractors direct from the generator
        distractors = list(item_data.get("distractors", []))[:4]
                
        correct_pos = random.randint(0, 4)
        correct_letter = "ABCDE"[correct_pos]
        options = list(distractors)
        options.insert(correct_pos, answer)

        if is_animated:
            q_gif_frames = []
            c_gif_frames = []
            for t in range(N_GIF_FRAMES):
                q_f = self._render_sequence_strip_t(frames, t, show_answer=False)
                c_f = self._render_answer_strip_t(options, t)
                
                q_gif_frames.append(q_f.resize((q_f.width//sf, q_f.height//sf), Image.Resampling.LANCZOS))
                c_gif_frames.append(c_f.resize((c_f.width//sf, c_f.height//sf), Image.Resampling.LANCZOS))

            q_gif_frames[0].save(q_path, save_all=True, append_images=q_gif_frames[1:], duration=ANIM_FRAME_MS, loop=0, optimize=False)
            c_gif_frames[0].save(c_path, save_all=True, append_images=c_gif_frames[1:], duration=ANIM_FRAME_MS, loop=0, optimize=False)
        else:
            q_f = self._render_sequence_strip_t(frames, 0, show_answer=False)
            c_f = self._render_answer_strip_t(options, 0)
            
            q_res = q_f.resize((q_f.width//sf, q_f.height//sf), Image.Resampling.LANCZOS)
            c_res = c_f.resize((c_f.width//sf, c_f.height//sf), Image.Resampling.LANCZOS)
            
            q_res.save(q_path)
            c_res.save(c_path)

        return folder_path, correct_letter, is_animated

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    gen = NVRSequenceGenerator()
    print(f"\nNVR Sequence Generator — Hybrid 5-Axis Engine")
    print("="*75)
    
    raw_n = input("How many items to generate? [default: 20]: ").strip()
    n_items = int(raw_n) if raw_n.isdigit() and int(raw_n) > 0 else 20

    raw_t = input("Enter a specific Target Score (e.g. 12) or press Enter for Random Spread: ").strip()
    target_score = int(raw_t) if raw_t.isdigit() else None
    
    spread_targets = []
    if target_score is None:
        buckets = [[1, 2, 3, 4], [5, 6, 7], [8, 9, 10], [11, 12, 13], [14, 15, 16], [17, 18, 19, 20]]
        for i in range(n_items):
            spread_targets.append(random.choice(buckets[i % len(buckets)]))
        random.shuffle(spread_targets)
    else:
        spread_targets = [target_score] * n_items
        
    print(f"\nPhase 1: Generating {n_items} item(s)...")
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    
    temp_metadata = []
    
    for i in range(1, n_items + 1):
        current_target = spread_targets[i-1]
        print(f"  [{i:3d}/{n_items}] Rendering sequence (Target Score: {current_target})...", end=" ", flush=True)
        try:
            item_data = _safe_gen(gen._gen_overlapping_shapes, gen._fallback_overlapping_shapes, current_target)
            temp_path, correct_letter, is_animated = gen.save_temp_item(item_data, i, TEMP_FOLDER)
            
            temp_metadata.append({
                "Temp_Path": temp_path,
                "Difficulty_Score": item_data["score"],
                "Rule_Axes": item_data["rule_axes"],
                "Shape_Types": item_data["shape_types"],
                "Correct_Position": correct_letter,
                "N_Options": item_data["n_options"],
                "Is_Animated": is_animated
            })
            print(f"done (Final Score: {item_data['score']} | Animated: {is_animated})")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

    print("\nPhase 2: Sorting outputs by Difficulty Score and applying Batch Logic...")
    
    # ── BATCH LOGIC ──
    manifest_path = os.path.join(OUTPUT_FOLDER, "manifest.csv")
    current_batch = 1
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                existing_batches = []
                for row in reader:
                    item_id = row.get("Item_ID", "")
                    if "." in str(item_id):
                        try:
                            existing_batches.append(int(str(item_id).split(".")[0]))
                        except ValueError:
                            pass
                if existing_batches:
                    current_batch = max(existing_batches) + 1
        except Exception as e:
            print(f"Warning: Could not read existing manifest. Defaulting to Batch 1. Error: {e}")
    
    temp_metadata.sort(key=lambda x: x["Difficulty_Score"])
    manifest_rows = []
    
    for idx, item in enumerate(temp_metadata, 1):
        score = item["Difficulty_Score"]
        
        batch_item_id = f"{current_batch}.{idx:03d}"
        final_folder_name = f"Seq_overlap_B{current_batch}_Score{score:02d}_{idx:03d}"
        final_folder_path = os.path.join(OUTPUT_FOLDER, final_folder_name)
        
        shutil.move(item["Temp_Path"], final_folder_path)
        
        old_base = os.path.basename(item["Temp_Path"])
        for file in os.listdir(final_folder_path):
            if file.startswith(old_base):
                new_file = file.replace(old_base, final_folder_name)
                os.rename(os.path.join(final_folder_path, file), os.path.join(final_folder_path, new_file))
                
        is_anim = item["Is_Animated"]
        q_ext = ".gif" if is_anim else ".png"
        c_ext = ".gif" if is_anim else ".png"

        manifest_rows.append({
            "Item_ID": batch_item_id,
            "Batch": current_batch,
            "Folder": final_folder_name,
            "Subtype": TARGET_SUBTYPE,
            "Difficulty_Score": score,
            "Is_Animated": is_anim,
            "Correct_Position": item["Correct_Position"],
            "N_Options": item["N_Options"],
            "Rule_Axes": item["Rule_Axes"],
            "Shape_Types": item["Shape_Types"],
            "Question_File": f"{final_folder_name}_question{q_ext}",
            "Choices_File": f"{final_folder_name}_choices{c_ext}",
        })

    if os.path.exists(TEMP_FOLDER): shutil.rmtree(TEMP_FOLDER)

    manifest_path = os.path.join(OUTPUT_FOLDER, "manifest.csv")
    if manifest_rows:
        with open(manifest_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=manifest_rows[0].keys())
            writer.writeheader()
            writer.writerows(manifest_rows)

    print(f"\n{'='*75}")
    print(f"Complete. {len(manifest_rows)} puzzle(s) compiled and sorted.")
    print(f"Output Directory : {OUTPUT_FOLDER}")
    print(f"Manifest File    : {manifest_path}")