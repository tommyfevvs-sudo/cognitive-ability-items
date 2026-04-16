"""
NVR_sequences_accumulation_suite.py
=========================
Non-Verbal Reasoning — Sequences Item Generator
Standalone Module: Accumulation & Snake Suites (Strict Deduplication)
"""

import random, os, math, csv, copy
from PIL import Image, ImageDraw, ImageFont

# ── Target Configuration ───────────────────────────────────────────────────────
SUITE_SUBTYPES = [
    "orbital_accumulation", "orbital_snake",
    "spine_row_accumulation", "spine_row_snake",
    "spine_col_accumulation", "spine_col_snake"
]

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_sequences_accumulation")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Animation / layout constants ───────────────────────────────────────────────
ANIM_FRAME_MS     = 700
ANIM_PAUSE_MS     = 1800
ANSWER_OPTIONS    = 5

FRAMED_SUBTYPES = {"fill_pattern", "multi_element_composition", "multi_element_independent"}
WIDE_SUBTYPES   = {"beads_on_wire"}

# ── Safeguard constants ────────────────────────────────────────────────────────
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
        if _check_sequence_unique(result["full_sequence"]):
            return result
    return fallback_fn(*args)

def _dedup_options(correct, distractors, emergency_fn):
    options = list(distractors[:4])
    all_states = [correct] + options
    
    for i in range(len(options)):
        for _ in range(100):  
            conflict = any(_states_equal(options[i], all_states[j])
                           for j in range(len(all_states)) if j != i + 1)
            
            if not conflict:
                break
                
            current_existing = [all_states[j] for j in range(len(all_states)) if j != i + 1]
            options[i] = emergency_fn(current_existing)
            all_states[i + 1] = options[i]
            
    return options

# ═══════════════════════════════════════════════════════════════════════════════
class NVRSequenceGenerator:

    def __init__(self):
        self.sf           = 4
        self.frame_hd     = 180 * self.sf
        self.frame_border = int(2  * self.sf)
        self.frame_sep    = int(6  * self.sf)
        self.strip_pad    = int(20 * self.sf)
        self.bead_fw_hd   = 300 * self.sf
        self.bead_fh_hd   = 110 * self.sf

        self.all_shapes       = ["circle","square","triangle","pentagon",
                                 "hexagon","arrow","star","cross_shape"]
        self.shade_colors     = ["black", "white", "grey"]

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

    def _draw_shape(self, canvas, shape, fill_shade, cx, cy, r, rotation=0, ow=2.5):
        draw   = ImageDraw.Draw(canvas)
        weight = int(ow * self.sf)
        coords = self._shape_coords(shape, cx, cy, r, rotation)
        
        color_map = {
            "black": "black",
            "white": "white",
            "grey":  "#888888"
        }
        fill_color = color_map.get(fill_shade, "black")
        
        if shape == "circle":
            draw.ellipse(coords, fill=fill_color, outline="black", width=weight)
        else:
            draw.polygon(coords, fill=fill_color, outline="black")
            closed = coords + [coords[0], coords[1]]
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
    def _gen_accumulation(self, tier, subtype):
        cfg        = TIERS[tier]
        complexity = cfg["complexity"]
        n_shown    = N_FRAMES_SHOWN[tier]
        
        is_snake = "snake" in subtype

        if complexity <= 2: 
            n_shape_cycle = 1
            n_fill_cycle = 1
        elif complexity <= 4: 
            n_shape_cycle = random.choice([1, 2])
            n_fill_cycle = random.choice([1, 2])
        else: 
            n_shape_cycle = random.choice([2, 3])
            n_fill_cycle = random.choice([2, 3])

        cycle_length = max(n_shape_cycle, n_fill_cycle)
        
        required_total_elements = max(3, cycle_length + 1)
        start_count = max(1, required_total_elements - n_shown + 1)
        max_visible_shapes = required_total_elements if is_snake else 999
        
        max_drawn_shapes = start_count + n_shown 
        min_arms = max_drawn_shapes + 1
        
        if complexity <= 2:
            n_arms = random.choice([min_arms, min_arms + 1])
        elif complexity <= 4:
            n_arms = random.choice([min_arms, min_arms + 1, min_arms + 2])
        else:
            n_arms = random.choice([min_arms, min_arms + 1])

        valid_steps = [s for s in range(1, n_arms) if math.gcd(s, n_arms) == 1]
        step_size = random.choice(valid_steps)
        
        shapes = random.sample(self.all_shapes[:6], n_shape_cycle)
        fills  = random.sample(self.shade_colors, n_fill_cycle)
        start_arm = random.randint(0, n_arms - 1)

        def _make_accumulation_frame(fi, step_override=None):
            elements = []
            total_elements_in_frame = start_count + fi
            
            start_idx = max(0, total_elements_in_frame - max_visible_shapes)
            
            for k in range(start_idx, total_elements_in_frame):
                current_step = step_override if (step_override is not None and k == total_elements_in_frame - 1) else step_size
                arm_idx = (start_arm + k * current_step) % n_arms
                elements.append({
                    "arm_idx": arm_idx,
                    "shape": shapes[k % len(shapes)],
                    "shade": fills[k % len(fills)]
                })
            return {"subtype": subtype, "n_arms": n_arms, "elements": elements}

        full_sequence = [_make_accumulation_frame(fi) for fi in range(n_shown + 1)]
        
        # Decide output format here so missing_idx can be set accordingly
        output_format = random.choice(["strip", "animated"])
        if output_format == "animated" or random.random() < 0.5:
            missing_idx = len(full_sequence) - 1
        else:
            missing_idx = random.randint(0, len(full_sequence) - 2)
            
        answer_state = full_sequence[missing_idx]

        d1 = _make_accumulation_frame(missing_idx, step_override=(step_size + 1) % n_arms)
        d2 = _make_accumulation_frame(missing_idx, step_override=(step_size - 1) % n_arms)
        
        d3 = copy.deepcopy(answer_state)
        d3["elements"][-1]["shape"] = random.choice([s for s in self.all_shapes if s != d3["elements"][-1]["shape"]] or ["circle"])
        
        d4 = copy.deepcopy(answer_state)
        alt_fill = random.choice([f for f in self.shade_colors if f != answer_state["elements"][-1]["shade"]])
        d4["elements"][-1]["shade"] = alt_fill

        def _emergency(existing):
            for _ in range(100):
                cand = copy.deepcopy(answer_state)
                cand["elements"][-1]["arm_idx"] = random.randint(0, n_arms-1)
                cand["elements"][-1]["shape"] = random.choice(self.all_shapes)
                cand["elements"][-1]["shade"] = random.choice(self.shade_colors)
                if not any(_states_equal(cand, e) for e in existing):
                    return cand
            
            cand["elements"][-1]["arm_idx"] = (cand["elements"][-1]["arm_idx"] + 1) % n_arms
            return cand

        distractors = _dedup_options(answer_state, [d1, d2, d3, d4], _emergency)
        b_est = round(random.uniform(*cfg["b_range"]), 2)
        
        return {
            "subtype": subtype, "full_sequence": full_sequence, "missing_idx": missing_idx, 
            "answer": answer_state, "distractors": distractors,
            "distractor_strategy": "wrong_step+wrong_shape+wrong_shade",
            "tier": tier, "b_estimate": b_est, "age_range": cfg["age_range"],
            "n_rules": 2 + (1 if complexity >= 5 else 0),
            "rule_axes": f"n_arms={n_arms}+step={step_size}+shape_cycle={n_shape_cycle}+fill_cycle={n_fill_cycle}+start_count={start_count}+snake={is_snake}",
            "shape_types": "|".join(shapes), 
            "fill_levels": "|".join(fills),
            "has_secondary": False, "has_hatch": False, "is_multilayer": False, "is_subcell": False,
            "output_format": output_format,
        }

    def _fallback_accumulation(self, tier, subtype):
        cfg = TIERS[tier]
        n_shown = N_FRAMES_SHOWN[tier]
        is_snake = "snake" in subtype
        
        start_count = 1
        n_arms = start_count + n_shown + 2
        shapes = ["circle"]
        fills = ["black"]
        max_visible = 3
        
        def _mf(fi, step=1):
            total = start_count + fi
            start_idx = max(0, total - max_visible) if is_snake else 0
            return {"subtype": subtype, "n_arms": n_arms, "elements": [
                {"arm_idx": (k * step) % n_arms, "shape": shapes[0], "shade": fills[0]}
                for k in range(start_idx, total)
            ]}
            
        full_sequence = [_mf(fi) for fi in range(n_shown + 1)]
        
        # Decide output format here so missing_idx can be set accordingly
        output_format = random.choice(["strip", "animated"])
        if output_format == "animated" or random.random() < 0.5:
            missing_idx = len(full_sequence) - 1
        else:
            missing_idx = random.randint(0, len(full_sequence) - 2)
            
        answer_state = full_sequence[missing_idx]
        
        def fallback_emergency(existing):
            for offset in range(2, 20):
                cand = _mf(missing_idx, step=offset % n_arms)
                if not any(_states_equal(cand, e) for e in existing):
                    return cand
            
            cand = _mf(missing_idx, step=1)
            cand["elements"][-1]["shape"] = "square"
            return cand

        distractors = _dedup_options(answer_state, [
            _mf(missing_idx, step=2), _mf(missing_idx, step=3), 
            _mf(max(0, missing_idx - 1)), _mf(missing_idx + 1)
        ], fallback_emergency)
        
        return {"subtype": subtype, "full_sequence": full_sequence, "missing_idx": missing_idx,
                "answer": answer_state, "distractors": distractors, "distractor_strategy": "fallback",
                "tier": tier, "b_estimate": round(random.uniform(*cfg["b_range"]), 2),
                "age_range": cfg["age_range"], "n_rules": 1, "rule_axes": f"n_arms={n_arms}+step=1",
                "shape_types": "circle", "fill_levels": "black",
                "has_secondary": False, "has_hatch": False, "is_multilayer": False, "is_subcell": False,
                "output_format": output_format}

    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET RENDERERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_orbital_frame(self, canvas, state):
        sf=self.sf; cx=canvas.width//2; cy=canvas.height//2
        n=state["n_arms"]; arm_r=int(self.frame_hd*0.36)
        draw=ImageDraw.Draw(canvas)
        for k in range(n):
            angle=math.radians(k*360/n - 90)
            draw.line([(cx,cy),
                       (int(cx+arm_r*math.cos(angle)),int(cy+arm_r*math.sin(angle)))],
                      fill="black",width=int(2*sf))
        cs=int(10*sf)
        draw.rectangle([cx-cs,cy-cs,cx+cs,cy+cs],fill="black")
        elem_r=int(12*sf)
        for el in state["elements"]:
            angle=math.radians(el["arm_idx"]*360/n - 90)
            ex=int(cx+arm_r*math.cos(angle)); ey=int(cy+arm_r*math.sin(angle))
            self._draw_shape(canvas, el["shape"], el["shade"], ex, ey, elem_r)

    def _render_spine_frame(self, canvas, state):
        sf = self.sf
        cx = canvas.width // 2
        cy = canvas.height // 2
        n = state["n_arms"]
        is_col = "spine_col" in state["subtype"]

        spine_h = int(self.frame_hd * 0.70)
        bot_y = cy + spine_h // 2
        top_y = cy - spine_h // 2

        draw = ImageDraw.Draw(canvas)
        draw.line([(cx, top_y), (cx, bot_y)], fill="black", width=int(3*sf))

        branch_l = int(self.frame_hd * 0.28)
        elem_r = int(12 * sf)
        
        total_levels = math.ceil(n / 2)
        
        def get_branch_coords(idx):
            if is_col:
                half = math.ceil(n / 2)
                side = -1 if idx < half else 1
                level = idx % half
            else:
                side = -1 if idx % 2 == 0 else 1
                level = idx // 2
                
            if total_levels > 1:
                spacing = spine_h / total_levels
                y_pos = bot_y - (level + 0.5) * spacing
            else:
                y_pos = cy
            return side, y_pos

        for k in range(n):
            side, y_pos = get_branch_coords(k)
            x_end = cx + side * branch_l
            draw.line([(cx, y_pos), (x_end, y_pos)], fill="black", width=int(2*sf))

        for el in state["elements"]:
            side, y_pos = get_branch_coords(el["arm_idx"])
            x_end = int(cx + side * branch_l)
            self._draw_shape(canvas, el["shape"], el["shade"], x_end, int(y_pos), elem_r)

    # ═══════════════════════════════════════════════════════════════════════════
    # DISPATCH ROUTINES
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_item(self, tier, subtype):
        return _safe_gen(self._gen_accumulation, self._fallback_accumulation, tier, subtype)

    def render_frame(self, state, show_question_mark=False):
        is_wide = False
        canvas = Image.new("RGB", (self.bead_fw_hd, self.bead_fh_hd) if is_wide else (self.frame_hd, self.frame_hd), "white")
        
        if show_question_mark:
            self._draw_question_mark(canvas, canvas.width//2, canvas.height//2)
            return canvas
            
        if state["subtype"].startswith("orbital"):
            self._render_orbital_frame(canvas, state)
        elif state["subtype"].startswith("spine"):
            self._render_spine_frame(canvas, state)
            
        return canvas

    # ═══════════════════════════════════════════════════════════════════════════
    # STRIP / GIF / SAVING
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_sequence_strip(self, full_sequence, missing_idx, show_answer):
        n_frames  = len(full_sequence)
        use_border = True

        fw  = self.frame_hd
        fh  = self.frame_hd
        bw  = self.frame_border if use_border else 0
        sep = -bw 
        pad = self.strip_pad

        strip_w = pad*2 + n_frames*fw + (n_frames-1)*sep
        strip_h = pad*2 + fh 
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i in range(n_frames):
            x0 = pad + i*(fw + sep)
            y0 = pad
            
            if i == missing_idx and not show_answer:
                img = self.render_frame(None, show_question_mark=True)
            else:
                img = self.render_frame(full_sequence[i])
                
            strip.paste(img, (x0, y0))
            if use_border:
                draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", width=bw)
            
        return strip

    def _render_animated_gif(self, full_sequence, missing_idx):
        sf      = self.sf
        use_border = True

        fw = self.frame_hd
        fh = self.frame_hd
        bw = self.frame_border if use_border else 0
        
        side_pad = int(300 * sf) 
        
        bot_pad = int(15 * sf) 
        
        cw = fw + (2 * side_pad) 
        ch = fh + bot_pad 

        def _gif_frame(state, is_q=False):
            c = Image.new("RGB", (cw, ch), "white")
            d = ImageDraw.Draw(c)
            
            content = (Image.new("RGB", (fw, fh), "white") if is_q else self.render_frame(state))
            if is_q:
                self._draw_question_mark(content, fw//2, fh//2)
            
            c.paste(content, (side_pad, 0)) 
            if use_border:
                d.rectangle([side_pad, 0, side_pad + fw, fh], outline="black", width=bw)
            
            sm = c.resize((cw//sf, ch//sf), Image.Resampling.LANCZOS)
            return sm.convert("P", palette=Image.Palette.ADAPTIVE, colors=32)

        gif_frames = []
        durations = []
        
        for i, state in enumerate(full_sequence):
            if i == missing_idx:
                gif_frames.append(_gif_frame(state, is_q=True))
                durations.append(ANIM_PAUSE_MS)
            else:
                gif_frames.append(_gif_frame(state, is_q=False))
                durations.append(ANIM_FRAME_MS)

        return gif_frames, durations

    def _render_answer_strip(self, options):
        use_border = True

        fw  = self.frame_hd
        fh  = self.frame_hd
        bw  = self.frame_border if use_border else 0
        gap = int(16 * self.sf)

        pad_x  = int(24 * self.sf)
        pad_y  = int(20 * self.sf)
        
        lbl_gap = int(27 * self.sf) 
        lbl_h  = int(64 * self.sf)
        
        n = len(options)

        strip_w = 2*pad_x + n*fw + (n-1)*gap
        strip_h = pad_y + fh + lbl_gap + lbl_h 
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE")):
            x0 = pad_x + i*(fw + gap)
            y0 = pad_y
            cx = x0 + fw//2
            
            strip.paste(self.render_frame(opt), (x0, y0))
            if use_border:
                draw.rectangle([x0, y0, x0+fw, y0+fh], outline="black", width=bw)
                
            bbox = draw.textbbox((0,0), lbl, font=self.font_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, y0+fh+lbl_gap), lbl, font=self.font_hd, fill="black")
            
        return strip

    def save_item(self, item_data, item_id, out_root):
        sf=self.sf; subtype=item_data["subtype"]
        
        folder_name=f"Seq_{subtype}_{item_id:03d}"
        folder_path=os.path.join(out_root, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        base=folder_name
        full_sequence = item_data["full_sequence"]
        missing_idx = item_data["missing_idx"]
        answer = item_data["answer"]

        # Retrieve format determined during generation
        output_format = item_data.get("output_format", "strip")

        # Always save Choices File
        distractors=list(item_data.get("distractors",[]))
        while len(distractors)<4: distractors.append(copy.deepcopy(answer))
        distractors=distractors[:4]
        correct_pos=random.randint(0,4)
        correct_letter="ABCDE"[correct_pos]
        options=list(distractors); options.insert(correct_pos,answer)

        c_path = os.path.join(folder_path, f"{base}_choices.png")
        c_hd = self._render_answer_strip(options)
        c_hd.resize((c_hd.width//sf, c_hd.height//sf), Image.Resampling.LANCZOS).save(c_path)

        q_path = ""
        s_path = ""
        p_path = ""

        if output_format == "strip":
            # Save Comic Strip WITH Question Mark
            q_path = os.path.join(folder_path, f"{base}_question_strip.png")
            q_hd = self._render_sequence_strip(full_sequence, missing_idx, show_answer=False)
            q_hd.resize((q_hd.width//sf, q_hd.height//sf), Image.Resampling.LANCZOS).save(q_path)

            # Save Solved Comic Strip
            s_path = os.path.join(folder_path, f"{base}_answer_strip.png")
            s_hd = self._render_sequence_strip(full_sequence, missing_idx, show_answer=True)
            s_hd.resize((s_hd.width//sf, s_hd.height//sf), Image.Resampling.LANCZOS).save(s_path)
            
        else: # output_format == "animated"
            # Save Animated GIF
            p_path = os.path.join(folder_path, f"{base}_animated.gif")
            gf, dur = self._render_animated_gif(full_sequence, missing_idx)
            gf[0].save(p_path, save_all=True, append_images=gf[1:], duration=dur, loop=0, optimize=False)

        return folder_name, q_path, p_path, c_path, correct_letter, output_format

# ═══════════════════════════════════════════════════════════════════════════════
# SPREAD HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def build_spread_jobs(n_items, tiers=None):
    if tiers is None: tiers=list(TIERS.keys())
    jobs=[]; tier_work=tiers[:]
    while len(jobs)<n_items:
        random.shuffle(tier_work)
        n_round=min(len(tier_work),n_items-len(jobs))
        subs=[SUITE_SUBTYPES[k%len(SUITE_SUBTYPES)] for k in range(len(jobs),len(jobs)+n_round)]
        random.shuffle(subs)
        for t,s in zip(tier_work[:n_round],subs): jobs.append((s,t))
    random.shuffle(jobs); return jobs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    from collections import Counter
    gen=NVRSequenceGenerator()
    print(f"\nNVR Sequence Item Generator  —  Suite: Accumulation & Snake")
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
               
    jobs=build_spread_jobs(n_items, tiers=sel_tiers)
    tier_counts=Counter(t for _,t in jobs)
    subtype_counts=Counter(s for s,_ in jobs)
    
    print(f"\nGenerating {n_items} item(s)  →  {OUTPUT_FOLDER}")
    for t in tier_names:
        if tier_counts[t]:
            cfg=TIERS[t]
            print(f"  {t:12s}: {tier_counts[t]:3d}  (b≈{cfg['b_range']}  age {cfg['age_range']})")
    print("\nSubtypes generating:")
    for s, count in subtype_counts.items():
        print(f"  {s:30s}: {count}")
    print()

    manifest_rows=[]
    for item_id,(subtype,tier) in enumerate(jobs,1):
        print(f"  [{item_id:3d}/{n_items}]  {subtype:30s} | {tier:10s} ...", end=" ",flush=True)
        try:
            item_data=gen.generate_item(tier, subtype)
            folder,sp,pp,cp,cl,os_=gen.save_item(item_data,item_id,OUTPUT_FOLDER)
            manifest_rows.append({
                "Item_ID":item_id,"Folder":folder,"Subtype":subtype,
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
                "Static_PNG":os.path.basename(sp) if sp else "",
                "Animated_GIF":os.path.basename(pp) if pp else "",
                "Choices_File":os.path.basename(cp),
            })
            print(f"done ({os_})")
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
