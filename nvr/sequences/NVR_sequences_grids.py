"""
NVR_grid_sequences.py
=====================
Non-Verbal Reasoning — Grid Sequence Generator

Generates grid-based movement sequence puzzles where filled cells move
through positions on a grid following specific rules. The student sees
a sequence of the pattern and must predict the missing position.

Formats:
  • STATIC: Randomly chosen (50/50) or forced if 3 elements with different rules.
            Fixed to exactly 5 total frames (4 clue frames + 1 question/answer frame).
  • ANIMATED: Randomly chosen (50/50). Frame count dynamically scales to rule complexity.

Movement types (from rules matrix):
  EASY         Linear row-by-row  |  Linear column-by-column
  EASY-MEDIUM  Clockwise perimeter 1-step  |  Anti-clockwise perimeter 1-step
  MEDIUM       Clockwise perimeter 2-step (skip)  |  Clockwise 3-step (corners)
  HARD         Diagonal bounce  |  L-shaped (knight)
  VERY HARD    Spiral inward  |  Alternating direction

Number of elements:  1–3 boxes with independent or linked rules
Step sizes:          Linear 1/2/3, Alternating (two), Increasing (1,2,3)
Grid sizes:          3×3, 4×4, 5×5

Difficulty is auto-calculated from a weighted matrix across all variables.
"""

import random, os, math, csv, copy
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_sequences_grids")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Animation constants ───────────────────────────────────────────────────────
ANIM_FRAME_MS = 700
ANIM_PAUSE_MS = 1800
ANSWER_OPTIONS = 5

# ── Font search paths ─────────────────────────────────────────────────────────
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
# DIFFICULTY MATRIX
# ═══════════════════════════════════════════════════════════════════════════════
MOVEMENT_WEIGHTS = {
    "linear_row":        1.0,
    "linear_col":        1.0,
    "clockwise_1":       2.0,
    "anticlockwise_1":   2.5,
    "clockwise_2":       3.0,
    "clockwise_3":       3.5,
    "diagonal_bounce":   4.5,
    "knight":            5.0,
    "spiral_inward":     5.5,
    "alternating_dir":   5.0,
}
ELEMENT_WEIGHTS = {
    1: 0.0,       
    2: 1.5,       
    3: 3.0,       
}
RELATIONSHIP_WEIGHTS = {
    "same":          0.0,  
    "opposite":      1.0,  
    "different":     1.5,  
    "converging":    2.0,  
}
STEP_WEIGHTS = {
    "linear_1":      0.0,
    "linear_2":      0.5,
    "linear_3":      1.0,
    "alternating":   1.5,  
    "increasing":    2.0,  
}
GRID_WEIGHTS = {
    3: 0.0,
    4: 0.5,
    5: 1.0,
}

TIER_BOUNDARIES = [
    (2.5,  "easy",      (-2.5, -1.5), "6-8"),
    (4.5,  "easy_med",  (-1.5, -0.5), "8-10"),
    (6.5,  "medium",    (-0.5,  0.5), "10-12"),
    (8.5,  "hard",      ( 0.5,  1.5), "12-14"),
    (10.5, "very_hard", ( 1.5,  2.5), "14-16"),
    (99.0, "extreme",   ( 2.5,  4.0), "16+"),
]

def compute_difficulty(movement, n_elements, relationship, step_type, grid_n):
    score = (MOVEMENT_WEIGHTS.get(movement, 3.0)
             + ELEMENT_WEIGHTS.get(n_elements, 1.5)
             + RELATIONSHIP_WEIGHTS.get(relationship, 0.0)
             + STEP_WEIGHTS.get(step_type, 0.5)
             + GRID_WEIGHTS.get(grid_n, 0.5))
    for threshold, tier, b_range, age_range in TIER_BOUNDARIES:
        if score < threshold:
            b_est = round(random.uniform(*b_range), 2)
            return score, tier, b_est, age_range
    b_est = round(random.uniform(2.5, 4.0), 2)
    return score, "extreme", b_est, "16+"

# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC FRAME COUNT
# ═══════════════════════════════════════════════════════════════════════════════
def compute_frames_needed(n_elements, relationship, step_type):
    base = 4
    step_add = {
        "linear_1": 0,
        "linear_2": 1,      
        "linear_3": 1,
        "alternating": 3,   
        "increasing": 2,    
    }
    base += step_add.get(step_type, 0)

    if n_elements >= 3:
        base += 2
    elif n_elements == 2:
        rel_add = {
            "same": 0,
            "opposite": 1,
            "different": 2,
            "converging": 2,
        }
        base += rel_add.get(relationship, 1)

    return base

# ═══════════════════════════════════════════════════════════════════════════════
# MOVEMENT ENGINES
# ═══════════════════════════════════════════════════════════════════════════════
def perimeter_cells(n):
    cells = []
    for c in range(n):            cells.append((0, c))          
    for r in range(1, n):         cells.append((r, n - 1))      
    for c in range(n - 2, -1, -1): cells.append((n - 1, c))     
    for r in range(n - 2, 0, -1): cells.append((r, 0))          
    return cells

def spiral_cells(n):
    cells = []
    top, bottom, left, right = 0, n - 1, 0, n - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):    cells.append((top, c))
        top += 1
        for r in range(top, bottom + 1):    cells.append((r, right))
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1): cells.append((bottom, c))
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):  cells.append((r, left))
            left += 1
    return cells

def all_cells_row_major(n):
    return [(r, c) for r in range(n) for c in range(n)]

def all_cells_col_major(n):
    return [(r, c) for c in range(n) for r in range(n)]

def advance_bounce(r, c, dr, dc, n):
    r2, c2 = r + dr, c + dc
    if r2 < 0 or r2 >= n:
        dr = -dr
        r2 = r + dr
    if c2 < 0 or c2 >= n:
        dc = -dc
        c2 = c + dc
    return r2, c2, dr, dc

def advance_knight(r, c, n, visited=None):
    moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
             (1, -2), (1, 2), (2, -1), (2, 1)]
    valid = [(r + dr, c + dc) for dr, dc in moves
             if 0 <= r + dr < n and 0 <= c + dc < n]
    if not valid:
        return r, c
    if visited:
        unvisited = [(nr, nc) for nr, nc in valid if (nr, nc) not in visited]
        if unvisited:
            return random.choice(unvisited)
    return random.choice(valid)

class MovementEngine:
    def __init__(self, movement_type, grid_n, step_type="linear_1", start_pos=None):
        self.movement_type = movement_type
        self.grid_n = grid_n
        self.step_type = step_type
        self.n_total = grid_n * grid_n

        if movement_type in ("linear_row",):
            self.path = all_cells_row_major(grid_n)
        elif movement_type in ("linear_col",):
            self.path = all_cells_col_major(grid_n)
        elif movement_type in ("clockwise_1", "clockwise_2", "clockwise_3"):
            self.path = perimeter_cells(grid_n)
        elif movement_type == "anticlockwise_1":
            self.path = list(reversed(perimeter_cells(grid_n)))
        elif movement_type == "spiral_inward":
            self.path = spiral_cells(grid_n)
        elif movement_type == "alternating_dir":
            self.path = perimeter_cells(grid_n)
        else:
            self.path = None  

        n_path = len(self.path) if self.path else self.n_total

        if start_pos is not None:
            if self.path:
                if start_pos in self.path:
                    self.idx = self.path.index(start_pos)
                else:
                    self.idx = random.randint(0, n_path - 1)
            else:
                self.pos = start_pos
                self.idx = 0
        else:
            if self.path:
                self.idx = random.randint(0, n_path - 1)
                self.pos = self.path[self.idx]
            else:
                self.pos = (random.randint(0, grid_n - 1), random.randint(0, grid_n - 1))
                self.idx = 0

        if self.path:
            self.pos = self.path[self.idx % len(self.path)]

        self.dr, self.dc = random.choice([(1, 1), (1, -1), (-1, 1), (-1, -1)])
        self.visited = {self.pos}
        self.alt_clockwise = True
        self.frame = 0

    def _get_step(self):
        if self.step_type == "linear_1": return 1
        elif self.step_type == "linear_2": return 2
        elif self.step_type == "linear_3": return 3
        elif self.step_type == "alternating": return 1 if self.frame % 2 == 0 else 2
        elif self.step_type == "increasing": return min(self.frame + 1, 5)  
        return 1

    def current(self):
        return self.pos

    def advance(self):
        self.frame += 1
        step = self._get_step()
        n = self.grid_n

        if self.movement_type in ("linear_row", "linear_col", "clockwise_1", "anticlockwise_1"):
            self.idx = (self.idx + step) % len(self.path)
            self.pos = self.path[self.idx]
        elif self.movement_type == "clockwise_2":
            self.idx = (self.idx + 2) % len(self.path)
            self.pos = self.path[self.idx]
        elif self.movement_type == "clockwise_3":
            self.idx = (self.idx + 3) % len(self.path)
            self.pos = self.path[self.idx]
        elif self.movement_type == "diagonal_bounce":
            for _ in range(step):
                r, c = self.pos
                r, c, self.dr, self.dc = advance_bounce(r, c, self.dr, self.dc, n)
                self.pos = (r, c)
        elif self.movement_type == "knight":
            for _ in range(step):
                r, c = advance_knight(self.pos[0], self.pos[1], n, self.visited)
                self.pos = (r, c)
                self.visited.add(self.pos)
        elif self.movement_type == "spiral_inward":
            self.idx = min(self.idx + step, len(self.path) - 1)
            self.pos = self.path[self.idx]
        elif self.movement_type == "alternating_dir":
            perim = perimeter_cells(n)
            n_perim = len(perim)
            cur_idx = perim.index(self.pos) if self.pos in perim else 0
            direction = 1 if self.alt_clockwise else -1
            cur_idx = (cur_idx + direction * step) % n_perim
            self.pos = perim[cur_idx]
            self.alt_clockwise = not self.alt_clockwise

        return self.pos

    def generate_sequence(self, n_frames):
        positions = [self.current()]
        for _ in range(n_frames - 1):
            positions.append(self.advance())
        return positions

# ═══════════════════════════════════════════════════════════════════════════════
# SAFEGUARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
MAX_GEN_RETRIES  = 12

def _state_key(state):
    def _norm(v):
        if isinstance(v, dict):  return tuple(sorted((k, _norm(w)) for k, w in v.items()))
        if isinstance(v, list):  return tuple(_norm(i) for i in v)
        if isinstance(v, tuple): return tuple(_norm(i) for i in v)
        if isinstance(v, float): return round(v, 4)
        return v
    return _norm(state)

def _check_frames_unique(frames):
    keys = set()
    for f in frames:
        k = tuple(sorted(f["cells"]))
        if k in keys:
            return False
        keys.add(k)
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# ITEM GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
class GridSequenceGenerator:

    def __init__(self):
        self.sf = 4
        self.frame_hd = 180 * self.sf   
        self.frame_border = int(4 * self.sf)
        self.frame_sep = int(6 * self.sf)
        self.strip_pad = int(20 * self.sf)

        self.font_hd = None
        self.qlabel_hd = None
        self._load_fonts()

    def _load_fonts(self):
        found = False
        for d in FONT_DIRS:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    lf = fname.lower()
                    if "proxima" in lf and "soft" in lf:
                        if any(b in lf for b in ["italic", "light", "bold",
                                                  "semibold", "medium", "thin"]):
                            continue
                        try:
                            fp = os.path.join(d, fname)
                            self.font_hd = ImageFont.truetype(fp, 44 * self.sf)
                            self.qlabel_hd = ImageFont.truetype(fp, 28 * self.sf)
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
                        self.qlabel_hd = ImageFont.truetype(fp, 28 * self.sf)
                        found = True
                        break
                    except Exception:
                        continue
        if not found:
            self.font_hd = self.qlabel_hd = ImageFont.load_default()

    def generate_item(self, movement=None, n_elements=None, relationship=None,
                      step_type=None, grid_n=None, puzzle_format="static"):
        """
        Generate a grid sequence item based on assigned formats and constraints.
        Static items are strictly capped to 4 clue frames.
        """
        if movement is None: movement = random.choice(list(MOVEMENT_WEIGHTS.keys()))
        if grid_n is None: grid_n = random.choice([4, 5]) if movement == "spiral_inward" else random.choice([3, 4, 5])
        if n_elements is None: n_elements = random.choice([1, 1, 1, 2, 2, 3])
        if step_type is None: step_type = random.choice(list(STEP_WEIGHTS.keys()))
        if relationship is None:
            relationship = "same" if n_elements == 1 else random.choice(["same", "opposite", "different", "converging"])

        if movement == "spiral_inward" and grid_n < 4: grid_n = random.choice([4, 5])
        if movement in ("clockwise_2", "clockwise_3") and grid_n < 3: grid_n = 3

        diff_score, tier, b_est, age_range = compute_difficulty(
            movement, n_elements, relationship, step_type, grid_n)

        # Static format strictly requires exactly 4 clue frames + 1 answer frame
        if puzzle_format == "static":
            n_shown = 4
        else:
            n_shown = compute_frames_needed(n_elements, relationship, step_type)
        
        n_total_frames = n_shown + 1

        for attempt in range(MAX_GEN_RETRIES):
            engines = []
            used_starts = set()

            for elem_idx in range(n_elements):
                if elem_idx == 0:
                    elem_movement = movement
                elif relationship == "same":
                    elem_movement = movement
                elif relationship == "opposite":
                    opposites = {
                        "clockwise_1": "anticlockwise_1", "anticlockwise_1": "clockwise_1",
                        "clockwise_2": "anticlockwise_1", "clockwise_3": "anticlockwise_1",
                        "linear_row": "linear_col", "linear_col": "linear_row",
                    }
                    elem_movement = opposites.get(movement, movement)
                elif relationship == "different":
                    alt_pool = [m for m in MOVEMENT_WEIGHTS.keys() if m != movement and m not in ("spiral_inward",)]
                    elem_movement = random.choice(alt_pool) if alt_pool else movement
                elif relationship == "converging":
                    elem_movement = movement  
                else:
                    elem_movement = movement

                if relationship == "converging" and elem_idx > 0:
                    perim = perimeter_cells(grid_n)
                    first_start = engines[0].current()
                    if first_start in perim:
                        opp_idx = (perim.index(first_start) + len(perim) // 2) % len(perim)
                        start = perim[opp_idx]
                    else:
                        start = (grid_n - 1 - first_start[0], grid_n - 1 - first_start[1])
                else:
                    for _ in range(50):
                        start = (random.randint(0, grid_n - 1), random.randint(0, grid_n - 1))
                        if start not in used_starts: break

                used_starts.add(start)
                engine = MovementEngine(elem_movement, grid_n, step_type, start)
                engines.append(engine)

            all_positions = []
            for eng in engines:
                all_positions.append(eng.generate_sequence(n_total_frames))

            frames = []
            for fi in range(n_total_frames):
                cells = [all_positions[ei][fi] for ei in range(n_elements)]
                frames.append({"grid_n": grid_n, "cells": cells})

            if _check_frames_unique(frames):
                break

       
        # Force to the end if animated, otherwise random 50/50 for static
        if puzzle_format == "animated" or random.random() < 0.5:
            missing_idx = len(frames) - 1
        else:
            missing_idx = random.randint(0, len(frames) - 2)
            
        answer_frame = frames[missing_idx]
        correct_cells = answer_frame["cells"]
        
        distractors = self._generate_distractors(
            correct_cells, frames, missing_idx, grid_n, n_elements, movement, step_type)

        rule_desc = f"{movement}+elements={n_elements}+rel={relationship}+step={step_type}"
        return {
            "full_sequence": frames,
            "missing_idx": missing_idx,
            "answer": answer_frame,
            "n_shown": n_shown,
            "puzzle_format": puzzle_format,
            "distractors": distractors,
            "grid_n": grid_n,
            "movement": movement,
            "n_elements": n_elements,
            "relationship": relationship,
            "step_type": step_type,
            "tier": tier,
            "b_estimate": b_est,
            "age_range": age_range,
            "difficulty_score": round(diff_score, 2),
            "rule_axes": rule_desc,
            "distractor_strategy": "off_by_one+wrong_dir+overshoot+random_pos",
        }

    def _generate_distractors(self, correct_cells, full_sequence, missing_idx, grid_n,
                               n_elements, movement, step_type):
        perim = perimeter_cells(grid_n)
        all_rc = all_cells_row_major(grid_n)

        def _make(cells): return {"grid_n": grid_n, "cells": list(cells)}

        # D1: Use the frame immediately preceding the missing frame for "off by one" distractor
        prev_idx = max(0, missing_idx - 1)
        d1_cells = list(full_sequence[prev_idx]["cells"])
        d1 = _make(d1_cells)

        d2_cells = []
        for cell in correct_cells:
            if cell in perim:
                idx = perim.index(cell)
                d2_cells.append(perim[(idx + 1) % len(perim)])
            else:
                r, c = cell
                d2_cells.append(((r + 1) % grid_n, c))
        d2 = _make(d2_cells)

        d3_cells = []
        for cell in correct_cells:
            if cell in perim:
                idx = perim.index(cell)
                d3_cells.append(perim[(idx - 2) % len(perim)])
            else:
                r, c = cell
                d3_cells.append(((r - 1) % grid_n, (c - 1) % grid_n))
        d3 = _make(d3_cells)

        d4_cells = []
        for cell in correct_cells:
            for _ in range(20):
                rand_cell = random.choice(all_rc)
                if rand_cell != cell:
                    d4_cells.append(rand_cell)
                    break
            else:
                d4_cells.append((0, 0))
        d4 = _make(d4_cells)

        raw_distractors = [d1, d2, d3, d4]
        
        correct_state = _make(correct_cells)
        used_states = {_state_key(correct_state)}
        final_distractors = []

        for dist in raw_distractors:
            current = dist
            attempts = 0
            while _state_key(current) in used_states and attempts < 100:
                rand_cells = [(random.choice(all_rc)) for _ in range(n_elements)]
                current = _make(rand_cells)
                attempts += 1
            used_states.add(_state_key(current))
            final_distractors.append(current)

        return final_distractors

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDERING
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_grid_frame(self, state, show_question_mark=False):
        sf = self.sf
        fhd = self.frame_hd
        grid_n = state["grid_n"]

        canvas = Image.new("RGB", (fhd, fhd), "white")
        draw = ImageDraw.Draw(canvas)

        if show_question_mark:
            txt = "?"
            bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((fhd // 2 - tw // 2, fhd // 2 - th // 2),
                      txt, font=self.font_hd, fill="black")
            return canvas

        pad = int(18 * sf)
        inner = fhd - 2 * pad
        cell_sz = inner // grid_n
        lw = max(1, int(1.5 * sf))

        # 1. DRAW COLORED CELLS FIRST
        # They are drawn edge-to-edge for the exact cell bounds.
        element_colors = ["black", "#777777", "#BBBBBB"] 
        for idx, (row, col) in enumerate(state["cells"]):
            fill_color = element_colors[idx % len(element_colors)]
            
            x0 = pad + col * cell_sz
            y0 = pad + row * cell_sz
            x1 = pad + (col + 1) * cell_sz
            y1 = pad + (row + 1) * cell_sz
            
            draw.rectangle([x0, y0, x1, y1], fill=fill_color)

        # 2. DRAW INNER GRID LINES ON TOP
        # These overlay the edges of the colored squares perfectly.
        for i in range(1, grid_n):
            x = pad + i * cell_sz
            draw.line([(x, pad), (x, pad + inner)], fill="black", width=lw)
            draw.line([(pad, x), (pad + inner, x)], fill="black", width=lw)

        # 3. DRAW OUTER BORDER LAST
        # This gives a clean, uniform frame around the whole grid.
        draw.rectangle([pad, pad, pad + inner, pad + inner], outline="black", width=lw * 2)

        return canvas

    def _render_sequence_strip(self, full_sequence, missing_idx, show_answer=False):
        sf = self.sf
        n_panels = len(full_sequence)
        fw = fh = self.frame_hd
        sep = self.frame_sep
        pad = self.strip_pad

        strip_w = pad * 2 + n_panels * fw + (n_panels - 1) * sep
        # Removed lbl_h to crop tightly to the bottom padding
        strip_h = pad * 2 + fh 
        strip = Image.new("RGB", (strip_w, strip_h), "white")
        draw = ImageDraw.Draw(strip)

        for i in range(n_panels):
            x0 = pad + i * (fw + sep)
            y0 = pad

            if i == missing_idx and not show_answer:
                img = self._render_grid_frame(full_sequence[i], show_question_mark=True)
            else:
                img = self._render_grid_frame(full_sequence[i])

            strip.paste(img, (x0, y0))

            # The block drawing the 1-5 labels has been entirely removed

        return strip

    def _render_animated_gif(self, full_sequence, missing_idx):
        sf = self.sf
        fw = fh = self.frame_hd

        def _gif_frame(state, is_q=False):
            img = self._render_grid_frame(state, show_question_mark=is_q)
            sm = img.resize((fw // sf, fh // sf), Image.Resampling.LANCZOS)
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
        sf = self.sf
        fw = fh = self.frame_hd
        gap = int(16 * sf)
        pad_x = int(24 * sf)
        pad_y = int(20 * sf)
        lbl_h = int(64 * sf)
        lbl_gap = int(12 * sf)
        n = len(options)

        strip_w = 2 * pad_x + n * fw + (n - 1) * gap
        strip_h = pad_y + fh + lbl_gap + lbl_h
        strip = Image.new("RGB", (strip_w, strip_h), "white")
        draw = ImageDraw.Draw(strip)

        for i, (opt, lbl) in enumerate(zip(options, "ABCDE")):
            x0 = pad_x + i * (fw + gap)
            y0 = pad_y
            cx = x0 + fw // 2

            strip.paste(self._render_grid_frame(opt), (x0, y0))

            bbox = draw.textbbox((0, 0), lbl, font=self.font_hd)
            draw.text((cx - (bbox[2] - bbox[0]) // 2, y0 + fh + lbl_gap),
                      lbl, font=self.font_hd, fill="black")

        return strip

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE ITEM — Produces single selected format based on rules 
    # ═══════════════════════════════════════════════════════════════════════════
    def save_item(self, item_data, item_id, out_root):
        sf = self.sf
        tier = item_data["tier"]
        grid_n = item_data["grid_n"]
        movement = item_data["movement"]
        fmt = item_data["puzzle_format"]
        tier_label = tier.replace("_", "-").title()
        move_label = movement.replace("_", "-")

        full_sequence = item_data["full_sequence"]
        missing_idx = item_data["missing_idx"]
        answer = item_data["answer"]

        distractors = list(item_data.get("distractors", []))
        while len(distractors) < 4:
            distractors.append(copy.deepcopy(answer))
        distractors = distractors[:4]

        correct_pos = random.randint(0, 4)
        correct_letter = "ABCDE"[correct_pos]
        options = list(distractors)
        options.insert(correct_pos, answer)

        id_str = f"{item_id:03d}"
        folder = f"GridSeq_{grid_n}x{grid_n}_{move_label}_{tier_label}_{fmt.upper()}_{id_str}"
        path = os.path.join(out_root, folder)
        os.makedirs(path, exist_ok=True)

        item_info = {
            "folder": folder,
            "item_id": id_str,
            "format": fmt,
            "correct_letter": correct_letter,
            "paths": {},
        }

        if fmt == "static":
            q_hd = self._render_sequence_strip(full_sequence, missing_idx, show_answer=False)
            q_path = os.path.join(path, f"{folder}_question.png")
            q_hd.resize((q_hd.width // sf, q_hd.height // sf),
                         Image.Resampling.LANCZOS).save(q_path)
            item_info["paths"]["question"] = q_path

            sa_hd = self._render_sequence_strip(full_sequence, missing_idx, show_answer=True)
            sa_path = os.path.join(path, f"{folder}_static_answers.png")
            sa_hd.resize((sa_hd.width // sf, sa_hd.height // sf),
                          Image.Resampling.LANCZOS).save(sa_path)
            item_info["paths"]["static_answers"] = sa_path

        elif fmt == "animated":
            gif_path = os.path.join(path, f"{folder}_animated.gif")
            gf, dur = self._render_animated_gif(full_sequence, missing_idx)
            gf[0].save(gif_path, save_all=True, append_images=gf[1:],
                        duration=dur, loop=0, optimize=False)
            item_info["paths"]["animated"] = gif_path

        c_hd = self._render_answer_strip(options)
        c_path = os.path.join(path, f"{folder}_choices.png")
        c_hd.resize((c_hd.width // sf, c_hd.height // sf),
                       Image.Resampling.LANCZOS).save(c_path)
        item_info["paths"]["choices"] = c_path

        return item_info


# ═══════════════════════════════════════════════════════════════════════════════
# SPREAD HELPER — balanced generation across all parameters
# ═══════════════════════════════════════════════════════════════════════════════
def build_spread_jobs(n_items, movements=None, grid_sizes=None):
    if movements is None:
        movements = list(MOVEMENT_WEIGHTS.keys())
    if grid_sizes is None:
        grid_sizes = [3, 4, 5]

    elements = [1, 1, 2, 2, 3]
    steps = list(STEP_WEIGHTS.keys())
    relationships = ["same", "opposite", "different", "converging"]

    jobs = []
    mov_cycle = movements[:]
    random.shuffle(mov_cycle)
    mi = 0

    while len(jobs) < n_items:
        if mi >= len(mov_cycle):
            random.shuffle(mov_cycle)
            mi = 0

        movement = mov_cycle[mi]
        mi += 1

        if movement == "spiral_inward":
            gn = random.choice([g for g in grid_sizes if g >= 4] or [4])
        else:
            gn = random.choice(grid_sizes)

        ne = random.choice(elements)
        st = random.choice(steps)
        rel = "same" if ne == 1 else random.choice(relationships)

        jobs.append({
            "movement": movement,
            "grid_n": gn,
            "n_elements": ne,
            "step_type": st,
            "relationship": rel,
        })

    random.shuffle(jobs)
    return jobs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from collections import Counter

    gen = GridSequenceGenerator()

    print("\nNVR Grid Sequence Generator")
    print("=" * 56)
    print("Generates grid-based movement sequence puzzles.")
    print("50:50 Static or Animated split. Constraints applied.")
    print("All 10 movement types, grid sizes 3×3–5×5, balanced spread.\n")

    raw_n = input("How many items? [default: 12]: ").strip()
    n_items = int(raw_n) if raw_n.isdigit() and int(raw_n) > 0 else 12

    jobs = build_spread_jobs(n_items)
    
    # Pre-calculate Formats to apply constraints
    for job in jobs:
        # Skew the initial random choice (e.g., 25% static, 75% animated)
        fmt = random.choices(["static", "animated"], weights=[0.4, 0.6], k=1)[0]
        
        # If there are 3 elements and they aren't doing the exact 'same' thing, force static.
        if job["n_elements"] == 3 and job["relationship"] != "same":
            fmt = "static"
            
        job["puzzle_format"] = fmt

    # ── Summary ───────────────────────────────────────────────────────────────
    mov_counts = Counter(j["movement"] for j in jobs)
    gs_counts = Counter(j["grid_n"] for j in jobs)
    fmt_counts = Counter(j["puzzle_format"] for j in jobs)
    
    print(f"\nGenerating {n_items} item(s)  →  {OUTPUT_FOLDER}")
    print(f"  Grid sizes: " + "  ".join(f"{k}×{k}={v}" for k, v in sorted(gs_counts.items())))
    print(f"  Movements : " + "  ".join(f"{k[:12]}={v}" for k, v in mov_counts.items()))
    print(f"  Formats   : Static={fmt_counts.get('static', 0)}  Animated={fmt_counts.get('animated', 0)}")
    print()

    # ── Generate ──────────────────────────────────────────────────────────────
    manifest_rows = []
    for item_id, job in enumerate(jobs, 1):
        print(f"  [{item_id:3d}/{n_items}]  {job['grid_n']}×{job['grid_n']}  "
              f"{job['movement']:20s}  {job['n_elements']} elem  "
              f"fmt={job['puzzle_format']:8s} ...", end=" ", flush=True)

        try:
            item_data = gen.generate_item(**job)
            item_info = gen.save_item(item_data, item_id, OUTPUT_FOLDER)

            shared_base = {
                "Grid_Size": f"{item_data['grid_n']}x{item_data['grid_n']}",
                "Movement": item_data["movement"],
                "N_Elements": item_data["n_elements"],
                "Relationship": item_data["relationship"],
                "Step_Type": item_data["step_type"],
                "Difficulty_Tier": item_data["tier"],
                "Difficulty_Score": item_data["difficulty_score"],
                "b_estimate": item_data["b_estimate"],
                "Age_Range": item_data["age_range"],
                "Rule_Axes": item_data["rule_axes"],
                "Distractor_Strategy": item_data["distractor_strategy"],
            }

            manifest_rows.append({
                "Item_ID": item_info["item_id"],
                "Folder": item_info["folder"],
                "Format": item_info["format"],
                **shared_base,
                "N_Shown_Frames": item_data["n_shown"],
                "Correct_Position": item_info["correct_letter"],
                "Question_PNG": os.path.basename(item_info["paths"]["question"]) if "question" in item_info["paths"] else "",
                "Static_Answers_PNG": os.path.basename(item_info["paths"]["static_answers"]) if "static_answers" in item_info["paths"] else "",
                "Animated_GIF": os.path.basename(item_info["paths"]["animated"]) if "animated" in item_info["paths"] else "",
                "Choices_PNG": os.path.basename(item_info["paths"]["choices"]) if "choices" in item_info["paths"] else "",
            })

            print(f"→ {item_data['tier']}  (score {item_data['difficulty_score']:.1f})  "
                  f"frames={item_data['n_shown']}f")

        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

    # ── Write manifest ────────────────────────────────────────────────────────
    manifest_path = os.path.join(OUTPUT_FOLDER, "manifest.csv")
    if manifest_rows:
        with open(manifest_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=manifest_rows[0].keys())
            writer.writeheader()
            writer.writerows(manifest_rows)

    # ── Final summary ─────────────────────────────────────────────────────────
    n_puzzles = n_items
    n_total_items = len(manifest_rows)
    tier_counts = Counter(r["Difficulty_Tier"] for r in manifest_rows)
    print(f"\n{'=' * 56}")
    print(f"Complete. Generated {n_puzzles} items.")
    print(f"Tier breakdown:")
    for tier in ["easy", "easy_med", "medium", "hard", "very_hard", "extreme"]:
        if tier_counts.get(tier, 0) > 0:
            print(f"  {tier:12s}: {tier_counts[tier]:3d} item(s)")
    print(f"\nOutput  : {OUTPUT_FOLDER}")
    print(f"Manifest: {manifest_path}")