"""
NVR_sequences_beads_on_wire.py
=========================
Non-Verbal Reasoning — Sequences Item Generator
Standalone Module: Beads on Wire (Wrap/Bounce/NextWire)
"""

import random, os, math, csv, copy
from PIL import Image, ImageDraw, ImageFont

# ── Target Configuration ───────────────────────────────────────────────────────
TARGET_SUBTYPE = "beads_on_wire"

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, f"NVR_Sequences_{TARGET_SUBTYPE.title()}")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Animation / layout constants ───────────────────────────────────────────────
ANIM_FRAME_MS     = 1000
ANIM_PAUSE_MS     = 2000
ANSWER_OPTIONS    = 5

FRAMED_SUBTYPES = {"fill_pattern", "multi_element_composition", "multi_element_independent"}
WIDE_SUBTYPES   = {"beads_on_wire"}

# ── Safeguard constants ────────────────────────────────────────────────────────
MAX_DEDUP_ATTEMPTS  = 20
MAX_GEN_RETRIES     = 10

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
# Scores aggregate logic (0-5) + boundary (0-2) + beads (1-3) + wires (1-3) + missing (0-2)
TIERS = {
    "easy":      {"score_range": (2, 4),   "age_range": "6-8",   "complexity": 1},
    "easy_med":  {"score_range": (5, 6),   "age_range": "8-10",  "complexity": 2},
    "medium":    {"score_range": (7, 8),   "age_range": "10-12", "complexity": 3},
    "hard":      {"score_range": (9, 10),  "age_range": "12-14", "complexity": 4},
    "very_hard": {"score_range": (11, 12), "age_range": "14-16", "complexity": 5},
    "extreme":   {"score_range": (13, 20), "age_range": "16+",   "complexity": 6},
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

def _safe_gen(gen_fn, tier):
    for _ in range(MAX_GEN_RETRIES):
        try:
            return gen_fn(tier)
        except Exception:
            continue
    return gen_fn("easy") # Fallback to easy if it repeatedly fails

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
        self.strip_pad    = int(10 * self.sf)  
        self.bead_fw_hd   = 300 * self.sf
        self.bead_fh_hd   = 300 * self.sf       

        self.font_hd   = None
        self.qlabel_hd = None
        self.font_q_mark_hd = None
        self._load_fonts()

    def _load_fonts(self):
        self.font_ans_hd = None 
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
                            self.font_hd     = ImageFont.truetype(fp, 44*self.sf)
                            self.qlabel_hd   = ImageFont.truetype(fp, 28*self.sf)
                            self.font_ans_hd = ImageFont.truetype(fp, 72*self.sf) 
                            self.font_q_mark_hd = ImageFont.truetype(fp, 80*self.sf)
                            found = True; break
                        except Exception: continue
                if found: break
            except Exception: continue
        if not found:
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd     = ImageFont.truetype(fp, 44*self.sf)
                        self.qlabel_hd   = ImageFont.truetype(fp, 28*self.sf)
                        self.font_ans_hd = ImageFont.truetype(fp, 72*self.sf) 
                        
                        found = True; break
                    except Exception: continue
        if not found:
            self.font_hd = self.qlabel_hd = self.font_ans_hd = ImageFont.load_default() 

    @staticmethod
    def _use_panel_border(subtype):
        return subtype in FRAMED_SUBTYPES

    def _draw_question_mark(self, canvas, cx, cy, text="?"):
        draw = ImageDraw.Draw(canvas)
        font = self.font_q_mark_hd if self.font_q_mark_hd else self.font_hd
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((cx-tw//2, cy-th//2), text, font=font, fill="black")

    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET SUBTYPE GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════
    def _get_step_sequence(self, logic_type, max_frames=10):
        if logic_type == 0:   return [1] * max_frames
        elif logic_type == 1: return [2] * max_frames
        elif logic_type == 2: return [1 if i%2==0 else 2 for i in range(max_frames)]
        elif logic_type == 3: return [i+1 for i in range(max_frames)]
        elif logic_type == 4: return [max(0, 3-i) for i in range(max_frames)]
        elif logic_type == 5: 
            fib = [1, 1]
            for _ in range(max_frames-2): fib.append(fib[-1] + fib[-2])
            return fib
        return [1] * max_frames

    def _gen_beads_on_wire(self, tier):
        cfg = TIERS[tier]
        target_range = cfg["score_range"]
        
        n_positions = 8
        total_frames = 5  
        
        retry_count = 0
        while retry_count < 500: 
            retry_count += 1
            
            step_logic = random.randint(0, 5)
            boundary = random.randint(0, 2)
            
            n_beads = random.choices([1, 2, 3], weights=[45, 45, 10], k=1)[0]
            
            n_wires = random.randint(1, 3)
            q_loc_idx = random.randint(0, 2) 
            rule_app = random.randint(0, 1)  
            
            score = step_logic + boundary + n_beads + n_wires + q_loc_idx
            if not (target_range[0] <= score <= target_range[1]):
                continue

            boundary_type = ["wrap", "bounce", "next_wire"][boundary]
            
            q_location = ["end", "middle", "start"][q_loc_idx]
            if q_location == "start": missing_idx_static = 0
            elif q_location == "middle": missing_idx_static = total_frames // 2
            else: missing_idx_static = total_frames - 1
            
            missing_idx_anim = total_frames - 1

            bead_cfgs = []
            available_colors = ["white", "black", "grey"]
            random.shuffle(available_colors)

            for i in range(n_beads):
                logic = step_logic if rule_app == 1 else random.randint(0, max(0, step_logic))
                steps = self._get_step_sequence(logic, total_frames)
                color = available_colors[i] 
                dir_mod = random.choice([1, -1])
                start_wire = random.randint(0, n_wires - 1)
                start_pos = random.randint(0, n_positions - 1)
                
                bead_cfgs.append({
                    "color": color, "steps": steps, "dir": dir_mod,
                    "start_w": start_wire, "start_p": start_pos
                })

            sequence = []
            interaction_frames = set() 
            used_wires = set() 
            
            for fi in range(total_frames):
                state_wires = [{"n_positions": n_positions, "beads": []} for _ in range(n_wires)]
                
                for b in bead_cfgs:
                    cw, cp, cdir = b["start_w"], b["start_p"], b["dir"]
                    
                    for step_idx in range(fi):
                        step_val = b["steps"][step_idx] * cdir
                        new_pos = cp + step_val
                        
                        hit_boundary = False
                        if new_pos < 0 or new_pos >= n_positions:
                            hit_boundary = True

                        if boundary_type == "wrap":
                            if hit_boundary:
                                interaction_frames.add(step_idx + 1)
                            cp = new_pos % n_positions
                            
                        elif boundary_type == "bounce":
                            if hit_boundary:
                                cdir = -cdir
                                new_pos = cp + (b["steps"][step_idx] * cdir)
                                interaction_frames.add(step_idx + 1)
                            cp = max(0, min(n_positions - 1, new_pos))
                            
                        elif boundary_type == "next_wire":
                            if hit_boundary:
                                interaction_frames.add(step_idx + 1)
                                if new_pos >= n_positions:
                                    cw = (cw + 1) % n_wires
                                elif new_pos < 0:
                                    cw = (cw - 1) % n_wires
                                cp = new_pos % n_positions
                            else:
                                cp = new_pos

                    state_wires[cw]["beads"].append({"pos": cp, "color": b["color"]})
                    used_wires.add(cw) 

                sequence.append({"wires": state_wires})

            if len(used_wires) < n_wires:
                continue 

            if boundary_type in ["wrap", "bounce", "next_wire"]:
                vis_static = [f for f in interaction_frames if f != missing_idx_static and (f-1) != missing_idx_static]
                vis_anim   = [f for f in interaction_frames if f != missing_idx_anim and (f-1) != missing_idx_anim]
                
                if not vis_static or not vis_anim:
                    continue 
            
            answer_state_static = sequence[missing_idx_static]
            answer_state_anim   = sequence[missing_idx_anim]
            break
        else:
            return self._gen_beads_on_wire("easy")

        def _mutate(state, offset):
            s = copy.deepcopy(state)
            if s["wires"] and s["wires"][0]["beads"]:
                s["wires"][0]["beads"][0]["pos"] = (s["wires"][0]["beads"][0]["pos"] + offset) % n_positions
            return s

        d1_s = sequence[min(missing_idx_static + 1, total_frames - 1)] if missing_idx_static < total_frames - 1 else sequence[missing_idx_static - 1]
        distractors_static = _dedup_options(answer_state_static, [d1_s, _mutate(answer_state_static, 1), _mutate(answer_state_static, -1), _mutate(answer_state_static, 2)], lambda ex: _mutate(answer_state_static, random.randint(3,7)))

        d1_a = sequence[missing_idx_anim - 1]
        distractors_anim = _dedup_options(answer_state_anim, [d1_a, _mutate(answer_state_anim, 1), _mutate(answer_state_anim, -1), _mutate(answer_state_anim, 2)], lambda ex: _mutate(answer_state_anim, random.randint(3,7)))

        step_desc = ["constant_1", "constant_2", "alternating", "accelerating", "decelerating", "fibonacci"][step_logic]
        axes = f"w={n_wires}|b={n_beads}|bnd={boundary_type}|step={step_desc}|q={q_location}"

        return {
            "subtype": "beads_on_wire", 
            "sequence": sequence, 
            "answer_static": answer_state_static,
            "distractors_static": distractors_static, 
            "missing_idx_static": missing_idx_static,
            "answer_anim": answer_state_anim,
            "distractors_anim": distractors_anim,
            "missing_idx_anim": missing_idx_anim,
            "tier": tier, 
            "score": score, 
            "age_range": cfg["age_range"], 
            "rule_axes": axes
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET RENDERER
    # ═══════════════════════════════════════════════════════════════════════════
    def render_frame(self, state, show_question_mark=False, q_text="?"):
        canvas = Image.new("RGB", (self.bead_fw_hd, self.bead_fh_hd), "white")
        sf=self.sf; fw,fh=canvas.width,canvas.height
        draw=ImageDraw.Draw(canvas)
        
        bw = int(2 * sf)
        draw.rectangle([bw//2, bw//2, fw - bw//2, fh - bw//2], outline="black", width=bw)
        
        if show_question_mark or state is None:
            self._draw_question_mark(canvas, fw//2, fh//2, text=q_text)
            return canvas
            
        n_wires=len(state["wires"]); wire_h=fh//(n_wires+1)
        bead_r=int(10*sf); end_pad=int(16*sf)
        tick_h=int(4*sf)
        
        for wi,wire in enumerate(state["wires"]):
            wy=wire_h*(wi+1); n_pos=wire["n_positions"]
            step=(fw-2*end_pad)/(n_pos-1)
            
            draw.line([(end_pad,wy),(fw-end_pad,wy)],fill="black",width=int(2*sf))
            
            for i in range(n_pos):
                px = int(end_pad + i * step)
                draw.line([(px, wy - tick_h), (px, wy + tick_h)], fill="black", width=int(2*sf))
            
            for ex in [end_pad,fw-end_pad]:
                draw.line([(ex,wy-bead_r),(ex,wy+bead_r)],fill="black",width=int(2.5*sf))
                
            for bead in wire["beads"]:
                bx=int(end_pad+bead["pos"]*step)
                c_fill = "black" if bead["color"] == "black" else "white" if bead["color"] == "white" else "grey"
                draw.ellipse([bx-bead_r,wy-bead_r,bx+bead_r,wy+bead_r],
                             fill=c_fill, outline="black", width=int(1.5*sf))
        return canvas

    # ═══════════════════════════════════════════════════════════════════════════
    # STRIP / GIF / SAVING 
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_sequence_strip(self, sequence, missing_idx, show_answer):
        n_frames  = len(sequence)
        fw, fh = self.bead_fw_hd, self.bead_fh_hd
        
        pad = int((100 / 3) * self.sf) 
        sep = int(-2 * self.sf) 
        
        strip_w = int(pad*2 + n_frames*fw + (n_frames-1)*sep)
        strip_h = int(pad*2 + fh) 
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        
        for i in range(n_frames):
            x0 = int(pad + i*(fw + sep))
            y0 = pad
            
            if i == missing_idx and not show_answer:
                img = self.render_frame(None, show_question_mark=True) 
            else:
                img = self.render_frame(sequence[i])
                
            strip.paste(img, (x0, y0))
            
        return strip

    def _render_animated_gif(self, sequence, missing_idx):
        sf = self.sf
        fw, fh = self.bead_fw_hd, self.bead_fh_hd
        
        side_padding = int(500 * sf) 
        bot_padding = int(25 * sf) 

        cw = fw + (2 * side_padding)
        ch = fh + bot_padding
        
        target_w = cw // sf
        target_h = ch // sf

        def _gif_frame(state, is_q=False):
            c = Image.new("RGB", (cw, ch), "white")
            
            if is_q:
                content = Image.new("RGB", (fw, fh), "white")
                self._draw_question_mark(content, fw // 2, fh // 2)
            else:
                content = self.render_frame(state)
            
            c.paste(content, (side_padding, 0)) 
            
            sm = c.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return sm.convert("P", palette=Image.Palette.ADAPTIVE, colors=32)

        gif_frames = []
        durations = []
        for i in range(len(sequence)):
            if i == missing_idx:
                gif_frames.append(_gif_frame(None, is_q=True))
                durations.append(ANIM_PAUSE_MS)
            else:
                gif_frames.append(_gif_frame(sequence[i]))
                durations.append(ANIM_FRAME_MS)
                
        return gif_frames, durations

    def _render_answer_strip(self, options):
        fw, fh = self.bead_fw_hd, self.bead_fh_hd
        
        pad_x = int(40 * self.sf)    
        gap = int(27 * self.sf)      
        pad_y = int(33 * self.sf) 
        
        lbl_gap = int(45 * self.sf)  
        lbl_h = int(107 * self.sf) 
        
        n = len(options)

        strip_w = int(2*pad_x + n*fw + (n-1)*gap)
        strip_h = int(pad_y + fh + lbl_gap + lbl_h)
        strip   = Image.new("RGB", (strip_w, strip_h), "white")
        draw    = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE")):
            x0 = int(pad_x + i*(fw + gap))
            y0 = pad_y
            cx = x0 + fw//2
            
            strip.paste(self.render_frame(opt), (x0, y0))
            
            bbox = draw.textbbox((0,0), lbl, font=self.font_ans_hd)
            draw.text((cx - (bbox[2]-bbox[0])//2, y0+fh+lbl_gap), lbl, font=self.font_ans_hd, fill="black")
            
        return strip

    def generate_item(self, tier):
        return _safe_gen(self._gen_beads_on_wire, tier)

    def save_item(self, item_data, item_id, out_root):
        sf=self.sf; subtype=item_data["subtype"]; tier=item_data["tier"]
        tier_label=tier.replace("_","-").title()
        
        folder_name=f"Seq_{subtype[:12]}_{tier_label}_{item_id:03d}"
        folder_path=os.path.join(out_root,folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        base=folder_name
        sequence = item_data["sequence"]
        
        output_format = random.choice(["strip", "animated"])

        q_path = ""
        s_path = ""
        p_path = ""
        c_path = ""
        clet = ""
        missing_idx = -1

        if output_format == "strip":
            missing_idx = item_data["missing_idx_static"]
            ans = item_data["answer_static"]
            dist = list(item_data.get("distractors_static", []))
            
            q_path = os.path.join(folder_path, f"{base}_question_strip.png")
            s_path = os.path.join(folder_path, f"{base}_answer_strip.png")
            c_path = os.path.join(folder_path, f"{base}_choices.png")
            
            q_hd = self._render_sequence_strip(sequence, missing_idx, show_answer=False)
            q_hd.resize((q_hd.width//sf, q_hd.height//sf), Image.Resampling.LANCZOS).save(q_path)
            
            a_hd = self._render_sequence_strip(sequence, missing_idx, show_answer=True)
            a_hd.resize((a_hd.width//sf, a_hd.height//sf), Image.Resampling.LANCZOS).save(s_path)
            
        else: # output_format == "animated"
            missing_idx = item_data["missing_idx_anim"]
            ans = item_data["answer_anim"]
            dist = list(item_data.get("distractors_anim", []))
            
            p_path = os.path.join(folder_path, f"{base}_animated.gif")
            c_path = os.path.join(folder_path, f"{base}_choices.png")
            
            gf, dur = self._render_animated_gif(sequence, missing_idx)
            gf[0].save(p_path, save_all=True, append_images=gf[1:], duration=dur, loop=0, optimize=False)
            
        # Common choices rendering
        while len(dist) < 4: dist.append(copy.deepcopy(ans))
        dist = dist[:4]
        cpos = random.randint(0, 4)
        clet = "ABCDE"[cpos]
        opts = list(dist); opts.insert(cpos, ans)

        c_hd = self._render_answer_strip(opts)
        c_hd.resize((c_hd.width//sf, c_hd.height//sf), Image.Resampling.LANCZOS).save(c_path)

        return folder_name, q_path, p_path, c_path, clet, missing_idx, output_format

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
        print(f"  {i} = {t:12s}  target score {cfg['score_range']}  target age {cfg['age_range']}")
    
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
            print(f"  {t:12s}: {tier_counts[t]:3d}  (score {cfg['score_range']}  age {cfg['age_range']})")
    print()

    manifest_rows=[]
    for item_id,(_,tier) in enumerate(jobs,1):
        print(f"  [{item_id:3d}/{n_items}]  {TARGET_SUBTYPE:30s} | {tier} ...", end=" ",flush=True)
        try:
            item_data=gen.generate_item(tier)
            folder, sp, pp, cp, cl, miss_idx, os_ = gen.save_item(item_data, item_id, OUTPUT_FOLDER)
            manifest_rows.append({
                "Item_ID":item_id, "Folder":folder, "Subtype":TARGET_SUBTYPE,
                "Output_Style":os_,
                "Difficulty_Tier":tier, "Aggregated_Score":item_data["score"], 
                "Age_Range":item_data["age_range"], "Rule_Axes":item_data["rule_axes"], 
                "Missing_Index":miss_idx,
                "Correct_Position":cl,
                "Static_PNG":os.path.basename(sp) if sp else "",
                "Animated_GIF":os.path.basename(pp) if pp else "",
                "Choices_File":os.path.basename(cp) if cp else "",
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
    print(f"Complete. {len(manifest_rows)} item(s) saved.")
    print(f"Output  : {OUTPUT_FOLDER}")
    print(f"Manifest: {manifest_path}")
