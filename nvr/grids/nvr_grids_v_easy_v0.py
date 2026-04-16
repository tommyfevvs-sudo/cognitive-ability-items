"""
NVR_grids_v1.py
================
Non-Verbal Reasoning — Grids Item Generator
Generates 2×2 (analogy) and 3×3 (induction) grid items as:
  • Static PNG  — full grid, answer revealed
  • Question GIF — animated (shapes rotate), answer cell = "?"
  • Answer GIF   — animated answer cell only

Rendering conventions match nvr_codes_rotating_fixed.py:
  • sf = 4 HD render → LANCZOS downsample on export
  • Proxima Soft Regular font (Arial / DejaVu fallback)
  • Two-pass unified bounding-box crop → stable GIF (no jumping)
  • 60 frames, 30 ms/frame, loop = 0  (~1.8 s loop)

Difficulty tiers (IRT b-parameter ranges from pilot analysis):
  Easy         b ≈ −2.5 → −1.5   Y6–8
  Easy-Medium  b ≈ −1.5 → −0.5   Y8–10
  Medium       b ≈ −0.5 →  0.5   Y10–12
  Hard         b ≈  0.5 →  1.5   Y12–14
  Very Hard    b ≈  1.5 →  2.5   Y14–16
  Extreme      b ≈  2.5 →  4.0   Y12+ / adult (unestimable in pilot)
"""

import random
import os
import math
import csv
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Output folder ──────────────────────────────────────────────────────────────
DESKTOP_PATH  = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_FOLDER = os.path.join(DESKTOP_PATH, "NVR_Grids_Production")
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

# ── Difficulty tier definitions ────────────────────────────────────────────────
TIERS = {
    "easy":       {"b_range": (-2.5, -1.5), "age_range": "6-8",   "n_rules": 1, "complexity": 1},
    "easy_med":   {"b_range": (-1.5, -0.5), "age_range": "8-10",  "n_rules": 1, "complexity": 2},
    "medium":     {"b_range": (-0.5,  0.5), "age_range": "10-12", "n_rules": 2, "complexity": 3},
    "hard":       {"b_range": ( 0.5,  1.5), "age_range": "12-14", "n_rules": 2, "complexity": 4},
    "very_hard":  {"b_range": ( 1.5,  2.5), "age_range": "14-16", "n_rules": 3, "complexity": 5},
    "extreme":    {"b_range": ( 2.5,  4.0), "age_range": "16+",   "n_rules": 3, "complexity": 6},
}

# ═══════════════════════════════════════════════════════════════════════════════
class NVRGridGenerator:
    """Generates and renders NVR Grid items (2×2 and 3×3)."""

    # ── Initialise ─────────────────────────────────────────────────────────────
    def __init__(self):
        # Scale factor — HD render then LANCZOS downsample on export
        self.sf = 4

        # Grid cell geometry (HD pixels)
        self.cell_size_hd  = 200 * self.sf    # 800 px per cell at HD
        self.grid_line_hd  = int(3  * self.sf) # inner grid line width
        self.border_hd     = int(5  * self.sf) # outer border width
        self.outer_pad_hd  = int(30 * self.sf) # canvas padding around grid

        # Shape radii (fraction of half-cell)
        half = self.cell_size_hd // 2
        self.r_small  = int(half * 0.30)
        self.r_medium = int(half * 0.46)
        self.r_large  = int(half * 0.66)
        self.r_map    = {"small": self.r_small, "medium": self.r_medium, "large": self.r_large}
        self.r_sec    = int(half * 0.18)  # secondary element radius

        # Shape pools
        self.all_shapes       = ["circle", "square", "triangle", "pentagon",
                                 "hexagon", "arrow", "star", "cross_shape"]
        self.rotatable_shapes = ["triangle", "arrow", "pentagon", "star"]
        self.simple_shapes    = ["circle", "square", "hexagon", "cross_shape"]

        # Fill pools
        self.solid_fills = ["solid", "hollow"]
        self.hatch_fills = [
            ("lines", "vertical"),
            ("lines", "diagonal_tl_br"),
            ("lines", "diagonal_tr_bl"),
            ("grids", "standard_large"),
            ("grids", "standard_small"),
            ("grids", "tilted_diamond"),
            ("wavy",  "wavy_v"),
            ("mini_tri", "tri_up"),
            ("tiling", "brickwork"),
        ]
        # Hatch levels for extreme-tier hatch-as-fill-level rule (Q5-type)
        self.hatch_levels = [
            ("lines", "diagonal_tl_br"),   # level 0: sparse diagonal — lightest
            ("lines", "vertical"),          # level 1: vertical lines
            ("grids", "standard_large"),    # level 2: coarse grid
            ("grids", "standard_small"),    # level 3: dense grid — heaviest
        ]
        self.all_fills = self.solid_fills + self.hatch_fills

        # ── Font loading (identical logic to codes script) ─────────────────────
        self.font_hd  = None
        self.qlabel_hd = None
        found = False

        print("Searching for Proxima Soft Regular...")
        for d in FONT_DIRS:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    lf = fname.lower()
                    if "proxima" in lf and "soft" in lf:
                        bad = ["italic", " it.", " it ", "light", " lt",
                               "bold", "semibold", "medium", " thin"]
                        if any(b in lf for b in bad):
                            continue
                        if lf.endswith("it.otf") or lf.endswith("it.ttf"):
                            continue
                        try:
                            fp = os.path.join(d, fname)
                            self.font_hd   = ImageFont.truetype(fp, 44 * self.sf)
                            self.qlabel_hd = ImageFont.truetype(fp, 28 * self.sf)
                            print(f"  SUCCESS: {fname}")
                            found = True
                            break
                        except Exception:
                            continue
                if found:
                    break
            except Exception:
                continue

        if not found:
            print("  Proxima Soft not found — trying fallback fonts.")
            for fp in FALLBACK_FONTS:
                if os.path.exists(fp):
                    try:
                        self.font_hd   = ImageFont.truetype(fp, 44 * self.sf)
                        self.qlabel_hd = ImageFont.truetype(fp, 28 * self.sf)
                        print(f"  Fallback: {fp}")
                        found = True
                        break
                    except Exception:
                        continue
        if not found:
            print("  WARNING: Using built-in default font — labels will be small.")
            self.font_hd   = ImageFont.load_default()
            self.qlabel_hd = ImageFont.load_default()

    # ═══════════════════════════════════════════════════════════════════════════
    # SHAPE COORDINATES  (identical to codes script — rotation around true centre)
    # ═══════════════════════════════════════════════════════════════════════════
    def get_shape_coords_hd(self, shape_type, cx, cy, r, rotation=0):
        pts = []
        if shape_type == "circle":
            return [cx - r, cy - r, cx + r, cy + r]
        elif shape_type == "square":
            adj = r * 0.85
            pts = [(cx-adj, cy-adj), (cx+adj, cy-adj),
                   (cx+adj, cy+adj), (cx-adj, cy+adj)]
        elif shape_type == "triangle":
            for i in range(3):
                a = math.radians(-90 + i * 120)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        elif shape_type == "arrow":
            pts = [(cx + 1.25*r, cy), (cx - 0.75*r, cy - r),
                   (cx - 0.15*r, cy), (cx - 0.75*r, cy + r)]
        elif shape_type == "star":
            for i in range(10):
                a = math.radians(-90 + i * 36)
                cr = r if i % 2 == 0 else r * 0.45
                pts.append((cx + cr * math.cos(a), cy + cr * math.sin(a)))
        elif shape_type == "cross_shape":
            w = r * 0.35
            pts = [(cx-w, cy-r), (cx+w, cy-r), (cx+w, cy-w), (cx+r, cy-w),
                   (cx+r, cy+w), (cx+w, cy+w), (cx+w, cy+r), (cx-w, cy+r),
                   (cx-w, cy+w), (cx-r, cy+w), (cx-r, cy-w), (cx-w, cy-w)]
        elif shape_type == "pentagon":
            for i in range(5):
                a = math.radians(-90 + i * 72)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        elif shape_type == "hexagon":
            for i in range(6):
                a = math.radians(-90 + i * 60)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

        # Rotate around the true centre — bypasses bounding-box centring artefacts
        if rotation != 0 and pts:
            rad = math.radians(rotation)
            return [
                (cx + (px-cx)*math.cos(rad) - (py-cy)*math.sin(rad),
                 cy + (px-cx)*math.sin(rad) + (py-cy)*math.cos(rad))
                for px, py in pts
            ]
        return pts

    # ═══════════════════════════════════════════════════════════════════════════
    # PATTERN DRAWING  (identical to codes script)
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_pattern_hd(self, draw, fill_data, size):
        sf = self.sf
        category, variant = fill_data

        if category == "tiling":
            if variant == "brickwork":
                bw, bh = 24*sf, 12*sf
                for y in range(0, size + bh, bh):
                    offset = (bw // 2) if (y // bh) % 2 == 0 else 0
                    draw.line([(0, y), (size, y)], fill="black", width=1*sf)
                    for x in range(-bw, size + bw, bw):
                        draw.line([(x+offset, y), (x+offset, y+bh)],
                                  fill="black", width=2*sf)
            elif variant == "basketweave":
                bs = 20 * sf
                for x in range(0, size, bs):
                    for y in range(0, size, bs):
                        if (x//bs + y//bs) % 2 == 0:
                            for i in range(2, bs, 6*sf):
                                draw.line([(x+2*sf, y+i), (x+bs-2*sf, y+i)],
                                          fill="black", width=2*sf)
                        else:
                            for i in range(2, bs, 6*sf):
                                draw.line([(x+i, y+2*sf), (x+i, y+bs-2*sf)],
                                          fill="black", width=2*sf)
                        draw.rectangle([x, y, x+bs, y+bs], outline="black", width=1*sf)
            elif variant == "hexagonal_honeycomb":
                h_r = 10*sf
                h_w = math.sqrt(3) * h_r
                h_h = 2 * h_r
                for row in range(-1, int(size / (h_h*0.75)) + 2):
                    for col in range(-1, int(size / h_w) + 2):
                        hcx = col*h_w + (h_w/2 if row % 2 else 0)
                        hcy = row*h_h*0.75
                        hp  = [(hcx + h_r*math.cos(math.radians(30+i*60)),
                                hcy + h_r*math.sin(math.radians(30+i*60)))
                               for i in range(6)]
                        draw.polygon(hp, outline="black", fill=None, width=1*sf)

        elif category == "arrows":
            for ax in range(0, size, 26*sf):
                for ay in range(0, size, 26*sf):
                    if   variant == "up":    h,s,l,r_h = (ax,ay-6*sf),(ax,ay+6*sf),(ax-4*sf,ay-2*sf),(ax+4*sf,ay-2*sf)
                    elif variant == "down":  h,s,l,r_h = (ax,ay+6*sf),(ax,ay-6*sf),(ax-4*sf,ay+2*sf),(ax+4*sf,ay+2*sf)
                    elif variant == "left":  h,s,l,r_h = (ax-6*sf,ay),(ax+6*sf,ay),(ax-2*sf,ay-4*sf),(ax-2*sf,ay+4*sf)
                    else:                    h,s,l,r_h = (ax+6*sf,ay),(ax-6*sf,ay),(ax+2*sf,ay-4*sf),(ax+2*sf,ay+4*sf)
                    draw.line([s, h], fill="black", width=2*sf)
                    draw.line([l, h], fill="black", width=2*sf)
                    draw.line([r_h, h], fill="black", width=2*sf)

        elif category == "wavy":
            for i in range(-size, size*2, 15*sf):
                wpts = []
                for j in range(0, size+10, 4*sf):
                    off = math.sin(j * 0.05) * (5*sf)
                    if   variant == "wavy_v": wpts.append((i+off, j))
                    elif variant == "wavy_h": wpts.append((j, i+off))
                    else:                     wpts.append((i+j+off, j))
                if len(wpts) > 1:
                    draw.line(wpts, fill="black", width=2*sf)

        elif category == "mini_tri":
            ts, gp = 6*sf, 22*sf
            for tx in range(0, size, gp):
                for ty in range(0, size, gp):
                    if   variant == "tri_up":    tri = [(tx, ty-ts), (tx+ts, ty+ts), (tx-ts, ty+ts)]
                    elif variant == "tri_down":  tri = [(tx, ty+ts), (tx+ts, ty-ts), (tx-ts, ty-ts)]
                    elif variant == "tri_left":  tri = [(tx-ts, ty), (tx+ts, ty-ts), (tx+ts, ty+ts)]
                    else:                        tri = [(tx+ts, ty), (tx-ts, ty-ts), (tx-ts, ty+ts)]
                    draw.polygon(tri, fill="black")

        elif category == "lines":
            for li in range(-size, size*2, 14*sf):
                if   variant == "vertical":        draw.line([(li, 0), (li, size)],      fill="black", width=2*sf)
                elif variant == "diagonal_tl_br":  draw.line([(li, 0), (li+size, size)], fill="black", width=2*sf)
                else:                              draw.line([(li, 0), (li-size, size)], fill="black", width=2*sf)

        elif category == "grids":
            if variant == "tilted_diamond":
                gs = 16*sf
                for gi in range(-size, size*2, gs):
                    draw.line([(gi, 0), (gi-size, size)], fill="black", width=2*sf)
                    draw.line([(gi-size, 0), (gi, size)], fill="black", width=2*sf)
            else:
                gs = 22*sf if "large" in variant else 10*sf
                for gx in range(0, size + 10*sf, gs):
                    draw.line([(gx, 0), (gx, size)], fill="black", width=2*sf)
                for gy in range(0, size + 10*sf, gs):
                    draw.line([(0, gy), (size, gy)], fill="black", width=2*sf)

    # ═══════════════════════════════════════════════════════════════════════════
    # MASKED OBJECT (identical to codes script)
    # ═══════════════════════════════════════════════════════════════════════════
    def _draw_masked_obj(self, canvas, shape, pattern, cx, cy, r,
                         rotation=0, outline_w=2.5):
        size = int(r * 3.0)
        buf  = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        mask = Image.new("L",    (size, size), 0)

        self.draw_pattern_hd(ImageDraw.Draw(buf), pattern, size)
        loc_pts  = self.get_shape_coords_hd(shape, size//2, size//2, r, rotation)
        glob_pts = self.get_shape_coords_hd(shape, cx, cy, r, rotation)

        draw      = ImageDraw.Draw(canvas)
        weight_hd = int(outline_w * self.sf)

        if shape == "circle":
            ImageDraw.Draw(mask).ellipse(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size//2), int(cy - size//2)), mask)
            draw.ellipse(glob_pts, outline="black", width=weight_hd)
        else:
            closed = glob_pts + [glob_pts[0], glob_pts[1]]
            draw.line(closed, fill="black", width=weight_hd * 2, joint="curve")
            draw.polygon(glob_pts, fill="black")
            ImageDraw.Draw(mask).polygon(loc_pts, fill=255)
            canvas.paste(buf, (int(cx - size//2), int(cy - size//2)), mask)

    # ═══════════════════════════════════════════════════════════════════════════
    # DRAW ONE SHAPE  (dispatches solid / hollow / pattern)
    # ═══════════════════════════════════════════════════════════════════════════
    def _draw_shape(self, canvas, shape, fill, cx, cy, r, rotation=0, outline_w=2.5):
        draw   = ImageDraw.Draw(canvas)
        weight = int(outline_w * self.sf)
        coords = self.get_shape_coords_hd(shape, cx, cy, r, rotation)

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
            # Pattern fill — use masked object pipeline
            self._draw_masked_obj(canvas, shape, fill, cx, cy, r, rotation, outline_w)

    # ═══════════════════════════════════════════════════════════════════════════
    # DRAW CELL CONTENT
    # ═══════════════════════════════════════════════════════════════════════════
    def _draw_cell_content(self, canvas, cx, cy, cell_data, rot_offset=0):
        """Render one cell's content centred at (cx, cy)."""
        cd = cell_data

        # ── Question-mark placeholder ──────────────────────────────────────────
        if cd.get("is_question_mark"):
            draw = ImageDraw.Draw(canvas)
            txt  = "?"
            bbox = draw.textbbox((0, 0), txt, font=self.font_hd)
            tw   = bbox[2] - bbox[0]
            th   = bbox[3] - bbox[1]
            draw.text((cx - tw//2, cy - th//2), txt, font=self.font_hd, fill="black")
            return

        # ── Sub-cell type (Q10 extreme — 2×2 mini-grid within cell) ───────────
        if cd.get("sub_cells"):
            self._draw_sub_cell_grid(canvas, cx, cy, cd["sub_cells"])
            return

        # ── Multi-layer type (Q9 extreme — stacked independent layers) ─────────
        if cd.get("layers"):
            for layer in cd["layers"]:
                r   = self.r_map.get(layer.get("size", "medium"), self.r_medium)
                rot = layer.get("rotation", 0) + rot_offset
                self._draw_shape(canvas, layer["shape"], layer["fill"],
                                 cx, cy, r, rot,
                                 layer.get("outline_w", 2.5))
            return

        # ── Standard cell ──────────────────────────────────────────────────────
        shape   = cd.get("shape",   "circle")
        fill    = cd.get("fill",    "hollow")
        r       = self.r_map.get(cd.get("size", "medium"), self.r_medium)
        base_rot = cd.get("rotation", 0)
        count   = cd.get("count", 1)
        ow      = cd.get("outline_w", 2.5)

        positions = self._count_positions(count, r)
        for (ox, oy) in positions:
            rot = base_rot + rot_offset
            self._draw_shape(canvas, shape, fill, cx + ox, cy + oy, r, rot, ow)

        # Secondary element (small shape in lower-right of cell)
        if cd.get("secondary_shape"):
            sec_cx = cx + int(r * 0.65)
            sec_cy = cy + int(r * 0.65)
            self._draw_shape(canvas, cd["secondary_shape"], "solid",
                             sec_cx, sec_cy, self.r_sec, 0, 1.5)

        # Number inside shape — drawn centred in each shape instance
        if cd.get("number") is not None:
            draw    = ImageDraw.Draw(canvas)
            num_txt = str(cd["number"])
            # Colour contrasts with fill: white on solid, black on hollow/pattern
            txt_col = "white" if fill == "solid" else "black"
            for (ox, oy) in positions:
                bbox = draw.textbbox((0, 0), num_txt, font=self.qlabel_hd)
                tw   = bbox[2] - bbox[0]
                th   = bbox[3] - bbox[1]
                draw.text((cx + ox - tw // 2, cy + oy - th // 2 + int(th * 0.05)),
                          num_txt, font=self.qlabel_hd, fill=txt_col)

    def _count_positions(self, count, r):
        """Return list of (dx, dy) offsets for count shapes within a cell."""
        if count == 1:
            return [(0, 0)]
        elif count == 2:
            off = int(r * 0.65)
            return [(-off, 0), (off, 0)]
        elif count == 3:
            sm = int(r * 0.55)
            return [(-sm, int(r*0.40)), (sm, int(r*0.40)), (0, -int(r*0.50))]
        else:
            off = int(r * 0.55)
            return [(-off, -off), (off, -off), (-off, off), (off, off)]

    def _draw_sub_cell_grid(self, canvas, cx, cy, sub_data):
        """Q10-type: 2×2 mini-grid of shapes inside a cell."""
        sub_r   = int(self.cell_size_hd * 0.18)
        gap     = int(self.cell_size_hd * 0.06)
        shape   = sub_data.get("shape", "square")
        filled  = set(sub_data.get("filled_indices", [0]))
        offsets = [
            (-sub_r - gap, -sub_r - gap),
            ( sub_r + gap, -sub_r - gap),
            (-sub_r - gap,  sub_r + gap),
            ( sub_r + gap,  sub_r + gap),
        ]
        for i, (ox, oy) in enumerate(offsets):
            fill = "solid" if i in filled else "hollow"
            self._draw_shape(canvas, shape, fill, cx + ox, cy + oy, sub_r, 0, 2.0)

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDER FULL GRID IMAGE
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_grid(self, cells, grid_size, show_answer=True, rot_offset=0):
        """
        Render grid_size × grid_size grid.
        cells : flat list (row-major), last entry is the answer cell.
        Returns HD RGB PIL Image.
        """
        cs   = self.cell_size_hd
        lw   = self.grid_line_hd
        bw   = self.border_hd
        pad  = self.outer_pad_hd

        # Cell centres: cell (r, c) starts at pad + bw + c*(cs + lw)
        grid_span = grid_size * cs + (grid_size - 1) * lw
        canvas_w  = 2 * pad + 2 * bw + grid_span
        canvas_h  = canvas_w  # square

        canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
        draw   = ImageDraw.Draw(canvas)

        # Outer border
        draw.rectangle(
            [pad, pad, pad + 2*bw + grid_span, pad + 2*bw + grid_span],
            outline="black", width=bw
        )

        # Inner grid lines
        for i in range(1, grid_size):
            x = pad + bw + i * (cs + lw) - lw  # left edge of gap
            y = x
            draw.rectangle([x, pad+bw, x+lw, pad+bw+grid_span],
                           fill="black")       # vertical
            draw.rectangle([pad+bw, y, pad+bw+grid_span, y+lw],
                           fill="black")       # horizontal

        # Draw each cell
        answer_idx = grid_size * grid_size - 1
        for idx, cell in enumerate(cells):
            row = idx // grid_size
            col = idx % grid_size
            # Centre of this cell
            cx = pad + bw + col * (cs + lw) + cs // 2
            cy = pad + bw + row * (cs + lw) + cs // 2

            if idx == answer_idx and not show_answer:
                self._draw_cell_content(canvas, cx, cy, {"is_question_mark": True}, 0)
            else:
                self._draw_cell_content(canvas, cx, cy, cell, rot_offset)

        return canvas

    # ═══════════════════════════════════════════════════════════════════════════
    # ITEM GENERATION — 2×2
    # ═══════════════════════════════════════════════════════════════════════════
    def _gen_2x2(self, tier):
        """
        Generate a 2×2 analogy item.

        Layout:  [A][B]      Rule applied left→right (col_rule)
                 [C][D=?]    A separate row_rule can vary top→bottom.

        For each attribute, we pick two values (at col=0 and col=1).
        Both rows obey the same col_rule; the row_rule adds a second dimension.
        """
        cfg = TIERS[tier]
        complexity = cfg["complexity"]
        n_rules    = cfg["n_rules"]

        # ── Choose which attributes change ────────────────────────────────────
        rule_pool = ["shape", "fill", "size", "rotation", "count"]
        if complexity >= 2:
            rule_pool.append("number")       # digit inside shape (1–4)
        if complexity >= 3:
            rule_pool += ["secondary",       # smaller shape in corner
                          "outline"]         # border thickness thin→thick
        if complexity >= 6:
            rule_pool = ["hatch_level", "rotation", "count"]

        n_pick = min(n_rules, len(rule_pool))
        rules  = random.sample(rule_pool, n_pick)
        col_rule = rules[0]
        row_rule = rules[1] if len(rules) > 1 else None

        # ── Base attribute pools ──────────────────────────────────────────────
        need_rotatable = "rotation" in rules
        shape_pool = (self.rotatable_shapes if need_rotatable else self.all_shapes)
        base_shape = random.choice(shape_pool)

        # Two distinct shapes for shape rule
        s_pair = random.sample(shape_pool, 2)

        # Fill pair
        if complexity <= 2:
            f_pair = random.choice([("hollow", "solid"), ("solid", "hollow")])
        elif complexity <= 4:
            f_pair = (random.choice(self.solid_fills),
                      random.choice(self.hatch_fills))
        else:
            f_pair = random.sample(self.hatch_fills, 2)

        # Hatch-level pair (extreme Q5-type).
        # Fix: was always levels [0] vs [2]. Now pick two levels that are at
        # least one step apart to guarantee a visible density contrast.
        hl_indices = random.choice([(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)])
        hl_pair = (self.hatch_levels[hl_indices[0]], self.hatch_levels[hl_indices[1]])

        # Size pair
        sz_pair = random.choice([("small", "medium"), ("medium", "large"), ("small", "large")])

        # Rotation pair — minimum 90° step so the difference is visually obvious
        rot_base = random.choice([0, 45, 90, 135])
        rot_step = random.choice([90, 120, 135, 180])
        rot_pair = (rot_base, (rot_base + rot_step) % 360)

        # Count pair
        cnt_pair = random.choice([(1, 2), (1, 3), (2, 3)])

        # Secondary pair (None / shape)
        sec_pair = (None, random.choice(["circle", "square", "triangle"]))

        # Number pair — digit inside the shape (e.g. 1→2, 2→4, etc.)
        num_pair = random.choice([(1, 2), (1, 3), (2, 3), (2, 4), (3, 4)])

        # Outline-weight pair — thin vs thick border
        ow_pair  = (1.0, 5.5)   # → 4px vs 22px at HD → 1px vs 5.5px at export

        # Default base values
        base_fill = f_pair[0]
        base_size = sz_pair[0]
        base_rot  = rot_pair[0]
        base_cnt  = cnt_pair[0]

        def get_val(rule, step, pair):
            """Return pair[0] for step=0, pair[1] for step=1."""
            return pair[step % 2]

        base_num = None   # number inside shape (None = no number shown)
        base_ow  = 2.5   # default outline weight

        def make_cell(col_step, row_step):
            shape   = base_shape
            fill    = base_fill
            size    = base_size
            rot     = base_rot
            count   = base_cnt
            sec     = None
            num     = base_num
            ow      = base_ow

            # Apply column rule (primary dimension)
            if   col_rule == "shape":       shape = get_val(col_rule, col_step, s_pair)
            elif col_rule == "fill":        fill  = get_val(col_rule, col_step, f_pair)
            elif col_rule == "hatch_level": fill  = get_val(col_rule, col_step, hl_pair)
            elif col_rule == "size":        size  = get_val(col_rule, col_step, sz_pair)
            elif col_rule == "rotation":    rot   = get_val(col_rule, col_step, rot_pair)
            elif col_rule == "count":       count = get_val(col_rule, col_step, cnt_pair)
            elif col_rule == "secondary":   sec   = get_val(col_rule, col_step, sec_pair)
            elif col_rule == "number":      num   = get_val(col_rule, col_step, num_pair)
            elif col_rule == "outline":     ow    = get_val(col_rule, col_step, ow_pair)

            # Apply row rule (secondary dimension)
            if   row_rule == "shape":       shape = get_val(row_rule, row_step, s_pair)
            elif row_rule == "fill":        fill  = get_val(row_rule, row_step, f_pair)
            elif row_rule == "hatch_level": fill  = get_val(row_rule, row_step, hl_pair)
            elif row_rule == "size":        size  = get_val(row_rule, row_step, sz_pair)
            elif row_rule == "rotation":    rot   = get_val(row_rule, row_step, rot_pair)
            elif row_rule == "count":       count = get_val(row_rule, row_step, cnt_pair)
            elif row_rule == "secondary":   sec   = get_val(row_rule, row_step, sec_pair)
            elif row_rule == "number":      num   = get_val(row_rule, row_step, num_pair)
            elif row_rule == "outline":     ow    = get_val(row_rule, row_step, ow_pair)

            return {
                "shape": shape, "fill": fill, "size": size,
                "rotation": rot, "count": count, "secondary_shape": sec,
                "number": num, "outline_w": ow,
            }

        # 2×2 cells: top-left, top-right, bottom-left, bottom-right (answer)
        cells = [make_cell(0,0), make_cell(1,0),
                 make_cell(0,1), make_cell(1,1)]

        # ── Distractors ───────────────────────────────────────────────────────
        # Four distractors targeting distinct misconceptions; generated while
        # make_cell / pair variables are still in scope.
        #
        # D1  "Column-rule miss"   — undo col_rule; row_rule correct.
        #     Traps students who apply row rule but miss the column change.
        # D2  "Row-rule miss"      — undo row_rule; col_rule correct.
        #     Traps students who apply col rule but miss the row change.
        #     (If no row_rule, gives a size-based near-miss instead.)
        # D3  "Shape confusion"    — correct everything except a different shape.
        #     Traps students who can't identify which shape completes the analogy.
        # D4  "Near miss"          — correct shape + fill, subtle secondary diff.
        #     Traps students who get the main rule right but miss fine detail.

        def _p(base_cell, **overrides):
            """Return a copy of base_cell with the given attribute overrides."""
            d = dict(base_cell)
            d.update(overrides)
            return d

        correct    = cells[-1]
        rule_attrs = {col_rule, row_rule} - {None}

        # D1: undo col_rule attribute
        if   col_rule == "fill":       d1 = _p(correct, fill=f_pair[0])
        elif col_rule == "hatch_level":d1 = _p(correct, fill=hl_pair[0])
        elif col_rule == "shape":      d1 = _p(correct, shape=s_pair[0])
        elif col_rule == "size":       d1 = _p(correct, size=sz_pair[0])
        elif col_rule == "rotation":   d1 = _p(correct, rotation=rot_pair[0])
        elif col_rule == "count":      d1 = _p(correct, count=cnt_pair[0])
        elif col_rule == "secondary":  d1 = _p(correct, secondary_shape=None)
        elif col_rule == "number":     d1 = _p(correct, number=num_pair[0])
        elif col_rule == "outline":    d1 = _p(correct, outline_w=ow_pair[0])
        else:                          d1 = _p(correct)

        # D2: undo row_rule attribute (or shape near-miss when no row_rule)
        if row_rule:
            if   row_rule == "fill":       d2 = _p(correct, fill=f_pair[0])
            elif row_rule == "hatch_level":d2 = _p(correct, fill=hl_pair[0])
            elif row_rule == "shape":      d2 = _p(correct, shape=s_pair[0])
            elif row_rule == "size":       d2 = _p(correct, size=sz_pair[0])
            elif row_rule == "rotation":   d2 = _p(correct, rotation=rot_pair[0])
            elif row_rule == "count":      d2 = _p(correct, count=cnt_pair[0])
            elif row_rule == "secondary":  d2 = _p(correct, secondary_shape=None)
            elif row_rule == "number":     d2 = _p(correct, number=num_pair[0])
            elif row_rule == "outline":    d2 = _p(correct, outline_w=ow_pair[0])
            else:                          d2 = _p(correct)
        else:
            # No row_rule: different shape as second distractor
            alt_sh = next((s for s in self.all_shapes
                           if s != correct.get("shape")), "circle")
            d2 = _p(correct, shape=alt_sh)

        # D3: different shape, everything else the same as correct
        wrong_shapes = [s for s in self.all_shapes if s != correct.get("shape")]
        d3 = _p(correct, shape=random.choice(wrong_shapes[:4]))

        # D4: near-miss — correct shape, one secondary attribute subtly different.
        # Priority: count → size → fill → rotation (last resort only, ≥90° step).
        # Rotation is deprioritised because on a spinning GIF a small angle change
        # is nearly invisible and makes the item a visual-spatial test rather than
        # an inductive-reasoning test.
        if "number" in rule_attrs and correct.get("number") is not None:
            # Number rule is active — near-miss is adjacent digit
            _nums = [1, 2, 3, 4]
            _cur  = correct.get("number", 1)
            _alt  = next((n for n in _nums if n != _cur), 1)
            d4 = _p(correct, number=_alt)
        elif "outline" in rule_attrs:
            # Outline rule — flip to wrong thickness
            d4 = _p(correct, outline_w=ow_pair[0]
                    if correct.get("outline_w") == ow_pair[1] else ow_pair[1])
        elif "count" not in rule_attrs:
            d4 = _p(correct, count=max(1, (correct.get("count", 1) % 3) + 1))
        elif "size" not in rule_attrs:
            sizes = ["small", "medium", "large"]
            d4 = _p(correct, size=sizes[(sizes.index(
                        correct.get("size", "medium")) + 1) % 3])
        elif "fill" not in rule_attrs:
            # Use a clearly different fill — solid ↔ hollow, or swap pattern
            if isinstance(correct.get("fill"), tuple):
                alt_f = "solid"
            else:
                alt_f = "hollow" if correct.get("fill") == "solid" else "solid"
            d4 = _p(correct, fill=alt_f)
        elif ("rotation" not in rule_attrs
              and correct.get("shape") in self.rotatable_shapes):
            # Last resort: rotation with a visible 90° step (never 45°)
            d4 = _p(correct, rotation=(correct.get("rotation", 0) + 90) % 360)
        else:
            # Everything is rule-driven — use a different wrong shape
            _d4_shapes = [s for s in self.all_shapes if s != correct.get("shape")]
            d4 = _p(correct, shape=random.choice(_d4_shapes[:3]))

        distractors = [d1, d2, d3, d4]

        # ── Deduplication guard ───────────────────────────────────────────────
        # Pass 1: ensure no distractor == correct
        _correct_shape = correct.get("shape")
        _used_shapes   = {_correct_shape}
        for _idx, _dist in enumerate(distractors):
            if _dist == correct:
                # Pick a shape not yet used by correct or earlier distractors
                _fb = next(
                    (s for s in self.all_shapes
                     if s not in _used_shapes),
                    next(s for s in self.all_shapes if s != _correct_shape)
                )
                distractors[_idx] = _p(correct, shape=_fb)
                _used_shapes.add(_fb)

        # Pass 2: ensure distractors are mutually distinct (iterate until stable)
        _changed = True
        while _changed:
            _changed = False
            for _i in range(len(distractors)):
                for _j in range(_i + 1, len(distractors)):
                    if distractors[_i] == distractors[_j]:
                        # Collect shapes already spoken for
                        _taken = {_correct_shape}
                        for _k, _d in enumerate(distractors):
                            if _k != _j:
                                _taken.add(_d.get("shape"))
                        _fb = next(
                            (s for s in self.all_shapes if s not in _taken),
                            next(s for s in self.all_shapes
                                 if s != distractors[_j].get("shape"))
                        )
                        distractors[_j] = _p(distractors[_j], shape=_fb)
                        _changed = True

        # Pass 3: rotation-diversity cap — at most 1 distractor may differ from
        # correct ONLY by rotation.  A spinning GIF makes multiple rotation-only
        # variants look nearly identical, turning the item into a visual-spatial
        # test instead of an inductive-reasoning test.
        def _rot_only(dist, ref):
            """True if dist and ref differ in rotation only."""
            return (dist.get("shape") == ref.get("shape")
                    and dist.get("fill")  == ref.get("fill")
                    and dist.get("size")  == ref.get("size")
                    and dist.get("count") == ref.get("count")
                    and dist.get("secondary_shape") == ref.get("secondary_shape")
                    and dist.get("rotation") != ref.get("rotation"))

        _rot_only_indices = [i for i, d in enumerate(distractors)
                             if _rot_only(d, correct)]
        # Keep the first rotation-only distractor; replace any extras with a
        # clearly different shape so the answer strip has visual variety.
        if len(_rot_only_indices) > 1:
            _shape_pool = [s for s in self.all_shapes if s != _correct_shape]
            for _extra in _rot_only_indices[1:]:
                _used_now = {_correct_shape} | {d.get("shape")
                             for k, d in enumerate(distractors) if k != _extra}
                _rep_sh   = next(
                    (s for s in _shape_pool if s not in _used_now),
                    next(s for s in _shape_pool
                         if s != distractors[_extra].get("shape"))
                )
                distractors[_extra] = _p(correct,
                                         shape=_rep_sh,
                                         rotation=correct.get("rotation", 0))

        # ── Spin flag ─────────────────────────────────────────────────────────
        # Items with a rotation rule always spin (the animation illustrates the
        # rule).  Other items spin with a tier-based probability: easy items are
        # mostly static so that early-ability students aren't confused by motion.
        _spin_prob = {"easy": 0.0, "easy_med": 0.20, "medium": 0.45,
                      "hard": 0.65, "very_hard": 0.85, "extreme": 1.0}
        spin = ("rotation" in rules) or (random.random() < _spin_prob.get(tier, 0.5))

        # ── Opposite-spin distractor ──────────────────────────────────────────
        # When the item spins AND rotation is a rule, replace D4 (near-miss)
        # with an opposite-direction-spin variant — same shape/fill/everything
        # but annotated spin_dir=-1 so save_item renders it counter-clockwise.
        if spin and "rotation" in rules:
            distractors[3] = dict(correct, spin_dir=-1)

        # ── Assemble return ───────────────────────────────────────────────────
        rule_axes   = col_rule + ("+" + row_rule if row_rule else "")
        b_estimate  = round(random.uniform(*cfg["b_range"]), 2)
        has_hatch   = any(isinstance(c.get("fill"), tuple) for c in cells)

        return {
            "cells":        cells,
            "distractors":  distractors,
            "distractor_strategy": "col_rule_miss+row_rule_miss+shape_swap+near_miss",
            "grid_size":    2,
            "tier":         tier,
            "b_estimate":   b_estimate,
            "age_range":    cfg["age_range"],
            "n_rules":      len(rules),
            "rule_axes":    rule_axes,
            "shape_types":  base_shape,
            "fill_levels":  str(base_fill),
            "has_secondary": any(c.get("secondary_shape") for c in cells),
            "has_hatch":    has_hatch,
            "spin":         spin,
            "is_multilayer": False,
            "is_subcell":   False,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # LATIN SQUARE HELPER
    # ═══════════════════════════════════════════════════════════════════════════
    # All 12 valid 3×3 Latin squares — precomputed at class level so the
    # generator never repeats the same spatial arrangement.
    _ALL_LATIN_SQUARES = None

    @classmethod
    def _random_latin_square(cls):
        """
        Return one of the 12 distinct 3×3 Latin squares chosen at random.
        Precomputed on first call; subsequent calls are O(1).
        Note: with shapes_3 = random.sample(pool, 3) providing 3! index
        reassignments, the 2 row-0-fixed structures already cover all 12
        arrangements.  Storing all 12 here makes the intent explicit and
        lets the spatial structure itself vary independently of shape choice.
        """
        if cls._ALL_LATIN_SQUARES is None:
            from itertools import permutations as _perms
            valid = []
            for r0 in _perms([0,1,2]):
                for r1 in _perms([0,1,2]):
                    for r2 in _perms([0,1,2]):
                        sq = [list(r0), list(r1), list(r2)]
                        if all(len({sq[r][c] for r in range(3)}) == 3
                               for c in range(3)):
                            valid.append(sq)
            cls._ALL_LATIN_SQUARES = valid   # exactly 12
        return random.choice(cls._ALL_LATIN_SQUARES)

    # ═══════════════════════════════════════════════════════════════════════════
    # ITEM GENERATION — 3×3
    # ═══════════════════════════════════════════════════════════════════════════
    def _gen_3x3(self, tier):
        """
        Generate a 3×3 induction item.
        Standard: Latin-square shape arrangement + secondary rules.
        Extreme:  Multilayer (Q9-type) or Sub-cell (Q10-type).
        """
        cfg = TIERS[tier]
        complexity = cfg["complexity"]

        if tier == "extreme":
            if random.random() < 0.5:
                return self._gen_3x3_multilayer(cfg)
            else:
                return self._gen_3x3_subcell(cfg)

        # ── Secondary rules chosen first so shape pool can react ──────────────
        possible = ["fill", "size", "rotation"]
        if complexity >= 4:
            possible.append("count")
        n_secondary = max(0, cfg["n_rules"] - 1)
        row_rules   = random.sample(possible, min(n_secondary, len(possible)))

        # ── Shape pool: must be rotatable if rotation is a rule ───────────────
        # Fix: need_rot must depend on whether rotation is actually in row_rules,
        # not just complexity — a circle/hexagon with a rotation rule is
        # ambiguous because those shapes look identical at every angle.
        need_rot   = "rotation" in row_rules
        shape_pool = self.rotatable_shapes if need_rot else self.all_shapes
        shapes_3   = random.sample(shape_pool, 3)

        # ── Randomised Latin square (one of 12, not always the same cyclic shift)
        latin = self._random_latin_square()

        # ── Fill sequence (3 values for 3 columns) ────────────────────────────
        # Fix: was hardcoded ["hollow","solid","hollow"] for easy tier, giving a
        # structural tell. Now randomised from a legitimate ordered sequence.
        if complexity <= 2:
            # Easy: two visually distinct solid fills in a randomised order
            seq = random.choice([
                ["hollow", "solid", "hollow"],
                ["solid", "hollow", "solid"],
                ["hollow", "hollow", "solid"],
                ["solid", "solid", "hollow"],
            ])
            fills_3 = seq
        elif complexity <= 4:
            # Medium/Hard: solid + one hatch + solid (randomise position of hatch)
            h = random.choice(self.hatch_fills)
            fills_3 = random.choice([
                ["hollow", h, "solid"],
                [h, "hollow", "solid"],
                ["hollow", "solid", h],
            ])
        else:
            fills_3 = random.sample(self.hatch_fills, 3)

        # ── Ordered sequences — randomise direction so not always ascending ───
        sizes_asc  = ["small", "medium", "large"]
        sizes_3    = sizes_asc if random.random() < 0.5 else list(reversed(sizes_asc))

        rot_base = random.choice([0, 45, 90, 135])
        rot_step = random.choice([90, 120])          # ≥90° so each step is clearly visible
        rots_3   = [rot_base, (rot_base+rot_step)%360, (rot_base+2*rot_step)%360]

        counts_asc = [1, 2, 3]
        counts_3   = counts_asc if random.random() < 0.5 else list(reversed(counts_asc))

        def make_3x3_cell(row, col):
            shape  = shapes_3[latin[row][col]]
            fill   = fills_3[col]   if "fill"     in row_rules else fills_3[0]
            size   = sizes_3[col]   if "size"     in row_rules else "medium"
            rot    = rots_3[col]    if "rotation" in row_rules else 0
            count  = counts_3[col]  if "count"    in row_rules else 1
            return {"shape": shape, "fill": fill, "size": size,
                    "rotation": rot, "count": count}

        cells      = [make_3x3_cell(r, c) for r in range(3) for c in range(3)]

        # ── Distractors ───────────────────────────────────────────────────────
        # Exploit the Latin-square structure to build psychometrically targeted
        # distractors — each one appears plausible by matching a subset of rules.
        #
        # D1  "Wrong column"         — row=2 shape (wrong for that column), wrong
        #     secondary attributes (from col=0).
        #     Traps: "pattern repeats column 0"
        # D2  "Right attributes, wrong shape (top)"  — col=2 secondary attributes
        #     are correct, but the shape is from row 0 of that column.
        #     Traps: "top shape descends into bottom-right"
        # D3  "Right attributes, wrong shape (middle)" — same as D2 but row 1.
        #     Together with D2, these catch students who get the secondary rule
        #     right but can't resolve the Latin-square shape constraint.
        # D4  "Near miss"            — correct shape + primary attribute, one
        #     secondary attribute subtly wrong.

        correct_3 = cells[-1]   # make_3x3_cell(2, 2)

        d1_3 = make_3x3_cell(2, 0)   # wrong column attributes + wrong shape
        d2_3 = make_3x3_cell(0, 2)   # correct col attributes, shape from row 0
        d3_3 = make_3x3_cell(1, 2)   # correct col attributes, shape from row 1

        # D4: near miss of correct — change one secondary attribute.
        # Rotation is last resort because a single-step rotation difference can
        # be almost invisible on a spinning GIF; use 2× the rule step if forced.
        d4_3 = dict(correct_3)
        if "size" in row_rules:
            d4_3["size"] = sizes_3[(sizes_3.index(
                               d4_3.get("size","medium")) + 1) % 3]
        elif "count" in row_rules:
            d4_3["count"] = max(1, (d4_3.get("count", 1) % 3) + 1)
        elif "fill" in row_rules and d4_3.get("fill") in fills_3:
            d4_3["fill"] = fills_3[(fills_3.index(d4_3["fill"]) + 1) % 3]
        elif "rotation" in row_rules:
            # Use 2× the rule step — clearly overshoots the correct rotation
            _rot_step = (rots_3[1] - rots_3[0]) % 360
            d4_3["rotation"] = (d4_3.get("rotation", 0) + 2 * _rot_step) % 360
        else:
            # No secondary rules — change fill
            d4_3["fill"] = ("solid" if d4_3.get("fill") == "hollow" else "hollow")

        distractors = [d1_3, d2_3, d3_3, d4_3]

        # ── Deduplication guard (3×3) ─────────────────────────────────────────
        _correct_shape_3 = correct_3.get("shape")
        _used_shapes_3   = {_correct_shape_3}
        for _idx, _dist in enumerate(distractors):
            if _dist == correct_3:
                _fb = next(
                    (s for s in self.all_shapes if s not in _used_shapes_3),
                    next(s for s in self.all_shapes if s != _correct_shape_3)
                )
                distractors[_idx] = dict(correct_3, shape=_fb)
                _used_shapes_3.add(_fb)

        _changed_3 = True
        while _changed_3:
            _changed_3 = False
            for _i in range(len(distractors)):
                for _j in range(_i + 1, len(distractors)):
                    if distractors[_i] == distractors[_j]:
                        _taken_3 = {_correct_shape_3}
                        for _k, _d in enumerate(distractors):
                            if _k != _j:
                                _taken_3.add(_d.get("shape"))
                        _fb = next(
                            (s for s in self.all_shapes if s not in _taken_3),
                            next(s for s in self.all_shapes
                                 if s != distractors[_j].get("shape"))
                        )
                        distractors[_j] = dict(distractors[_j], shape=_fb)
                        _changed_3 = True

        # ── Spin flag (3×3) ──────────────────────────────────────────────────
        _spin_prob_3 = {"easy": 0.0, "easy_med": 0.20, "medium": 0.45,
                        "hard": 0.65, "very_hard": 0.85, "extreme": 1.0}
        spin_3 = ("rotation" in row_rules) or (
                  random.random() < _spin_prob_3.get(tier, 0.5))

        # Opposite-spin distractor for rotation-rule spinning items
        if spin_3 and "rotation" in row_rules:
            distractors[3] = dict(correct_3, spin_dir=-1)

        # ── Assemble return ───────────────────────────────────────────────────
        rule_axes  = "latin_square" + ("+" + "+".join(row_rules) if row_rules else "")
        b_estimate = round(random.uniform(*cfg["b_range"]), 2)
        has_hatch  = any(isinstance(c.get("fill"), tuple) for c in cells)

        return {
            "cells":        cells,
            "distractors":  distractors,
            "distractor_strategy":
                "col_axis_miss+right_attrs_wrong_shape_r0"
                "+right_attrs_wrong_shape_r1+near_miss",
            "grid_size":    3,
            "tier":         tier,
            "b_estimate":  b_estimate,
            "age_range":   cfg["age_range"],
            "n_rules":     1 + len(row_rules),
            "rule_axes":   rule_axes,
            "shape_types": "|".join(shapes_3),
            "fill_levels": str(fills_3[0]),
            "has_secondary": False,
            "has_hatch":   has_hatch,
            "spin":        spin_3,
            "is_multilayer": False,
            "is_subcell":  False,
        }

    def _gen_3x3_multilayer(self, cfg):
        """
        Q9-type extreme: two overlapping shape layers with independent rules.
        Layer 1 (large, background): shape follows Latin square, fill varies by column.
        Layer 2 (small, foreground): different shape set, fill varies by row, rotation by column.
        """
        shapes_A = random.sample(self.rotatable_shapes, 3)  # layer 1
        shapes_B = random.sample(self.simple_shapes,    3)  # layer 2
        latin = [[0,1,2],[1,2,0],[2,0,1]]

        fills_A = [("lines", "diagonal_tl_br"), "hollow", "solid"]
        fills_B = [("grids", "standard_small"), ("lines", "vertical"), "hollow"]
        rots_A  = [0, 120, 240]   # layer-1 rotation rule: by column
        rots_B  = [0, 90, 180]    # layer-2 rotation rule: by row

        cells = []
        for row in range(3):
            for col in range(3):
                cells.append({
                    "layers": [
                        {   # Background layer — large
                            "shape":    shapes_A[latin[row][col]],
                            "fill":     fills_A[col % 3],
                            "size":     "large",
                            "rotation": rots_A[col],
                            "outline_w": 2.5,
                        },
                        {   # Foreground layer — small
                            "shape":    shapes_B[latin[row][col]],
                            "fill":     fills_B[row % 3],
                            "size":     "small",
                            "rotation": rots_B[row],
                            "outline_w": 2.0,
                        },
                    ]
                })

        # ── Multilayer distractors ────────────────────────────────────────────
        # Correct answer = cells[-1] = make_cell(row=2, col=2)
        # D1: swap layer sizes (foreground ↔ background)
        # D2: correct layer-1 shape+rotation, wrong layer-1 fill (from col 0)
        # D3: correct layer-2 shape+fill, wrong layer-2 rotation (from row 0)
        # D4: near-miss — correct both layers but layer-2 fill from different row

        def _ml_cell(r, c):
            return {"layers": [
                {"shape": shapes_A[latin[r][c]], "fill": fills_A[c%3],
                 "size": "large",  "rotation": rots_A[c], "outline_w": 2.5},
                {"shape": shapes_B[latin[r][c]], "fill": fills_B[r%3],
                 "size": "small",  "rotation": rots_B[r], "outline_w": 2.0},
            ]}

        import copy as _copy

        d_ml1 = _copy.deepcopy(cells[-1])   # swap layer sizes
        d_ml1["layers"][0]["size"] = "small"
        d_ml1["layers"][1]["size"] = "large"

        d_ml2 = _copy.deepcopy(cells[-1])   # layer-1 fill from col 0
        d_ml2["layers"][0]["fill"] = fills_A[0]

        d_ml3 = _copy.deepcopy(cells[-1])   # layer-2 rotation from row 0
        d_ml3["layers"][1]["rotation"] = rots_B[0]

        d_ml4 = _copy.deepcopy(cells[-1])   # layer-2 fill from row 0
        d_ml4["layers"][1]["fill"] = fills_B[0]

        b_estimate = round(random.uniform(*cfg["b_range"]), 2)
        return {
            "cells":        cells,
            "distractors":  [d_ml1, d_ml2, d_ml3, d_ml4],
            "distractor_strategy":
                "layer_size_swap+layer1_fill_wrong+layer2_rot_wrong+layer2_fill_wrong",
            "grid_size":    3,
            "tier":         "extreme",
            "b_estimate":   b_estimate,
            "age_range":    cfg["age_range"],
            "n_rules":      4,
            "rule_axes":    "multilayer+latin_square+rotation_col+fill_row",
            "shape_types":  "|".join(shapes_A) + "|" + "|".join(shapes_B),
            "fill_levels":  "multilayer",
            "has_secondary": False,
            "has_hatch":    True,
            "spin":         True,
            "is_multilayer": True,
            "is_subcell":   False,
        }

    def _gen_3x3_subcell(self, cfg):
        """
        Q10-type extreme: each cell contains a 2×2 sub-grid of mini shapes.
        Rule 1 (count): number of filled sub-cells increases across columns (1→2→3).
        Rule 2 (shift): which sub-cells are filled rotates across rows.
        """
        shape = random.choice(["square", "circle"])
        cells = []
        for row in range(3):
            for col in range(3):
                n_filled = col + 1   # 1, 2, or 3 filled sub-cells
                # Rotate which positions are filled by row
                filled = [(i + row) % 4 for i in range(n_filled)]
                cells.append({
                    "sub_cells": {
                        "shape":          shape,
                        "filled_indices": filled,
                    }
                })

        # ── Subcell distractors ───────────────────────────────────────────────
        # Correct answer: row=2, col=2 → n_filled=3, filled=[2,3,0]
        # D1: "Count-rule miss"  — n_filled=2 (one fewer), correct shift
        # D2: "Shift-rule miss"  — n_filled=3 (correct count), shift=0 (no shift)
        # D3: "Off-by-one shift" — n_filled=3, shift=1 instead of 2
        # D4: "Count+shift both wrong" — n_filled=2, shift=0

        def _sc(nf, shift):
            return {"sub_cells": {"shape": shape,
                                  "filled_indices": [(i+shift)%4
                                                     for i in range(nf)]}}

        correct_n  = 3   # col=2 → n_filled=3
        correct_sh = 2   # row=2 → shift=2

        d_sc1 = _sc(correct_n - 1, correct_sh)     # count miss
        d_sc2 = _sc(correct_n,     0)               # shift miss
        d_sc3 = _sc(correct_n,     (correct_sh + 1) % 4)   # off-by-one shift
        d_sc4 = _sc(correct_n - 1, 0)              # both wrong

        b_estimate = round(random.uniform(*cfg["b_range"]), 2)
        return {
            "cells":        cells,
            "distractors":  [d_sc1, d_sc2, d_sc3, d_sc4],
            "distractor_strategy":
                "count_miss+shift_miss+shift_off_by_one+count_and_shift_wrong",
            "grid_size":    3,
            "tier":         "extreme",
            "b_estimate":   b_estimate,
            "age_range":    cfg["age_range"],
            "n_rules":      3,
            "rule_axes":    "subcell_count+subcell_shift",
            "shape_types":  shape,
            "fill_levels":  "subcell",
            "has_secondary": False,
            "has_hatch":    False,
            "spin":         True,
            "is_multilayer": False,
            "is_subcell":   True,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC ENTRY — generate item data
    # ═══════════════════════════════════════════════════════════════════════════
    def generate_item(self, grid_size, tier):
        if grid_size == 2:
            return self._gen_2x2(tier)
        else:
            return self._gen_3x3(tier)

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDER ITEM  (HD frames + two-pass stable crop)
    # ═══════════════════════════════════════════════════════════════════════════
    def render_item(self, item_data):
        """
        Render item_data → (static_img, q_frames_hd, a_frames_hd).
        Two-pass unified bounding-box crop prevents GIF jumping.
        """
        cells      = item_data["cells"]
        grid_size  = item_data["grid_size"]
        spin       = item_data.get("spin", True)
        num_frames = 60 if spin else 1   # static items: single frame, no animation

        raw_q, raw_a = [], []
        for f in range(num_frames):
            rot_off = (360.0 / 60) * f if spin else 0   # always clockwise
            raw_q.append(self._render_grid(cells, grid_size,
                                           show_answer=False, rot_offset=rot_off))
            raw_a.append(self._render_grid([cells[-1]], 1,
                                           show_answer=True,  rot_offset=rot_off))

        # Static: frame-0 with answer revealed
        static_img = self._render_grid(cells, grid_size, show_answer=True, rot_offset=0)

        # ── Pass 2: unified bounding box ──────────────────────────────────────
        qw, qh = raw_q[0].size
        aw, ah = raw_a[0].size
        INF    = 999999

        min_xq, min_yq, max_xq, max_yq = INF, INF, 0, 0
        min_xa, min_ya, max_xa, max_ya = INF, INF, 0, 0

        for qi, ai in zip(raw_q, raw_a):
            bd_q = ImageOps.invert(qi.convert("RGB")).getbbox()
            bd_a = ImageOps.invert(ai.convert("RGB")).getbbox()
            if bd_q:
                min_xq = min(min_xq, bd_q[0]); min_yq = min(min_yq, bd_q[1])
                max_xq = max(max_xq, bd_q[2]); max_yq = max(max_yq, bd_q[3])
            if bd_a:
                min_xa = min(min_xa, bd_a[0]); min_ya = min(min_ya, bd_a[1])
                max_xa = max(max_xa, bd_a[2]); max_ya = max(max_ya, bd_a[3])

        p = 10   # crop padding
        crop_q = (max(0, min_xq-p), max(0, min_yq-p),
                  min(qw, max_xq+p),  min(qh, max_yq+p))
        crop_a = (max(0, min_xa-p), max(0, min_ya-p),
                  min(aw, max_xa+p),  min(ah, max_ya+p))

        # ── Pass 3: apply unified crop ────────────────────────────────────────
        q_frames = [f.crop(crop_q) for f in raw_q]
        a_frames = [f.crop(crop_a) for f in raw_a]

        return static_img, q_frames, a_frames

    # ═══════════════════════════════════════════════════════════════════════════
    # ANSWER STRIP  (5 options: 4 distractors + 1 correct, randomised position)
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_answer_strip(self, options, rot_offset=0):
        """
        Render 5 answer options (cell_data dicts) in a horizontal strip with
        A B C D E labels centred beneath each option.

        Each option cell is drawn at the same cell_size_hd as grid cells, with
        a thin border, to match the visual weight of the question grid.

        Options may contain a 'spin_dir' key (1 = clockwise, -1 = counter-
        clockwise).  A counter-clockwise option gets −rot_offset so it visually
        spins the opposite direction to the question grid and other options.

        Returns a single HD RGB PIL Image.
        """
        cs      = self.cell_size_hd          # cell size
        bw      = self.border_hd             # cell border width
        gap     = int(16 * self.sf)          # gap between cells
        pad_x   = int(24 * self.sf)          # left/right canvas padding
        pad_y   = int(20 * self.sf)          # top canvas padding
        lbl_h   = int(64 * self.sf)          # space reserved for letter label
        lbl_gap = int(12 * self.sf)          # gap between cell bottom and label

        n       = len(options)               # always 5
        strip_w = 2 * pad_x + n * cs + (n - 1) * gap
        strip_h = pad_y + cs + lbl_gap + lbl_h

        canvas = Image.new("RGB", (strip_w, strip_h), "white")
        draw   = ImageDraw.Draw(canvas)
        labels = ["A", "B", "C", "D", "E"]

        for i, (cell_data, label) in enumerate(zip(options, labels)):
            # Cell top-left corner
            cell_x = pad_x + i * (cs + gap)
            cell_y = pad_y
            cx     = cell_x + cs // 2
            cy     = cell_y + cs // 2

            # Option border (thin, matching outer grid border style)
            draw.rectangle(
                [cell_x, cell_y, cell_x + cs, cell_y + cs],
                outline="black", width=bw
            )

            # Clip content to cell area using a temporary overlay
            # (content drawn directly — border drawn on top keeps edges clean)
            opt_rot = rot_offset * cell_data.get("spin_dir", 1)
            self._draw_cell_content(canvas, cx, cy, cell_data, opt_rot)

            # Redraw border on top so content doesn't bleed over edges
            draw.rectangle(
                [cell_x, cell_y, cell_x + cs, cell_y + cs],
                outline="black", width=bw
            )

            # Letter label centred below cell
            bbox = draw.textbbox((0, 0), label, font=self.font_hd)
            tw   = bbox[2] - bbox[0]
            th   = bbox[3] - bbox[1]
            lx   = cx - tw // 2
            ly   = cell_y + cs + lbl_gap
            draw.text((lx, ly), label, font=self.font_hd, fill="black")

        return canvas

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE ITEM  (static PNG + animated GIFs + choices strip)
    # ═══════════════════════════════════════════════════════════════════════════
    def save_item(self, item_data, item_id, out_root):
        """
        Saves per item:
          _static.png    — full grid with answer revealed (frame 0)
          _question.gif  — animated grid, answer cell shows "?"
          _choices.gif   — animated answer strip: A B C D E options
                           (correct answer in randomised position)

        Returns (folder_name, static_path, q_gif_path, choices_gif_path,
                 correct_letter).
        """
        gs         = item_data["grid_size"]
        tier       = item_data["tier"]
        tier_label = tier.replace("_", "-").title()
        sf         = self.sf

        folder_name = f"Grid_{gs}x{gs}_{tier_label}_{item_id:03d}"
        folder_path = os.path.join(out_root, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # ── Render question grid frames ────────────────────────────────────────
        static_img, q_frames, _ = self.render_item(item_data)

        base   = f"Grid_{gs}x{gs}_{tier_label}_{item_id:03d}"
        s_path = os.path.join(folder_path, f"{base}_static.png")
        q_path = os.path.join(folder_path, f"{base}_question.gif")
        c_path = os.path.join(folder_path, f"{base}_choices.gif")

        # Static PNG
        static_small = static_img.resize(
            (static_img.width // sf, static_img.height // sf),
            Image.Resampling.LANCZOS
        )
        static_small.save(s_path)

        # Question GIF
        q_small = [f.resize((f.width//sf, f.height//sf), Image.Resampling.LANCZOS)
                   for f in q_frames]
        q_small[0].save(q_path, save_all=True, append_images=q_small[1:],
                        duration=30, loop=0)

        # ── Build answer options ───────────────────────────────────────────────
        correct_cell = item_data["cells"][-1]
        distractors  = item_data.get("distractors", [])

        # Ensure we always have exactly 4 distractors
        while len(distractors) < 4:
            distractors.append(dict(correct_cell))   # fallback: copy of correct
        distractors = distractors[:4]

        # Place correct answer in a random position among the 5 slots
        correct_pos    = random.randint(0, 4)
        correct_letter = "ABCDE"[correct_pos]
        options        = list(distractors)           # 4 distractors
        options.insert(correct_pos, correct_cell)    # insert correct at random pos

        # ── Render choices strip ──────────────────────────────────────────────
        # Static items: 1 frame (no animation).  Spinning items: 60 frames,
        # same phase as the question GIF so they feel synchronised.
        spin       = item_data.get("spin", True)
        num_frames = 60 if spin else 1
        raw_choice_frames = []
        for frame in range(num_frames):
            rot_off = (360.0 / 60) * frame if spin else 0
            raw_choice_frames.append(
                self._render_answer_strip(options, rot_offset=rot_off)
            )

        # Two-pass stable crop for choices strip
        sw, sh = raw_choice_frames[0].size
        INF = 999999
        min_x, min_y, max_x, max_y = INF, INF, 0, 0
        for img in raw_choice_frames:
            bd = ImageOps.invert(img.convert("RGB")).getbbox()
            if bd:
                min_x = min(min_x, bd[0]); min_y = min(min_y, bd[1])
                max_x = max(max_x, bd[2]); max_y = max(max_y, bd[3])
        p = 10
        crop_c = (max(0, min_x-p), max(0, min_y-p),
                  min(sw, max_x+p),  min(sh, max_y+p))
        choice_frames = [f.crop(crop_c) for f in raw_choice_frames]

        # Save choices GIF
        c_small = [f.resize((f.width//sf, f.height//sf), Image.Resampling.LANCZOS)
                   for f in choice_frames]
        c_small[0].save(c_path, save_all=True, append_images=c_small[1:],
                        duration=30, loop=0)

        return folder_name, s_path, q_path, c_path, correct_letter


# ═══════════════════════════════════════════════════════════════════════════════
# SPREAD HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def build_spread_jobs(n_items, grid_sizes=None, tiers=None):
    """
    Build a job list with guaranteed even coverage across the full ability
    range and both grid sizes, regardless of how many items are requested.

    Algorithm — round-robin across tiers, balanced grid sizes per round
    -------------------------------------------------------------------
    Each "round" visits every tier exactly once (in a freshly shuffled order),
    so every tier appears before any tier gets a second item.  Grid sizes are
    split as evenly as possible within each round (half 2×2, half 3×3),
    assigned randomly so the spatial mix also varies.  The final list is
    shuffled so the output folder is never sorted by difficulty.

    Guarantees
    ----------
    n ≥ 6  → every tier appears at least once (all 6 tiers covered)
    n ≥ 12 → every tier appears at least twice, both grid sizes for each tier
    n = 1  → one randomly-chosen tier
    n = 3  → 3 distinct tiers, split as evenly as possible across sizes
    """
    if grid_sizes is None:
        grid_sizes = [2, 3]
    if tiers is None:
        tiers = list(TIERS.keys())

    jobs = []
    tiers_work = tiers[:]

    while len(jobs) < n_items:
        random.shuffle(tiers_work)                     # fresh order every round
        n_this_round = min(len(tiers_work), n_items - len(jobs))

        # Assign grid sizes: split the round as evenly as possible
        if len(grid_sizes) == 2:
            half       = n_this_round // 2
            sizes_this = ([grid_sizes[0]] * half +
                          [grid_sizes[1]] * (n_this_round - half))
            random.shuffle(sizes_this)
        else:
            # Only one size specified — use it throughout
            sizes_this = [grid_sizes[0]] * n_this_round

        for tier, gs in zip(tiers_work[:n_this_round], sizes_this):
            jobs.append((gs, tier))

    random.shuffle(jobs)          # shuffle so manifest is not sorted by difficulty
    return jobs


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    gen = NVRGridGenerator()

    print("\nNVR Grid Item Generator  —  v1")
    print("=" * 42)
    print("Default mode: full spread — balanced across ALL tiers and grid sizes.")
    print("Advanced mode: target a specific tier or grid size.\n")

    raw_n   = input("How many items? [default: 12]: ").strip()
    n_items = int(raw_n) if raw_n.isdigit() and int(raw_n) > 0 else 12

    raw_adv = input("Advanced options? (y / n) [default: n]: ").strip().lower()

    tier_names = list(TIERS.keys())

    if raw_adv == "y":
        # ── Advanced: let user narrow down size and/or tier ───────────────────
        print("\nGrid size:")
        print("  0 = 2×2 only")
        print("  1 = 3×3 only")
        print("  2 = Both (default)")
        raw_gs = input("Choice [default: 2]: ").strip()
        if   raw_gs == "0": grid_sizes = [2]
        elif raw_gs == "1": grid_sizes = [3]
        else:               grid_sizes = [2, 3]

        print("\nDifficulty tier:")
        for i, t in enumerate(tier_names):
            cfg = TIERS[t]
            print(f"  {i} = {t:12s}  b ≈ {cfg['b_range']}  age {cfg['age_range']}")
        raw_t = input("Tier number, name, or 'all' [default: all]: ").strip() or "all"

        if raw_t == "all":
            tiers = tier_names
        elif raw_t.isdigit():
            tiers = [tier_names[int(raw_t) % len(tier_names)]]
        elif raw_t in TIERS:
            tiers = [raw_t]
        else:
            tiers = tier_names

        jobs = build_spread_jobs(n_items, grid_sizes=grid_sizes, tiers=tiers)

    else:
        # ── Default: full spread, no further questions ─────────────────────────
        jobs = build_spread_jobs(n_items)

    # ── Summary of what's coming ───────────────────────────────────────────────
    from collections import Counter
    tier_counts = Counter(t for _, t in jobs)
    gs_counts   = Counter(gs for gs, _ in jobs)
    print(f"\nGenerating {n_items} item(s)  →  {OUTPUT_FOLDER}")
    print(f"  Grid sizes : 2×2={gs_counts[2]}  3×3={gs_counts[3]}")
    for t in tier_names:
        if tier_counts[t]:
            cfg = TIERS[t]
            print(f"  {t:12s}: {tier_counts[t]:3d} item(s)  "
                  f"(b ≈ {cfg['b_range']}  age {cfg['age_range']})")
    print()

    manifest_rows = []
    for item_id, (gs, tier) in enumerate(jobs, 1):
        print(f"  [{item_id:3d}/{n_items}]  Grid {gs}×{gs}  |  {tier} ...", end=" ", flush=True)
        item_data = gen.generate_item(gs, tier)
        folder, sp, qp, cp, correct_letter = gen.save_item(
            item_data, item_id, OUTPUT_FOLDER)

        manifest_rows.append({
            "Item_ID":            item_id,
            "Folder":             folder,
            "Grid_Size":          f"{gs}x{gs}",
            "Difficulty_Tier":    tier,
            "Difficulty_Score":   TIERS[tier]["complexity"],
            "b_estimate":         item_data["b_estimate"],
            "Age_Range":          item_data["age_range"],
            "N_Rules":            item_data["n_rules"],
            "Rule_Axes":          item_data["rule_axes"],
            "Correct_Position":   correct_letter,   # which A-E holds correct answer
            "Distractor_Strategy": item_data.get("distractor_strategy", ""),
            "Shape_Types":        item_data["shape_types"],
            "Fill_Levels":        item_data["fill_levels"],
            "Has_Secondary":      item_data["has_secondary"],
            "Has_Hatch":          item_data["has_hatch"],
            "Is_MultiLayer":      item_data["is_multilayer"],
            "Is_SubCell":         item_data["is_subcell"],
            "Static_PNG":         os.path.basename(sp),
            "Question_GIF":       os.path.basename(qp),
            "Choices_GIF":        os.path.basename(cp),
        })
        print("done")

    # Write manifest
    manifest_path = os.path.join(OUTPUT_FOLDER, "manifest.csv")
    if manifest_rows:
        with open(manifest_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=manifest_rows[0].keys())
            writer.writeheader()
            writer.writerows(manifest_rows)

    print(f"\n{'='*42}")
    print(f"Complete.  {n_items} item(s) saved.")
    print(f"Output:    {OUTPUT_FOLDER}")
    print(f"Manifest:  {manifest_path}")
