"""
NVR_sequences_multi_element_composition.py
=========================
Non-Verbal Reasoning — Sequences Item Generator
Standalone Module: Multi-Element Composition
"""

import random, os, math, csv, copy
from PIL import Image, ImageDraw, ImageFont

# ── Target Configuration ───────────────────────────────────────────────────────
TARGET_SUBTYPE = "multi_element_composition"

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, f"NVR_Sequences_{TARGET_SUBTYPE.title()}")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Animation / layout constants ───────────────────────────────────────────────
ANIMATED_SUBTYPES = {"grid_movement", "orbital_rotation", "beads_on_wire", "frame_border"}
ANIM_FRAME_MS     = 700
ANIM_PAUSE_MS     = 1800
ANSWER_OPTIONS    = 5

FRAMED_SUBTYPES = {"fill_pattern", "multi_element_composition", "multi_element_independent"}
WIDE_SUBTYPES   = {"beads_on_wire"}

# ── Safeguard constants ────────────────────────────────────────────────────────
MIN_SIZE_DELTA_FRAC = 0.04
MAX_DEDUP_ATTEMPTS  = 20
MAX_GEN_RETRIES     = 8

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

# ── Difficulty tiers ───────────────────────────────────────────────────────────
TIERS = {
    "easy":      {"b_range": (-2.5,-1.5), "age_range": "6-8",   "complexity": 1},
    "easy_med":  {"b_range": (-1.5,-0.5), "age_range": "8-10",  "complexity": 2},
    "medium":    {"b_range": (-0.5, 0.5), "age_range": "10-12", "complexity": 3},
    "hard":      {"b_range": ( 0.5, 1.5), "age_range": "12-14", "complexity": 4},
    "very_hard": {"b_range": ( 1.5, 2.5), "age_range": "14-16", "complexity": 5},
    "extreme":   {"b_range": ( 2.5, 4.0), "age_range": "16+",   "complexity": 6},
}

N_FRAMES_SHOWN = {
    "easy": 4, "easy_med": 4, "medium": 4,
    "hard": 3, "very_hard": 3, "extreme": 3,
}

# ═══════════════════════════════════════════════════════════════════════════════
# SAFEGUARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _state_key(state):
    def _norm(v):
        if isinstance(v, dict):  return tuple(sorted((k, _norm(w)) for k, w in v.items()))
        if isinstance(v, list):  return tuple(_norm(i) for i in v)
        if isinstance(v, float): return round(v, 4)
        return v
    return _norm(state)

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

def _dedup_options(correct, distractors, emergency_fn):
    options = list(distractors[:4])
    all_states = [correct] + options
    for i in range(len(options)):
        for _ in range(MAX_DEDUP_ATTEMPTS):
            conflict = any(_states_equal(options[i], all_states[j])
                           for j in range(len(all_states)) if j != i + 1)
            if not conflict:
                break
            options[i] = emergency_fn([correct] + [options[k] for k in range(len(options)) if k != i])
            all_states[i + 1] = options[i]
    return options

# ═══════════════════════════════════════════════════════════════════════════════
class NVRSequenceGenerator:

    def __init__(self):
        self.sf           = 4
        self.frame_hd     = 180 * self.sf
        self.frame_border = int(4  * self.sf)
        self.frame_sep    = int(6  * self.sf)
        self.strip_pad    = int(20 * self.sf)
        self.bead_fw_hd   = 300 * self.sf
        self.bead_fh_hd   = 110 * self.sf

        half = self.frame_hd // 2
        self.r_large  = int(half * 0.62)
        self.r_medium = int(half * 0.43)
        self.r_small  = int(half * 0.28)

        self.all_shapes       = ["circle","square","triangle","pentagon",
                                 "hexagon","arrow","star","cross_shape"]
        self.rotatable_shapes = ["triangle","arrow","pentagon","star"]
        self.simple_shapes    = ["circle","square","hexagon","cross_shape"]

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
                        if any(b in lf for b in ["italic","light","bold","semibold","medium","thin"]):
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

    @staticmethod
    def _use_panel_border(subtype):
        return subtype in FRAMED_SUBTYPES

    # ═══════════════════════════════════════════════════════════════════════════
    # SHAPE / DRAW HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _shape_coords(self, shape, cx, cy, r, rotation=0):
        pts = []
        if shape == "circle":
            return [cx-r, cy-r, cx+r, cy+r]
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
                if len(wpts) > 1:
                    draw.line(wpts, fill="black", width=2*sf)
        elif category == "mini_tri":
            ts, gp = 5*sf, 18*sf
            for tx in range(0, size, gp):
                for ty in range(0, size, gp):
                    draw.polygon([(tx,ty-ts),(tx+ts,ty+ts),(tx-ts,ty+ts)], fill="black")
        elif category == "lines":
            for li in range(-size, size*2, 13*sf):
                if variant == "vertical":
                    draw.line([(li,0),(li,size)], fill="black", width=2*sf)
                elif variant == "diagonal_tl_br":
                    draw.line([(li,0),(li+size,size)], fill="black", width=2*sf)
                else:
                    draw.line([(li,0),(li-size,size)], fill="black", width=2*sf)
        elif category == "grids":
            gs = 20*sf if "large" in variant else 9*sf
            for gx in range(0, size+10*sf, gs):
                draw.line([(gx,0),(gx,size)], fill="black", width=2*sf)
            for gy in range(0, size+10*sf, gs):
                draw.line([(0,gy),(size,gy)], fill="black", width=2*sf)

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
            if shape == "circle":
                draw.ellipse(coords, fill="black", outline="black", width=weight)
            else:
                draw.polygon(coords, fill="black", outline="black")
        elif fill == "hollow":
            if shape == "circle":
                draw.ellipse(coords, fill="white", outline="black", width=weight)
            else:
                draw.polygon(coords, fill="white", outline="black")
                closed = coords + [coords[0], coords[1]]
                draw.line(closed, fill="black", width=weight, joint="curve")
        else:
            self._draw_masked_shape(canvas, shape, fill, cx, cy, r, rotation, ow)

    def _draw_striped_shape(self, canvas, shape, cx, cy, r, stripe_angle_deg, ow=2.5):
        size  = int(r * 3.0)
        buf   = Image.new("RGBA", (size,size), (255,255,255,0))
        mask  = Image.new("L",   (size,size), 0)
        bdraw = ImageDraw.Draw(buf)
        cx2, cy2 = size//2, size//2
        rad   = math.radians(stripe_angle_deg)
        dx, dy = math.cos(rad), math.sin(rad)
        px, py = -dy, dx
        step  = max(int(12 * self.sf), 1)
        diag  = int(math.sqrt(2) * size) + 2
        for i in range(-diag, diag, step):
            sx = cx2 + i * px
            sy = cy2 + i * py
            x1 = sx - diag * dx
            y1 = sy - diag * dy
            x2 = sx + diag * dx
            y2 = sy + diag * dy
            if abs(x2-x1) > 0.5 or abs(y2-y1) > 0.5:
                bdraw.line([(x1,y1),(x2,y2)], fill="black", width=max(2*self.sf,1))
        loc_pts  = self._shape_coords(shape, cx2, cy2, r, 0)
        glob_pts = self._shape_coords(shape, cx, cy, r, 0)
        draw     = ImageDraw.Draw(canvas)
        weight   = int(ow * self.sf)
        if shape == "circle":
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx-size//2), int(cy-size//2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight)
        else:
            draw.polygon(glob_pts, fill="black")
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx-size//2), int(cy-size//2)), mask)
            closed = glob_pts + [glob_pts[0], glob_pts[1]]
            draw.line(closed, fill="black", width=weight, joint="curve")

    def _draw_question_mark(self, canvas, cx, cy):
        draw = ImageDraw.Draw(canvas)
        txt  = "?"
        bbox = draw.textbbox((0,0), txt, font=self.font_hd)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((cx-tw//2, cy-th//2), txt, font=self.font_hd, fill="black")

    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET SUBTYPE GENERATOR & FALLBACK
    # ═══════════════════════════════════════════════════════════════════════════
    def _gen_multi_element_composition(self, tier):
        cfg        = TIERS[tier]
        complexity = cfg["complexity"]
        n_shown    = N_FRAMES_SHOWN[tier]

        n_shapes  = 2 if complexity<=4 else 3
        rot_step  = {1:90,2:60,3:45,4:45,5:30,6:30}[complexity]
        shape_pool = self.rotatable_shapes + self.simple_shapes
        shapes    = random.sample(shape_pool, n_shapes)
        fills     = random.choices(["hollow","solid"], k=n_shapes)
        offsets   = [(0.0,0.0),(0.30,0.0),(-0.15,0.28)][:n_shapes]

        if complexity<=2:
            t_type="rotation_rigid"
        elif complexity<=4:
            t_type=random.choice(["rotation_rigid","size_inversion"])
        else:
            t_type=random.choice(["counter_rotation","size_inversion",
                                   "colour_inversion","shape_morph"])

        size_fracs   = [0.28,0.38,0.50]
        morph_pool   = ["circle","square","triangle","pentagon","hexagon"]

        def _morph_shape(base_shape, fi):
            base_idx = morph_pool.index(base_shape) if base_shape in morph_pool else 0
            return morph_pool[(base_idx + fi) % len(morph_pool)]

        def _make_comp_frame(fi):
            layers = []
            for k, shape in enumerate(shapes):
                cur_shape = _morph_shape(shape,fi) if t_type=="shape_morph" else shape
                if t_type=="rotation_rigid":
                    base_rot = (fi*rot_step) % 360
                elif t_type=="counter_rotation":
                    base_rot = (fi*rot_step*(1 if k%2==0 else -1)) % 360
                else:
                    base_rot = 0
                sf_idx = k % len(size_fracs)
                if t_type=="size_inversion" and fi%2==1:
                    sf_idx = (k+1) % len(size_fracs)
                fill = ("solid" if fi%2==0 else "hollow") if t_type=="colour_inversion" else fills[k]
                ox,oy = offsets[k]
                layers.append({"shape":cur_shape,"size_frac":size_fracs[sf_idx],
                               "rotation":base_rot,"fill":fill,"rel_pos":(ox,oy)})
            return {"subtype":"multi_element_composition","layers":layers}

        frames = [_make_comp_frame(fi) for fi in range(n_shown+1)]
        answer_state = frames[-1]; shown_frames = frames[:-1]

        correct = answer_state
        d1 = _make_comp_frame(n_shown-1)
        d2 = copy.deepcopy(correct)
        for lyr in d2["layers"]: lyr["rotation"]=(-lyr["rotation"])%360
        d3 = _make_comp_frame(0)
        d3["layers"][0]["rotation"] = correct["layers"][0]["rotation"]
        d4 = copy.deepcopy(correct)
        for lyr in d4["layers"]: lyr["fill"]="solid" if lyr["fill"]=="hollow" else "hollow"

        def _emergency(existing):
            for step in [2,3,4,5]:
                cand = _make_comp_frame(step % (n_shown+2))
                if all(not _states_equal(cand,e) for e in existing):
                    return cand
            return copy.deepcopy(d2)

        distractors = _dedup_options(answer_state,[d1,d2,d3,d4],_emergency)
        b_est = round(random.uniform(*cfg["b_range"]),2)
        return {
            "subtype":"multi_element_composition","frames":shown_frames,"answer":answer_state,
            "distractors":distractors,
            "distractor_strategy":"rot_behind+wrong_dir+size_miss+fill_swap",
            "tier":tier,"b_estimate":b_est,"age_range":cfg["age_range"],
            "n_rules":1+(1 if t_type!="rotation_rigid" else 0),
            "rule_axes":f"{t_type}+rot_step={rot_step}",
            "shape_types":"|".join(shapes),"fill_levels":"|".join(fills),
            "has_secondary":False,"has_hatch":False,"is_multilayer":True,"is_subcell":False,
        }

    def _fallback_multi_element_composition(self, tier):
        cfg=TIERS[tier]; n_shown=N_FRAMES_SHOWN[tier]
        def _mf(fi): return {"subtype":"multi_element_composition","layers":[
            {"shape":"circle","size_frac":0.35,"rotation":(fi*90)%360,
             "fill":"hollow","rel_pos":(0.0,0.0)},
            {"shape":"square","size_frac":0.25,"rotation":(fi*90)%360,
             "fill":"solid","rel_pos":(0.30,0.0)},]}
        frames=[_mf(fi) for fi in range(n_shown+1)]
        answer_state=frames[-1]; shown_frames=frames[:-1]
        distractors=_dedup_options(answer_state,[
            _mf(n_shown-1),_mf(n_shown+1),_mf(n_shown+2),_mf(n_shown-2)
        ],lambda ex:_mf(n_shown+3))
        return {"subtype":"multi_element_composition","frames":shown_frames,"answer":answer_state,
                "distractors":distractors,"distractor_strategy":"fallback",
                "tier":tier,"b_estimate":round(random.uniform(*cfg["b_range"]),2),
                "age_range":cfg["age_range"],"n_rules":1,"rule_axes":"rotation_rigid+90",
                "shape_types":"circle|square","fill_levels":"hollow|solid",
                "has_secondary":False,"has_hatch":False,"is_multilayer":True,"is_subcell":False}


    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET RENDERER
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_comp_frame(self, canvas, state):
        cx=canvas.width//2; cy=canvas.height//2; half=self.frame_hd//2
        for layer in state["layers"]:
            ox=int(layer["rel_pos"][0]*half); oy=int(layer["rel_pos"][1]*half)
            r=int(layer["size_frac"]*half)
            self._draw_shape(canvas,layer["shape"],layer["fill"],
                             cx+ox,cy+oy,r,layer.get("rotation",0))

    # ═══════════════════════════════════════════════════════════════════════════
    # DISPATCH ROUTINES
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_item(self, tier):
        return _safe_gen(self._gen_multi_element_composition, self._fallback_multi_element_composition, tier)

    def render_frame(self, state, show_question_mark=False):
        is_wide = TARGET_SUBTYPE in WIDE_SUBTYPES
        canvas = Image.new("RGB", (self.bead_fw_hd, self.bead_fh_hd) if is_wide else (self.frame_hd, self.frame_hd), "white")
        
        if show_question_mark:
            self._draw_question_mark(canvas, canvas.width//2, canvas.height//2)
            return canvas
            
        self._render_comp_frame(canvas, state)
        return canvas

    # ═══════════════════════════════════════════════════════════════════════════
    # STRIP / GIF / SAVING  (Unchanged boilerplate)
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_sequence_strip(self, frames, show_answer, answer_state=None):
        n_frames  = len(frames) + 1
        is_wide   = TARGET_SUBTYPE in WIDE_SUBTYPES
        use_border = self._use_panel_border(TARGET_SUBTYPE)

        fw  = self.bead_fw_hd if is_wide else self.frame_hd
        fh  = self.bead_fh_hd if is_wide else self.frame_hd
        bw  = self.frame_border if use_border else 0
        sep = self.frame_sep
        pad = self.strip_pad
        lbl_h = int(40 * self.sf)

        strip_w = pad*2 + n_frames*(fw + 2*bw) + (n_frames-1)*sep
        strip_h = pad*2 + fh + 2*bw + lbl_h
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i in range(n_frames):
            x0 = pad + i*(fw + 2*bw + sep)
            y0 = pad
            if use_border:
                draw.rectangle([x0, y0, x0+fw+2*bw, y0+fh+2*bw], outline="black", width=bw)
            if i < len(frames):
                img = self.render_frame(frames[i])
            else:
                img = (self.render_frame(answer_state) if show_answer and answer_state else self.render_frame(None, show_question_mark=True))
            strip.paste(img, (x0+bw, y0+bw))
            lbl  = str(i+1) if i < len(frames) else "?"
            bbox = draw.textbbox((0,0), lbl, font=self.qlabel_hd)
            tw   = bbox[2] - bbox[0]
            draw.text((x0+bw+fw//2 - tw//2, y0+bw+fh + int(8*self.sf)), lbl, font=self.qlabel_hd, fill="black")
        return strip

    def _render_animated_gif(self, frames, answer_state):
        sf      = self.sf
        is_wide = TARGET_SUBTYPE in WIDE_SUBTYPES
        use_border = self._use_panel_border(TARGET_SUBTYPE)

        fw = self.bead_fw_hd if is_wide else self.frame_hd
        fh = self.bead_fh_hd if is_wide else self.frame_hd
        bw = self.frame_border if use_border else 0
        cw = fw + 2*bw
        ch = fh + 2*bw

        def _gif_frame(state, is_q=False):
            c = Image.new("RGB", (cw, ch), "white")
            d = ImageDraw.Draw(c)
            if use_border:
                d.rectangle([0, 0, cw-1, ch-1], outline="black", width=bw)
            content = (Image.new("RGB", (fw, fh), "white") if is_q else self.render_frame(state))
            if is_q:
                self._draw_question_mark(content, fw//2, fh//2)
            c.paste(content, (bw, bw))
            sm = c.resize((cw//sf, ch//sf), Image.Resampling.LANCZOS)
            return sm.convert("P", palette=Image.Palette.ADAPTIVE, colors=32)

        gif_frames = [_gif_frame(f) for f in frames] + [_gif_frame(answer_state, is_q=True)]
        durations  = [ANIM_FRAME_MS] * len(frames) + [ANIM_PAUSE_MS]
        return gif_frames, durations

    def _render_answer_strip(self, options):
        is_wide    = TARGET_SUBTYPE in WIDE_SUBTYPES
        use_border = self._use_panel_border(TARGET_SUBTYPE)

        fw  = self.bead_fw_hd if is_wide else self.frame_hd
        fh  = self.bead_fh_hd if is_wide else self.frame_hd
        bw  = self.frame_border if use_border else 0
        gap = int(16 * self.sf)

        pad_x  = int(24 * self.sf)
        pad_y  = int(20 * self.sf)
        lbl_h  = int(64 * self.sf)
        lbl_gap = int(12 * self.sf)
        n = len(options)

        strip_w = 2*pad_x + n*(fw + 2*bw) + (n-1)*gap
        strip_h = pad_y + fh + 2*bw + lbl_gap + lbl_h
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE")):
            x0 = pad_x + i*(fw + 2*bw + gap)
            y0 = pad_y
            cx = x0 + bw + fw//2
            if use_border:
                draw.rectangle([x0, y0, x0+fw+2*bw, y0+fh+2*bw], outline="black", width=bw)
            strip.paste(self.render_frame(opt), (x0+bw, y0+bw))
            if use_border:
                draw.rectangle([x0, y0, x0+fw+2*bw, y0+fh+2*bw], outline="black", width=bw)
            bbox = draw.textbbox((0,0), lbl, font=self.font_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, y0+bw+fh+lbl_gap), lbl, font=self.font_hd, fill="black")
        return strip

    def save_item(self, item_data, item_id, out_root):
        sf=self.sf; subtype=item_data["subtype"]; tier=item_data["tier"]
        animated=subtype in ANIMATED_SUBTYPES
        tier_label=tier.replace("_","-").title()
        folder_name=f"Seq_{subtype[:12]}_{tier_label}_{item_id:03d}"
        folder_path=os.path.join(out_root,folder_name)
        os.makedirs(folder_path,exist_ok=True)
        base=folder_name
        s_path=os.path.join(folder_path,f"{base}_static.png")

        frames=item_data["frames"]; answer=item_data["answer"]

        static_hd=self._render_sequence_strip(frames,show_answer=True,answer_state=answer)
        static_hd.resize((static_hd.width//sf,static_hd.height//sf), Image.Resampling.LANCZOS).save(s_path)

        distractors=list(item_data.get("distractors",[]))
        while len(distractors)<4: distractors.append(copy.deepcopy(answer))
        distractors=distractors[:4]
        correct_pos=random.randint(0,4)
        correct_letter="ABCDE"[correct_pos]
        options=list(distractors); options.insert(correct_pos,answer)

        if animated:
            p_path=os.path.join(folder_path,f"{base}_animated.gif")
            c_path=os.path.join(folder_path,f"{base}_choices.png")
            gf,dur=self._render_animated_gif(frames,answer)
            gf[0].save(p_path,save_all=True,append_images=gf[1:], duration=dur,loop=0,optimize=False)
            c_hd=self._render_answer_strip(options)
            c_hd.resize((c_hd.width//sf,c_hd.height//sf), Image.Resampling.LANCZOS).save(c_path)
            output_style="animated"
        else:
            p_path=os.path.join(folder_path,f"{base}_question.gif")
            c_path=os.path.join(folder_path,f"{base}_choices.gif")
            q_hd=self._render_sequence_strip(frames,show_answer=False)
            q_hd.resize((q_hd.width//sf,q_hd.height//sf), Image.Resampling.LANCZOS).save(
                p_path,save_all=True,append_images=[],duration=500,loop=0)
            c_hd=self._render_answer_strip(options)
            c_hd.resize((c_hd.width//sf,c_hd.height//sf), Image.Resampling.LANCZOS).save(
                c_path,save_all=True,append_images=[],duration=500,loop=0)
            output_style="static"

        return folder_name,s_path,p_path,c_path,correct_letter,output_style

# ═══════════════════════════════════════════════════════════════════════════════
# SPREAD HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def build_spread_jobs(n_items, subtypes=None, tiers=None):
    if subtypes is None: subtypes=[TARGET_SUBTYPE]
    if tiers    is None: tiers=list(TIERS.keys())
    jobs=[]; tier_work=tiers[:]
    while len(jobs)<n_items:
        random.shuffle(tier_work)
        n_round=min(len(tier_work),n_items-len(jobs))
        subs=[subtypes[k%len(subtypes)] for k in range(len(jobs),len(jobs)+n_round)]
        random.shuffle(subs)
        for t,s in zip(tier_work[:n_round],subs): jobs.append((s,t))
    random.shuffle(jobs); return jobs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    from collections import Counter
    gen=NVRSequenceGenerator()
    print(f"\nNVR Sequence Item Generator  —  Standalone: {TARGET_SUBTYPE}")
    print("="*56)
    
    raw_n=input("How many items? [default: 18]: ").strip()
    n_items=int(raw_n) if raw_n.isdigit() and int(raw_n)>0 else 18

    print("\n── Filter by difficulty tier ───────────────────────────────────")
    print("Enter a number or name to restrict to one tier, or press Enter to keep all.")
    tier_names=list(TIERS.keys())
    for i,t in enumerate(tier_names):
        cfg=TIERS[t]
        print(f"  {i} = {t:12s}  difficulty b≈{cfg['b_range']}  target age {cfg['age_range']}")
    
    raw_t=input("Tier choice [default: all]: ").strip() or "all"
    sel_tiers=(tier_names if raw_t=="all"
               else [tier_names[int(raw_t)%len(tier_names)]] if raw_t.isdigit()
               else [raw_t] if raw_t in TIERS else tier_names)
               
    jobs=build_spread_jobs(n_items, subtypes=[TARGET_SUBTYPE], tiers=sel_tiers)
    tier_counts=Counter(t for _,t in jobs)
    
    print(f"\nGenerating {n_items} item(s)  →  {OUTPUT_FOLDER}")
    for t in tier_names:
        if tier_counts[t]:
            cfg=TIERS[t]
            print(f"  {t:12s}: {tier_counts[t]:3d}  (b≈{cfg['b_range']}  age {cfg['age_range']})")
    print()

    manifest_rows=[]
    for item_id,(_,tier) in enumerate(jobs,1):
        print(f"  [{item_id:3d}/{n_items}]  {TARGET_SUBTYPE:30s} | {tier} ...", end=" ",flush=True)
        try:
            item_data=gen.generate_item(tier)
            folder,sp,pp,cp,cl,os_=gen.save_item(item_data,item_id,OUTPUT_FOLDER)
            manifest_rows.append({
                "Item_ID":item_id,"Folder":folder,"Subtype":TARGET_SUBTYPE,
                "Output_Style":os_,"Difficulty_Tier":tier,
                "Difficulty_Score":TIERS[tier]["complexity"],
                "b_estimate":item_data["b_estimate"],"Age_Range":item_data["age_range"],
                "N_Rules":item_data["n_rules"],"Rule_Axes":item_data["rule_axes"],
                "Correct_Position":cl,
                "Distractor_Strategy":item_data.get("distractor_strategy",""),
                "Shape_Types":item_data.get("shape_types",""),
                "Fill_Levels":item_data.get("fill_levels",""),
                "Has_Secondary":item_data.get("has_secondary",False),
                "Has_Hatch":item_data.get("has_hatch",False),
                "Is_MultiLayer":item_data.get("is_multilayer",False),
                "Is_SubCell":item_data.get("is_subcell",False),
                "Static_PNG":os.path.basename(sp),
                "Puzzle_File":os.path.basename(pp),
                "Choices_File":os.path.basename(cp),
            })
            print("done")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

    manifest_path=os.path.join(OUTPUT_FOLDER,"manifest.csv")
    if manifest_rows:
        with open(manifest_path,"w",newline="",encoding="utf-8") as fh:
            writer=csv.DictWriter(fh,fieldnames=manifest_rows[0].keys())
            writer.writeheader(); writer.writerows(manifest_rows)

    print(f"\n{'='*56}")
    print(f"Complete.  {len(manifest_rows)} item(s) saved.")
    print(f"Output  : {OUTPUT_FOLDER}")
    print(f"Manifest: {manifest_path}")
