import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np
import os
import random
import csv
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
import io

# --- FONT CONFIGURATION ---
def get_proxima_soft_paths():
    font_dirs = [
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts",
        "/System/Library/Fonts",
    ]
    for font_dir in font_dirs:
        try:
            fonts = [f for f in os.listdir(font_dir)
                     if 'proxima' in f.lower() and 'soft' in f.lower()
                     and not any(x in f.lower() for x in ['bold', 'italic', 'semibold', 'light', 'black'])
                     and f.lower().endswith(('.ttf', '.otf'))]
            if fonts:
                full_path = os.path.join(font_dir, fonts[0])
                return full_path, fm.FontProperties(fname=full_path)
        except Exception:
            pass
    return None, None

FONT_PATH, custom_font = get_proxima_soft_paths()

def draw_ticks(ax):
    tick_style = {'color': 'black', 'lw': 0.6, 'zorder': 100}
    ax.plot([0.5, 0.5], [0.075, 0.1], **tick_style)
    ax.plot([0.5, 0.5], [0.9, 0.925], **tick_style)
    ax.plot([0.075, 0.1], [0.5, 0.5], **tick_style)
    ax.plot([0.9, 0.925], [0.5, 0.5], **tick_style)

def draw_ghost_lines(ax, show_vertical=True):
    """Draws ghosts for this script's fold logic. Only vertical line if requested."""
    ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.6, zorder=5))
    if show_vertical:
        ax.plot([0.5, 0.5], [0.1, 0.9], linestyle='--', color='gray', lw=0.6, zorder=5)

def draw_unfolded_paper(ax, base_rect, all_cuts, facecolor, is_answer=False):
    """Uses Shapely to geometrically subtract cuts from the paper block."""
    x, y, w, h = base_rect
    
    # Logic to remove internal ghost lines for answers
    if is_answer:
        ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.6, zorder=5))
    else:
        draw_ghost_lines(ax, show_vertical=True)
    
    paper_poly = Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    cut_polys = [Polygon(cut) for cut in all_cuts if len(cut) >= 3]
    
    if cut_polys:
        all_cuts_union = unary_union(cut_polys)
        result_poly = paper_poly.difference(all_cuts_union)
    else:
        result_poly = paper_poly

    if result_poly.geom_type == 'Polygon':
        polys = [result_poly]
    elif result_poly.geom_type == 'MultiPolygon':
        polys = list(result_poly.geoms)
    else: return

    for poly in polys:
        ext_coords = np.array(poly.exterior.coords)
        ax.add_patch(patches.Polygon(ext_coords, facecolor=facecolor, edgecolor='black', lw=0.8, zorder=10))
        for interior in poly.interiors:
            ax.add_patch(patches.Polygon(np.array(interior.coords), facecolor='white', edgecolor='black', lw=0.8, zorder=11))

# --- GENERATION FACTORY ---
def generate_cuts(mode_input, count_input):
    all_cuts = []
    size_label = random.choice(["Medium", "Large"])
    current_mode = mode_input if mode_input != "random" else random.choice(["edge", "corner", "both"])
    
    if count_input == "random":
        current_count = random.randint(1, 4)
    else:
        current_count = max(1, int(count_input))

    # Track available positions to prevent overlapping
    available_edges = [0, 1, 2, 3] # Top, Right, Bottom (Fold), Left
    available_corners = [(0.9, 0.7), (0.5, 0.7), (0.5, 0.1), (0.9, 0.1)] # Flap R, Flap L, Base L, Base R

    for i in range(current_count):
        is_forced_cut = (i == 0) 
        this_cut_type = current_mode
        if current_mode == "both":
            this_cut_type = "edge" if (is_forced_cut or random.random() > 0.5) else "corner"

        if this_cut_type == "edge":
            e_mult = 0.05 if size_label == "Medium" else 0.07
            s, d = e_mult / 2, e_mult
            
            if is_forced_cut:
                edge = 2 # Folded area
            else:
                # Pick an edge that hasn't been used yet if possible
                remaining = [e for e in available_edges if e != 2 or not is_forced_cut]
                edge = random.choice(remaining) if remaining else random.randint(0,3)
            
            if edge in available_edges: available_edges.remove(edge)
            
            pos = random.uniform(0.1, 0.3) if edge in [0, 2] else random.uniform(0.1, 0.5)
            if edge == 0: cut = [[0.5+pos+s, 0.1], [0.5+pos, 0.1+d], [0.5+pos-s, 0.1]]
            elif edge == 1: cut = [[0.9, 0.1+pos-s], [0.9-d, 0.1+pos], [0.9, 0.1+pos+s]]
            elif edge == 2: cut = [[0.5+pos-s, 0.7], [0.5+pos, 0.7-d], [0.5+pos+s, 0.7]] 
            else: cut = [[0.5, 0.1+pos+s], [0.5+d, 0.1+pos], [0.5, 0.1+pos-s]]
            all_cuts.append(cut)
        else: 
            c_size = 0.035 if size_label == "Medium" else 0.05
            if is_forced_cut:
                targets = [(0.9, 0.7), (0.5, 0.7)]
                cx, cy = random.choice(targets)
            else:
                cx, cy = random.choice(available_corners)
            
            if (cx, cy) in available_corners: available_corners.remove((cx, cy))
            
            s1, s2 = c_size * random.uniform(0.6, 1.4), c_size * random.uniform(0.6, 1.4)
            dx, dy = (s1 if cx == 0.5 else -s1), (s2 if cy == 0.1 else -s2)
            off = 0.005
            all_cuts.append([[cx + (-off if cx == 0.5 else off), cy + (-off if cy == 0.1 else off)], [cx + dx, cy], [cx, cy + dy]])
            
    return all_cuts, size_label, current_mode, current_count

def generate_spatial_files(output_folder, file_name, all_cut_coords, label_mapping):
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    PAPER_COLOR, FOLDED_COLOR = '#d6eaf8', '#aed6f1'
    ARROW_STYLE = dict(arrowstyle="->", connectionstyle="arc3,rad=.5", lw=2.0)

    L_horiz, R_horiz = -0.22, 1.22 
    L_vert, R_vert = 0.08, 0.92 

    # 1. FOLDS
    fig_f = plt.figure(figsize=(12, 4), facecolor='white')
    plt.subplots_adjust(wspace=0.05)
    for i in range(3):
        ax = plt.subplot(1, 3, i+1)
        ax.set_axis_off(); ax.set_xlim(L_horiz, R_horiz); ax.set_ylim(L_vert, R_vert); ax.set_aspect('equal')
        if i == 0: 
            draw_ghost_lines(ax, show_vertical=False)
            ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=PAPER_COLOR, edgecolor='black', lw=0.75, zorder=10))
        elif i == 1:
            draw_ghost_lines(ax, show_vertical=True)
            ax.add_patch(patches.Rectangle((0.5, 0.1), 0.4, 0.8, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.annotate('', xy=(0.62, 0.5), xytext=(0.38, 0.5), arrowprops=ARROW_STYLE, zorder=60)
        elif i == 2:
            draw_ghost_lines(ax, show_vertical=True)
            ax.add_patch(patches.Rectangle((0.5, 0.1), 0.4, 0.8, fill=False, linestyle=':', color='gray', lw=0.6, zorder=1))
            ax.add_patch(patches.Rectangle((0.5, 0.1), 0.4, 0.6, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.plot([0.5, 0.9], [0.5, 0.5], color='black', lw=0.75, zorder=15)
            ax.annotate('', xy=(0.7, 0.58), xytext=(0.7, 0.82), arrowprops=ARROW_STYLE, zorder=60)
        draw_ticks(ax)
    
    buf_folds = io.BytesIO()
    fig_f.savefig(buf_folds, format='png', dpi=300, bbox_inches='tight', pad_inches=0.1)
    buf_folds.seek(0); plt.close(fig_f)

    # 2. CUTS
    fig_c = plt.figure(figsize=(4, 4), facecolor='white')
    ax_c = fig_c.add_subplot(111)
    ax_c.set_axis_off(); ax_c.set_xlim(L_horiz, R_horiz); ax_c.set_ylim(L_vert, R_vert); ax_c.set_aspect('equal')
    ax_c.plot([0.5, 0.9], [0.7, 0.7], linestyle='--', color='gray', lw=0.6, zorder=5)
    draw_unfolded_paper(ax_c, (0.5, 0.1, 0.4, 0.6), all_cut_coords, FOLDED_COLOR)
    ax_c.plot([0.5, 0.9], [0.5, 0.5], color='black', lw=0.75, zorder=15)
    draw_ticks(ax_c)
    
    buf_cuts = io.BytesIO()
    fig_c.savefig(buf_cuts, format='png', dpi=300, bbox_inches='tight', pad_inches=0.05)
    buf_cuts.seek(0); plt.close(fig_c)

    # PIL Processing
    img_folds, img_cuts = Image.open(buf_folds).convert('RGB'), Image.open(buf_cuts).convert('RGB')
    wf, wc = img_folds.size[0], img_cuts.size[0]
    final_img_cuts = Image.new('RGB', (wf, img_cuts.size[1]), (255, 255, 255))
    final_img_cuts.paste(img_cuts, ((wf - wc) // 2, 0))
    img_folds.save(os.path.join(output_folder, f"{file_name}_1_folds.png"))
    final_img_cuts.save(os.path.join(output_folder, f"{file_name}_2_cuts.png"))

    # 3. ANSWERS
    fig_a, axes_a = plt.subplots(1, 5, figsize=(18, 5), facecolor='white')
    q_all = all_cut_coords
    q_v_cuts = [c for c in q_all if any(p[1] >= 0.5 for p in c)]
    q_v_mirrored = [[[p[0], 1.4 - p[1]] for p in c] for c in q_v_cuts]
    q_vertical = q_all + q_v_mirrored
    q_full = q_vertical + [[[1.0 - p[0], p[1]] for p in c] for c in q_vertical]
    
    options_data = {'Correct': q_full, 'Half-H': q_vertical, 'Half-V': q_all + [[[1.0 - p[0], p[1]] for p in c] for c in q_all], 'Stamping': q_all + [[[p[0]-0.4, p[1]] for p in c] for c in q_all], 'No-TL': q_all + [[[1-p[0], p[1]] for p in c] for c in q_all] + q_v_mirrored}

    for i, label in enumerate(['A', 'B', 'C', 'D', 'E']):
        ax = axes_a[i]; ax.set_axis_off(); ax.set_xlim(0.05, 0.95); ax.set_ylim(0.05, 0.95); ax.set_aspect('equal')
        draw_unfolded_paper(ax, (0.1, 0.1, 0.8, 0.8), options_data[label_mapping[label]], PAPER_COLOR, is_answer=True)
        draw_ticks(ax)
        ax.text(0.5, -0.15, label, fontproperties=custom_font, fontsize=24, ha='center', fontweight='bold', transform=ax.transAxes)
    fig_a.savefig(os.path.join(output_folder, f"{file_name}_3_answers.png"), dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig_a)

# --- EXECUTION ---
num_questions = int(input("How many questions? ") or 1)
cut_mode = input("Cut type? (edge, corner, both, random): ").lower()
if cut_mode not in ["edge", "corner", "both", "random"]: cut_mode = "random"
cut_count_input = input("How many cuts? (1-4, or 'random'): ").lower()

script_dir = os.path.dirname(os.path.abspath(__file__))
main_folder = os.path.join(script_dir, "Folding & Cutting rectangle_fold")
os.makedirs(main_folder, exist_ok=True)

csv_path = os.path.join(main_folder, "batch_metadata.csv")
batch_id = 1
if os.path.exists(csv_path):
    try:
        with open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            batches = [int(row['Batch']) for row in reader if 'Batch' in row]
            if batches: batch_id = max(batches) + 1
    except: pass

subfolders = {k: os.path.join(main_folder, k.capitalize()) for k in ['edge', 'corner', 'both']}
for f in subfolders.values(): os.makedirs(f, exist_ok=True)

file_exists = os.path.isfile(csv_path)
with open(csv_path, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['ID', 'Batch', 'Mode', 'Size', 'Ans'])
    for i in range(1, num_questions + 1):
        logics = ['Correct', 'Half-H', 'Half-V', 'No-TL', 'Stamping']
        random.shuffle(logics)
        mapping = {label: logic for label, logic in zip(['A', 'B', 'C', 'D', 'E'], logics)}
        cuts, size, final_mode, final_count = generate_cuts(cut_mode, cut_count_input)
        
        name = f"item_{batch_id}.{i:02d}_{final_mode}_{final_count}cuts"
        item_folder = os.path.join(subfolders[final_mode], name)
        os.makedirs(item_folder, exist_ok=True)
        generate_spatial_files(item_folder, name, cuts, mapping)
        
        writer.writerow([name, batch_id, final_mode, size, [k for k, v in mapping.items() if v == 'Correct'][0]])
        print(f"Generated: {name}")

print(f"\nBatch complete. Files saved in: {main_folder}")