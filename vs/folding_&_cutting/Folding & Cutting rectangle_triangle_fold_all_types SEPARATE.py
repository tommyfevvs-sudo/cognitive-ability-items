import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np
import os
import random
import csv
import matplotlib.font_manager as fm
from PIL import Image
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

def draw_ghost_lines(ax):
    ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.6, zorder=1))
    ax.plot([0.5, 0.5], [0.1, 0.9], linestyle='--', color='gray', lw=0.6, zorder=1)
    ax.plot([0.5, 0.9], [0.9, 0.5], linestyle='--', color='gray', lw=0.6, zorder=1)

def draw_unfolded_paper(ax, paper_points, all_cuts, facecolor):
    paper_poly = Polygon(paper_points)
    cut_polys = [Polygon(cut) for cut in all_cuts if len(cut) >= 3]
    if cut_polys:
        result_poly = paper_poly.difference(unary_union(cut_polys))
    else:
        result_poly = paper_poly

    if result_poly.geom_type == 'Polygon': polys = [result_poly]
    elif result_poly.geom_type == 'MultiPolygon': polys = list(result_poly.geoms)
    else: return

    for poly in polys:
        ax.add_patch(patches.Polygon(np.array(poly.exterior.coords), facecolor=facecolor, edgecolor='black', lw=0.8, zorder=10))
        for interior in poly.interiors:
            ax.add_patch(patches.Polygon(np.array(interior.coords), facecolor='white', edgecolor='black', lw=0.8, zorder=11))

# --- GENERATION FACTORY ---
def generate_cuts(mode_input):
    all_cuts = []
    size_label = random.choice(["Medium", "Large"])
    current_mode = mode_input if mode_input != "random" else random.choice(["edge", "corner", "both"])
    current_count = random.randint(1, 4)
    
    # Tracking used locations to prevent overlapping cuts
    used_locations = []

    def get_edge_cut(force_on_flap=False):
        e_size = 0.05 if size_label == "Medium" else 0.07
        s = e_size / 2
        
        flap_edges = ["flap_diag", "flap_bottom", "flap_left"]
        base_edges = ["base_bottom", "base_right", "base_left"]
        
        pool = flap_edges if force_on_flap else (flap_edges + base_edges)
        available = [e for e in pool if e not in used_locations]
        
        # Select from available, or reset if somehow all exhausted
        edge = random.choice(available) if available else random.choice(pool)
        used_locations.append(edge)

        t = random.uniform(0.3, 0.7)
        if edge == "base_bottom":
            x = 0.5 + t * 0.4
            return [[x-s, 0.1], [x, 0.1+e_size], [x+s, 0.1]]
        elif edge == "base_right":
            y = 0.1 + t * 0.4
            return [[0.9, y-s], [0.9-e_size, y], [0.9, y+s]]
        elif edge == "base_left":
            y = 0.1 + t * 0.4
            return [[0.5, y-s], [0.5+e_size, y], [0.5, y+s]]
        elif edge == "flap_bottom": 
            x = 0.5 + t * 0.4
            return [[x-s, 0.5], [x, 0.5+e_size], [x+s, 0.5]]
        elif edge == "flap_left": 
            y = 0.5 + t * 0.4
            return [[0.5, y-s], [0.5+e_size, y], [0.5, y+s]]
        else: # flap_diag
            x = 0.5 + t * 0.4
            y = -x + 1.4
            return [[x-s, y-s], [x-0.05, y-0.05], [x+s, y+s]]

    def get_corner_cut(force_on_flap=False):
        c_size = 0.04 if size_label == "Medium" else 0.06
        # Named dictionary to distinguish specific corner points
        pts_flap = {"f_top": (0.5, 0.9), "f_right": (0.9, 0.5)}
        pts_base = {"b_bottom_l": (0.5, 0.1), "b_bottom_r": (0.9, 0.1)}
        
        pool = pts_flap if force_on_flap else {**pts_flap, **pts_base}
        available = [k for k in pool.keys() if k not in used_locations]
        
        key = random.choice(available) if available else random.choice(list(pool.keys()))
        used_locations.append(key)
        cx, cy = pool[key]
            
        dx = c_size if cx == 0.5 else -c_size
        dy = c_size if cy in [0.1, 0.5] else -c_size
        return [[cx, cy], [cx + dx, cy], [cx, cy + dy]]

    for i in range(current_count):
        must_be_flap = (i == 0) 
        if current_mode == "edge":
            all_cuts.append(get_edge_cut(force_on_flap=must_be_flap))
        elif current_mode == "corner":
            all_cuts.append(get_corner_cut(force_on_flap=must_be_flap))
        else:
            if i == 0: 
                all_cuts.append(get_edge_cut(force_on_flap=True))
            else: 
                func = random.choice([get_edge_cut, get_corner_cut])
                all_cuts.append(func(force_on_flap=False))
            
    return all_cuts, size_label, current_mode, current_count

def generate_spatial_files(output_folder, file_name, all_cut_coords, label_mapping):
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    PAPER_COLOR, FOLDED_COLOR = '#d6eaf8', '#aed6f1'
    ARROW_STYLE = dict(arrowstyle="->", connectionstyle="arc3,rad=.3", lw=2.0)

    L_horiz, R_horiz = -0.22, 1.22 
    L_vert, R_vert = 0.08, 0.92 

    # 1. FOLDS
    fig_f = plt.figure(figsize=(12, 4), facecolor='white')
    plt.subplots_adjust(wspace=0.05)
    for i in range(3):
        ax = plt.subplot(1, 3, i+1); ax.set_axis_off(); ax.set_xlim(L_horiz, R_horiz); ax.set_ylim(L_vert, R_vert); ax.set_aspect('equal')
        draw_ghost_lines(ax)
        if i == 0: 
            ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=PAPER_COLOR, edgecolor='black', lw=0.75, zorder=10))
        elif i == 1: 
            ax.add_patch(patches.Rectangle((0.5, 0.1), 0.4, 0.8, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.annotate('', xy=(0.62, 0.5), xytext=(0.38, 0.5), arrowprops=ARROW_STYLE, zorder=60)
        elif i == 2:
            tri_pts = [[0.5, 0.1], [0.9, 0.1], [0.9, 0.5], [0.5, 0.9]]
            ax.add_patch(patches.Polygon(tri_pts, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.plot([0.5, 0.9], [0.5, 0.5], color='black', lw=1.0, zorder=15)
            ax.annotate('', xy=(0.615, 0.615), xytext=(0.785, 0.785), arrowprops=ARROW_STYLE, zorder=60)
        draw_ticks(ax)
    buf_folds = io.BytesIO()
    fig_f.savefig(buf_folds, format='png', dpi=300, bbox_inches='tight', pad_inches=0.1); buf_folds.seek(0); plt.close(fig_f)

    # 2. CUTS
    fig_c = plt.figure(figsize=(4, 4), facecolor='white'); ax_c = fig_c.add_subplot(111)
    ax_c.set_axis_off(); ax_c.set_xlim(L_horiz, R_horiz); ax_c.set_ylim(L_vert, R_vert); ax_c.set_aspect('equal')
    draw_ghost_lines(ax_c)
    draw_unfolded_paper(ax_c, [[0.5, 0.1], [0.9, 0.1], [0.9, 0.5], [0.5, 0.9]], all_cut_coords, FOLDED_COLOR)
    ax_c.plot([0.5, 0.9], [0.5, 0.5], color='black', lw=1.0, zorder=15)
    draw_ticks(ax_c)
    buf_cuts = io.BytesIO()
    fig_c.savefig(buf_cuts, format='png', dpi=300, bbox_inches='tight', pad_inches=0.05); buf_cuts.seek(0); plt.close(fig_c)

    img_folds, img_cuts = Image.open(buf_folds).convert('RGB'), Image.open(buf_cuts).convert('RGB')
    wf, wc = img_folds.size[0], img_cuts.size[0]
    final_img_cuts = Image.new('RGB', (wf, img_cuts.size[1]), (255, 255, 255))
    final_img_cuts.paste(img_cuts, ((wf - wc) // 2, 0))
    img_folds.save(os.path.join(output_folder, f"{file_name}_1_folds.png"))
    final_img_cuts.save(os.path.join(output_folder, f"{file_name}_2_cuts.png"))

    # 3. ANSWERS
    fig_a, axes_a = plt.subplots(1, 5, figsize=(18, 5), facecolor='white')
    q_all = all_cut_coords
    def reflect_diag(cut):
        return [[0.5 + (0.9 - p[1]), 0.5 + (0.9 - p[0])] for p in cut]
    
    q_v_cuts = [c for c in q_all if any(p[1] >= 0.5 for p in c)]
    q_vertical = q_all + [reflect_diag(c) for c in q_v_cuts]
    q_full = q_vertical + [[[1.0 - p[0], p[1]] for p in c] for c in q_vertical]
    
    options_data = {
        'Correct': q_full, 
        'No-Diag': q_all + [[[1.0 - p[0], p[1]] for p in c] for c in q_all], 
        'Half-V': q_all + [[[p[0], 1.0 - p[1]] for p in c] for c in q_all], 
        'Stamping': q_all + [[[p[0]-0.4, p[1]] for p in c] for c in q_all], 
        'No-Unfold': q_all
    }

    for i, label in enumerate(['A', 'B', 'C', 'D', 'E']):
        ax = axes_a[i]; ax.set_axis_off(); ax.set_xlim(0.05, 0.95); ax.set_ylim(0.05, 0.95); ax.set_aspect('equal')
        ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.6, zorder=1))
        draw_unfolded_paper(ax, [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]], options_data[label_mapping[label]], PAPER_COLOR)
        draw_ticks(ax)
        ax.text(0.5, -0.15, label, fontproperties=custom_font, fontsize=24, ha='center', fontweight='bold', transform=ax.transAxes)
        
    fig_a.savefig(os.path.join(output_folder, f"{file_name}_3_answers.png"), dpi=300, bbox_inches='tight', pad_inches=0.1); plt.close(fig_a)

# --- EXECUTION ---
num_questions_in = input("How many questions? ")
num_questions = int(num_questions_in) if num_questions_in.strip() else 1
cut_mode = input("Cut type? (edge, corner, both, random): ").lower()
if cut_mode not in ["edge", "corner", "both", "random"]: cut_mode = "random"

script_dir = os.path.dirname(os.path.abspath(__file__))
main_folder = os.path.join(script_dir, "Folding & Cutting rectangle_triangle_fold")
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
        logics = ['Correct', 'No-Diag', 'Half-V', 'Stamping', 'No-Unfold']
        random.shuffle(logics)
        mapping = {label: logic for label, logic in zip(['A', 'B', 'C', 'D', 'E'], logics)}
        cuts, size, final_mode, final_count = generate_cuts(cut_mode)
        
        name = f"item_{batch_id}.{i:02d}_{final_mode}_{final_count}cuts"
        item_folder = os.path.join(subfolders[final_mode], name)
        os.makedirs(item_folder, exist_ok=True)
        generate_spatial_files(item_folder, name, cuts, mapping)
        
        writer.writerow([name, batch_id, final_mode, size, [k for k, v in mapping.items() if v == 'Correct'][0]])
        print(f"Generated: {name}")

print(f"\nBatch complete. Files saved in: {main_folder}")