"""
NVR_sequences_frame_border.py
=========================
Non-Verbal Reasoning — Sequences Item Generator
Standalone Module: Unified Core Logic (7 Variables)
"""

import random, os, math, csv, copy
from PIL import Image, ImageDraw, ImageFont

# ── Target Configuration ───────────────────────────────────────────────────────
TARGET_SUBTYPE = "frame_border"

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, f"NVR_Sequences_{TARGET_SUBTYPE.title()}")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Safeguard constants ────────────────────────────────────────────────────────
MAX_DEDUP_ATTEMPTS  = 20
N_FRAMES_SHOWN      = 4
ANIMATED_SUBTYPES   = {"grid_movement", "orbital_rotation", "beads_on_wire", "frame_border"}
ANIM_FRAME_MS       = 700
ANIM_PAUSE_MS       = 1800
WIDE_SUBTYPES       = {"beads_on_wire"}

# ── Font search paths ──────────────────────────────────────────────────────────
FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts", "/usr/share/fonts/truetype",
]
FALLBACK_FONTS = ["/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/Arial.ttf"]

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

def _dedup_options(correct, distractors, emergency_fn):
    options = []
    seen_states = {_state_key(correct)}
    for d in distractors:
        state = copy.deepcopy(d)
        for _ in range(MAX_DEDUP_ATTEMPTS):
            key = _state_key(state)
            if key not in seen_states: break
            state = emergency_fn(list(seen_states))
        options.append(state)
        seen_states.add(_state_key(state))
    return options[:4]

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

        self.simple_shapes = ["circle","square","hexagon","cross_shape", "triangle"]
        
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
                        if any(b in lf for b in ["italic", "light", "bold", "semibold", "medium", "thin"]):
                            continue
                        try:
                            fp = os.path.join(d, fname)
                            self.font_hd = ImageFont.truetype(fp, 44*self.sf)
                            self.qlabel_hd = ImageFont.truetype(fp, 28*self.sf)
                            found = True; break
                        except Exception: continue
                if found: break
            except Exception: continue
            
        if not found:
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd = ImageFont.truetype(fp, 44*self.sf)
                        self.qlabel_hd = ImageFont.truetype(fp, 28*self.sf)
                        found = True; break
                    except Exception: continue
                    
        if not getattr(self, 'font_hd', None): 
            self.font_hd = self.qlabel_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════
    # STRICT 7-VARIABLE LOGIC ROLLER
    # ═══════════════════════════════════════════════════════════════════════════
    def _roll_logic(self, difficulty_level):
        all_vars = [1, 2, 3, 4, 5, 6, 7]
        active_vars = random.sample(all_vars, difficulty_level)
        
        if 2 in active_vars and 1 in active_vars:
            active_vars.remove(2)
            available = [v for v in all_vars if v not in active_vars and v != 2]
            active_vars.append(random.choice(available))

        logic = {"active": active_vars}
        
        base_styles = ["solid", "dashed", "dotted", "double"]
        if 1 in active_vars:
            logic["v1_rule"] = random.choice(["toggle", "cycle3"])
            logic["v1_seq"] = random.sample(base_styles, 3)
        else:
            logic["v1_rule"] = "static"
            logic["v1_seq"] = ["solid"] if 2 in active_vars else [random.choice(base_styles)]

        if 2 in active_vars:
            logic["v2_rule"] = "pendulum"
            logic["v2_seq"] = ["thin", "medium", "thick", "medium"]
        else:
            logic["v2_rule"] = "static"
            logic["v2_seq"] = ["medium"]

        if 3 in active_vars:
            logic["v3_rule"] = "cycle3"
            logic["v3_seq"] = random.sample(self.simple_shapes, 3)
        else:
            logic["v3_rule"] = "static"
            logic["v3_seq"] = [random.choice(self.simple_shapes)]

        if 4 in active_vars:
            logic["v4_rule"] = random.choice(["cw", "ccw", "diagonal"])
            start = random.randint(0, 3)
            if logic["v4_rule"] == "cw": logic["v4_seq"] = [(start + i) % 4 for i in range(6)]
            elif logic["v4_rule"] == "ccw": logic["v4_seq"] = [(start - i) % 4 for i in range(6)]
            else: logic["v4_seq"] = [(start + (i*2)) % 4 for i in range(6)] 
        else:
            logic["v4_rule"] = "static"
            logic["v4_seq"] = [random.randint(0, 3)]

        if 5 in active_vars:
            logic["v5_rule"] = "toggle"
            logic["v5_seq"] = ["solid", "hollow"] if random.random() > 0.5 else ["hollow", "solid"]
        else:
            logic["v5_rule"] = "static"
            logic["v5_seq"] = [random.choice(["solid", "hollow"])]

        if 6 in active_vars:
            logic["v6_rule"] = random.choice(["grow", "shrink", "toggle", "cycle3"])
            if logic["v6_rule"] == "grow": logic["v6_seq"] = [1, 2, 3, 4, 1, 2]
            elif logic["v6_rule"] == "shrink": logic["v6_seq"] = [4, 3, 2, 1, 4, 3]
            elif logic["v6_rule"] == "toggle": logic["v6_seq"] = [1, 2, 1, 2, 1, 2] if random.random() > 0.5 else [3, 4, 3, 4, 3, 4]
            else: logic["v6_seq"] = [1, 2, 3, 1, 2, 3]
        else:
            logic["v6_rule"] = "static"
            logic["v6_seq"] = [random.randint(1, 4)]

        if 7 in active_vars:
            logic["v7_rule"] = random.choice(["grow", "shrink", "toggle", "cycle3"])
            if logic["v7_rule"] == "grow": logic["v7_seq"] = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
            elif logic["v7_rule"] == "shrink": logic["v7_seq"] = [1.5, 1.25, 1.0, 0.75, 0.5, 0.25]
            elif logic["v7_rule"] == "toggle": logic["v7_seq"] = [0.6, 1.2, 0.6, 1.2, 0.6, 1.2]
            else: logic["v7_seq"] = [0.6, 0.9, 1.2, 0.6, 0.9, 1.2]
        else:
            logic["v7_rule"] = "static"
            logic["v7_seq"] = [1.0]

        return logic

    # ═══════════════════════════════════════════════════════════════════════════
    # SHAPE & RENDER HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _shape_coords(self, shape, cx, cy, r):
        pts = []
        if shape == "circle": return [cx-r, cy-r, cx+r, cy+r]
        elif shape == "square":
            adj = r * 0.85
            pts = [(cx-adj,cy-adj),(cx+adj,cy-adj),(cx+adj,cy+adj),(cx-adj,cy+adj)]
        elif shape == "triangle":
            for i in range(3):
                a = math.radians(-90 + i*120)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        elif shape == "cross_shape":
            w = r*0.35
            pts = [(cx-w,cy-r),(cx+w,cy-r),(cx+w,cy-w),(cx+r,cy-w),
                   (cx+r,cy+w),(cx+w,cy+w),(cx+w,cy+r),(cx-w,cy+r),
                   (cx-w,cy+w),(cx-r,cy+w),(cx-r,cy-w),(cx-w,cy-w)]
        elif shape == "hexagon":
            for i in range(6):
                a = math.radians(-90 + i*60)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        return pts

    def _draw_shape(self, canvas, shape, fill, cx, cy, r, ow=2.5):
        draw = ImageDraw.Draw(canvas)
        weight = int(ow * self.sf)
        coords = self._shape_coords(shape, cx, cy, r)
        if fill == "solid":
            if shape == "circle": draw.ellipse(coords, fill="black", outline="black", width=weight)
            else: draw.polygon(coords, fill="black", outline="black")
        elif fill == "hollow":
            if shape == "circle": draw.ellipse(coords, fill="white", outline="black", width=weight)
            else:
                draw.polygon(coords, fill="white", outline="black")
                closed = coords + [coords[0], coords[1]]
                draw.line(closed, fill="black", width=weight, joint="curve")

    def _draw_question_mark(self, canvas, cx, cy):
        draw = ImageDraw.Draw(canvas)
        txt  = "?"
        bbox = draw.textbbox((0,0), txt, font=self.font_hd)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((cx-tw//2, cy-th//2), txt, font=self.font_hd, fill="black")

    # ═══════════════════════════════════════════════════════════════════════════
    # FRAME BUILDER
    # ═══════════════════════════════════════════════════════════════════════════
    def _gen_sequence(self, difficulty):
        logic = self._roll_logic(difficulty)
        
        def _get_frame(fi):
            v1_style = logic["v1_seq"][fi % len(logic["v1_seq"])] if logic["v1_rule"] != "static" else logic["v1_seq"][0]
            v2_weight = logic["v2_seq"][fi % len(logic["v2_seq"])] if logic["v2_rule"] != "static" else logic["v2_seq"][0]
            v3_shape = logic["v3_seq"][fi % len(logic["v3_seq"])] if logic["v3_rule"] != "static" else logic["v3_seq"][0]
            v4_pos = logic["v4_seq"][fi % len(logic["v4_seq"])] if logic["v4_rule"] != "static" else logic["v4_seq"][0]
            v5_shade = logic["v5_seq"][fi % len(logic["v5_seq"])] if logic["v5_rule"] != "static" else logic["v5_seq"][0]
            v6_count = logic["v6_seq"][fi % len(logic["v6_seq"])] if logic["v6_rule"] != "static" else logic["v6_seq"][0]
            v7_size = logic["v7_seq"][fi % len(logic["v7_seq"])] if logic["v7_rule"] != "static" else logic["v7_seq"][0]
            
            return {
                "style": v1_style, "weight": v2_weight, "shape": v3_shape,
                "pos": v4_pos, "shade": v5_shade, "count": v6_count, "size": v7_size
            }

        frames = [_get_frame(fi) for fi in range(5)]
        
        # Decide output format here so missing_idx can be set accordingly
        output_format = random.choice(["strip", "animated"])
        if output_format == "animated" or random.random() < 0.5:
            missing_idx = 4
        else:
            missing_idx = random.randint(0, 3)
            
        answer_state = frames[missing_idx]

        d1 = _get_frame(missing_idx - 1)
        d2 = _get_frame(missing_idx + 2)
        
        d3 = copy.deepcopy(answer_state)
        d3["shade"] = "solid" if answer_state["shade"] == "hollow" else "hollow"
        
        d4 = copy.deepcopy(answer_state)
        d4["pos"] = (answer_state["pos"] + 2) % 4

        def _emergency(existing_keys):
            for p in range(4):
                for s in self.simple_shapes:
                    cand = copy.deepcopy(answer_state)
                    cand["pos"] = p
                    cand["shape"] = s
                    if _state_key(cand) not in existing_keys: return cand
            return _get_frame(missing_idx + 3)

        distractors = _dedup_options(answer_state, [d1, d2, d3, d4], _emergency)

        return {
            "subtype": "frame_border", "frames": frames, "answer": answer_state,
            "missing_idx": missing_idx, "distractors": distractors, 
            "difficulty_score": difficulty, "rule_axes": f"Active: {logic['active']}",
            "output_format": output_format,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET RENDERER
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_fb_frame(self, canvas, state):
        sf=self.sf; fw,fh=canvas.width,canvas.height; draw=ImageDraw.Draw(canvas)
        pad=int(15*sf); style=state["style"]
        
        weight_map = {"thin": 1.5, "medium": 3, "thick": 5.5}
        weight = weight_map.get(state["weight"], 3) * sf

        if style in ["dashed", "dotted"]:
            dl, gl = (int(12*sf), int(8*sf)) if style == "dashed" else (int(3*sf), int(6*sf))
            for ey in [pad,fh-pad]:
                x,t=pad,True
                while x<fw-pad:
                    xe=min(x+dl,fw-pad)
                    if t: draw.line([(x,ey),(xe,ey)],fill="black",width=int(weight))
                    x+=dl if t else gl; t=not t
            for ex in [pad,fw-pad]:
                y,t=pad,True
                while y<fh-pad:
                    ye=min(y+dl,fh-pad)
                    if t: draw.line([(ex,y),(ex,ye)],fill="black",width=int(weight))
                    y+=dl if t else gl; t=not t
        elif style == "double":
            w_inner = max(1, int(weight * 0.4))
            draw.rectangle([pad,pad,fw-pad,fh-pad],outline="black",width=w_inner)
            gap = int(6 * sf) + w_inner
            draw.rectangle([pad+gap,pad+gap,fw-pad-gap,fh-pad-gap],outline="black",width=w_inner)
        else: 
            draw.rectangle([pad,pad,fw-pad,fh-pad],outline="black",width=int(weight))

        corner_coords = [
            (pad+int(38*sf), pad+int(38*sf)),         
            (fw-pad-int(38*sf), pad+int(38*sf)),      
            (fw-pad-int(38*sf), fh-pad-int(38*sf)),   
            (pad+int(38*sf), fh-pad-int(38*sf)),      
        ]
        
        base_cx, base_cy = corner_coords[state["pos"]]
        
        count = state["count"]
        size_mod = state["size"]
        base_r = int(11 * sf * size_mod)
        gap = int(24 * sf)

        if count == 1:
            offsets = [(0, 0)]
        elif count == 2:
            offsets = [(-gap//2, 0), (gap//2, 0)]
        elif count == 3:
            offsets = [(0, -gap//2), (-gap//2, gap//2), (gap//2, gap//2)]
        else:
            offsets = [(-gap//2, -gap//2), (gap//2, -gap//2), (-gap//2, gap//2), (gap//2, gap//2)]

        for dx, dy in offsets:
            self._draw_shape(canvas, state["shape"], state["shade"], base_cx + dx, base_cy + dy, base_r)

    # ═══════════════════════════════════════════════════════════════════════════
    # STRIP / GIF / SAVING 
    # ═══════════════════════════════════════════════════════════════════════════
    def render_frame(self, state, show_question_mark=False):
        canvas = Image.new("RGB", (self.frame_hd, self.frame_hd), "white")
        if show_question_mark:
            self._draw_question_mark(canvas, canvas.width//2, canvas.height//2)
            return canvas
        self._render_fb_frame(canvas, state)
        return canvas

    def _render_sequence_strip(self, frames, missing_idx, show_answer=False):
        n_frames  = len(frames)
        fw, fh = self.frame_hd, self.frame_hd
        sep = self.frame_sep
        pad = self.strip_pad

        strip_w = pad*2 + n_frames*fw + (n_frames-1)*sep
        strip_h = pad*2 + fh 
        strip   = Image.new("RGB", (strip_w, strip_h), "white")

        for i in range(n_frames):
            x0 = pad + i*(fw + sep)
            y0 = pad
            
            if i == missing_idx and not show_answer:
                img = self.render_frame(None, show_question_mark=True)
            else:
                img = self.render_frame(frames[i])
                
            strip.paste(img, (x0, y0))
            
        return strip

    def _render_animated_gif(self, frames, missing_idx):
        sf = self.sf
        fw, fh = self.frame_hd, self.frame_hd

        def _gif_frame(state, is_q=False):
            c = Image.new("RGB", (fw, fh), "white")
            content = (Image.new("RGB", (fw, fh), "white") if is_q else self.render_frame(state))
            if is_q: self._draw_question_mark(content, fw//2, fh//2)
            c.paste(content, (0, 0))
            sm = c.resize((fw//sf, fh//sf), Image.Resampling.LANCZOS)
            return sm.convert("P", palette=Image.Palette.ADAPTIVE, colors=32)

        gif_frames = []
        for i, f in enumerate(frames):
            if i == missing_idx:
                gif_frames.append(_gif_frame(None, is_q=True))
            else:
                gif_frames.append(_gif_frame(f))
                
        durations  = [ANIM_FRAME_MS] * len(frames)
        durations[-1] = ANIM_PAUSE_MS
        return gif_frames, durations

    def _render_answer_strip(self, options):
        fw, fh = self.frame_hd, self.frame_hd
        gap = int(16 * self.sf); pad_x = int(24 * self.sf); pad_y = int(20 * self.sf)
        lbl_h = int(64 * self.sf); lbl_gap = int(12 * self.sf); n = len(options)

        strip_w = 2*pad_x + n*fw + (n-1)*gap
        strip_h = pad_y + fh + lbl_gap + lbl_h
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE")):
            x0 = pad_x + i*(fw + gap); y0 = pad_y; cx = x0 + fw//2
            
            strip.paste(self.render_frame(opt), (x0, y0))
            
            bbox = draw.textbbox((0,0), lbl, font=self.font_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, y0+fh+lbl_gap), lbl, font=self.font_hd, fill="black")
        return strip

    def save_item(self, item_data, item_id, out_root):
        sf=self.sf; subtype=item_data["subtype"]
        folder_name=f"Seq_{subtype[:12]}_{item_id:03d}_Diff{item_data['difficulty_score']}"
        folder_path=os.path.join(out_root,folder_name)
        os.makedirs(folder_path,exist_ok=True)
        base=folder_name

        frames = item_data["frames"]
        answer = item_data["answer"]
        missing_idx = item_data["missing_idx"]
        
        # Retrieve format determined during generation
        output_format = item_data.get("output_format", "strip")

        # Always save Choices File (Answers are required for both types)
        distractors = list(item_data.get("distractors",[]))
        while len(distractors) < 4: distractors.append(copy.deepcopy(answer))
        distractors = distractors[:4]
        correct_pos = random.randint(0,4)
        correct_letter = "ABCDE"[correct_pos]
        options = list(distractors); options.insert(correct_pos, answer)

        c_path = os.path.join(folder_path, f"{base}_choices.png")
        c_hd = self._render_answer_strip(options)
        c_hd.resize((c_hd.width//sf, c_hd.height//sf), Image.Resampling.LANCZOS).save(c_path)

        # Variables to return for manifest tracking
        q_path = ""
        s_path = ""
        p_path = ""

        if output_format == "strip":
            # 1. Save Comic Strip WITH Question Mark
            q_path = os.path.join(folder_path, f"{base}_question_strip.png")
            q_hd = self._render_sequence_strip(frames, missing_idx, show_answer=False)
            q_hd.resize((q_hd.width//sf, q_hd.height//sf), Image.Resampling.LANCZOS).save(q_path)

            # 2. Save Solved Comic Strip
            s_path = os.path.join(folder_path, f"{base}_answer_strip.png")
            s_hd = self._render_sequence_strip(frames, missing_idx, show_answer=True)
            s_hd.resize((s_hd.width//sf, s_hd.height//sf), Image.Resampling.LANCZOS).save(s_path)
            
        else: # output_format == "animated"
            # 3. Save Animated GIF
            p_path = os.path.join(folder_path, f"{base}_animated.gif")
            gf, dur = self._render_animated_gif(frames, missing_idx)
            gf[0].save(p_path, save_all=True, append_images=gf[1:], duration=dur, loop=0, optimize=False)

        # Return everything to map cleanly to the manifest
        return folder_name, q_path, p_path, c_path, correct_letter, output_format

    # ═══════════════════════════════════════════════════════════════════════════
    # BATCH GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_batch(self, total_items):
        print(f"Generating balanced batch of {total_items} logic items...")
        
        jobs = []
        for i in range(total_items):
            diff = (i % 3) + 1 
            jobs.append(self._gen_sequence(diff))
            
        jobs.sort(key=lambda x: x["difficulty_score"])
        return jobs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    gen=NVRSequenceGenerator()
    print(f"\nNVR Sequence Item Generator  —  Unified Core Logic")
    print("="*56)
    
    raw_n=input("How many items to generate? [default: 60]: ").strip()
    n_items=int(raw_n) if raw_n.isdigit() and int(raw_n)>0 else 60
    
    jobs = gen.generate_batch(n_items)
    print(f"\nSaving {n_items} items to → {OUTPUT_FOLDER}\n")

    manifest_rows=[]
    for item_id, item_data in enumerate(jobs, 1):
        diff = item_data["difficulty_score"]
        print(f"  [{item_id:3d}/{n_items}] Diff Level: {diff} | Variables: {item_data['rule_axes']} ...", end=" ",flush=True)
        try:
            folder, sp, pp, cp, cl, os_ = gen.save_item(item_data, item_id, OUTPUT_FOLDER)
            manifest_rows.append({
                "Item_ID": item_id,
                "Folder": folder,
                "Output_Style": os_,
                "Difficulty_Level": diff,
                "Variables_Active": item_data["rule_axes"],
                "Correct_Position": cl,
                "Static_PNG": os.path.basename(sp) if sp else "",
                "Animated_GIF": os.path.basename(pp) if pp else "",
                "Choices_File": os.path.basename(cp),
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
    print(f"Complete. {len(manifest_rows)} meticulously logical item(s) saved.")
    print(f"Output  : {OUTPUT_FOLDER}")
    print(f"Manifest: {manifest_path}")