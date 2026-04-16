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

def draw_unfolded_paper(ax, paper_points, all_cuts, facecolor):
    paper_poly = Polygon(paper_points)
    cut_polys = [Polygon(cut).buffer(0.001) for cut in all_cuts if len(cut) >= 3]
    
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
def generate_cuts(mode_input, size_input):
    all_cuts = []
    cut_centers = [] 
    current_size = size_input if size_input != "random" else random.choice(["medium", "large"])
    current_mode = mode_input if mode_input != "random" else random.choice(["edge", "corner", "both"])
    
    # Logic for max cuts: Corner mode only has 3 valid positions (0.1,0.1), (0.9,0.1), (0.5,0.5)
    max_allowed = 3 if current_mode == "corner" else 4
    current_count = random.randint(1, max_allowed)
    
    # Determine sequence of cut types
    types_to_generate = []
    if current_mode == "both":
        current_count = max(2, current_count) 
        types_to_generate = ["edge", "corner"] # Ensure at least one of each
        while len(types_to_generate) < current_count:
            types_to_generate.append(random.choice(["edge", "corner"]))
    else:
        types_to_generate = [current_mode] * current_count

    def get_edge_cut():
        e_size = 0.05 if current_size == "medium" else 0.08
        s = e_size / 2
        edge = random.choice(["bottom", "left_diag", "right_diag"])
        t = random.uniform(0.3, 0.7)
        if edge == "bottom":
            x, y = 0.1 + t * 0.8, 0.09
            return [[x-s, y], [x, y+e_size], [x+s, y]], (x, y)
        elif edge == "left_diag":
            val = 0.1 + t * 0.4
            x, y = val, val
            return [[val-s, val+s], [val+0.04, val-0.04], [val+s, val+s]], (x, y)
        else:
            x = 0.5 + t * 0.4
            y = -x + 1.0
            return [[x-s, y-s], [x+0.04, y+0.04], [x+s, y+s]], (x, y)

    def get_corner_cut(available_corners):
        if not available_corners: return None, None
        c_size = 0.04 if current_size == "medium" else 0.07
        cx, cy = random.choice(available_corners)
        available_corners.remove((cx, cy))
        dx = c_size if cx <= 0.5 else -c_size
        dy = c_size if cy == 0.1 else -c_size
        ox = -0.01 if cx == 0.1 else (0.01 if cx == 0.9 else 0)
        oy = -0.01 if cy == 0.1 else 0
        return [[cx + ox, cy + oy], [cx + dx, cy], [cx, cy + dy]], (cx, cy)

    available_corners = [(0.1, 0.1), (0.9, 0.1), (0.5, 0.5)]

    for cut_type in types_to_generate:
        attempts = 0
        while attempts < 15:
            if cut_type == "edge":
                new_cut, center = get_edge_cut()
            else:
                new_cut, center = get_corner_cut(available_corners)
            
            if new_cut is None: break 

            # Overlap prevention: ensure center is at least 0.15 units away from previous centers
            if all(np.linalg.norm(np.array(center) - np.array(prev)) > 0.15 for prev in cut_centers):
                all_cuts.append(new_cut)
                cut_centers.append(center)
                break
            attempts += 1
            
    return all_cuts, current_size, current_mode, len(all_cuts)

def generate_spatial_files(output_folder, file_name, all_cut_coords, label_mapping):
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    PAPER_COLOR, FOLDED_COLOR = '#d6eaf8', '#aed6f1'
    CURVED_ARROW = dict(arrowstyle="->", connectionstyle="arc3,rad=0.35", lw=2.0)

    L_horiz, R_horiz = -0.22, 1.22 
    L_vert, R_vert = 0.08, 0.92 

    # 1. FOLDS
    fig_f = plt.figure(figsize=(12, 4), facecolor='white')
    plt.subplots_adjust(wspace=0.05)
    for i in range(3):
        ax = plt.subplot(1, 3, i+1); ax.set_axis_off(); ax.set_xlim(L_horiz, R_horiz); ax.set_ylim(L_vert, R_vert); ax.set_aspect('equal')
        # Ghost Perimeter
        ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.5, zorder=1))
        
        if i == 0: 
            ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=PAPER_COLOR, edgecolor='black', lw=0.75, zorder=10))
        elif i == 1:
            pts = [[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]]
            ax.add_patch(patches.Polygon(pts, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.annotate('', xy=(0.41, 0.41), xytext=(0.59, 0.59), arrowprops=CURVED_ARROW, zorder=20)
        elif i == 2:
            ax.plot([0.1, 0.9], [0.9, 0.1], linestyle='--', color='gray', lw=0.6, zorder=1)
            pts = [[0.1, 0.1], [0.9, 0.1], [0.5, 0.5]]
            ax.add_patch(patches.Polygon(pts, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.annotate('', xy=(0.4, 0.2), xytext=(0.2, 0.4), arrowprops=CURVED_ARROW, zorder=20)
        draw_ticks(ax)
    buf_folds = io.BytesIO()
    fig_f.savefig(buf_folds, format='png', dpi=300, bbox_inches='tight', pad_inches=0.1); buf_folds.seek(0); plt.close(fig_f)

    # 2. CUTS
    fig_c = plt.figure(figsize=(4, 4), facecolor='white'); ax_c = fig_c.add_subplot(111)
    ax_c.set_axis_off(); ax_c.set_xlim(L_horiz, R_horiz); ax_c.set_ylim(L_vert, R_vert); ax_c.set_aspect('equal')
    ax_c.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.5, zorder=1))
    ax_c.plot([0.1, 0.9], [0.9, 0.1], linestyle='--', color='gray', lw=0.6, zorder=1)
    ax_c.plot([0.5, 0.1], [0.5, 0.1], linestyle='--', color='gray', lw=0.6, zorder=1)

    draw_unfolded_paper(ax_c, [[0.1, 0.1], [0.9, 0.1], [0.5, 0.5]], all_cut_coords, FOLDED_COLOR)
    draw_ticks(ax_c)
    buf_cuts = io.BytesIO()
    fig_c.savefig(buf_cuts, format='png', dpi=300, bbox_inches='tight', pad_inches=0.05); buf_cuts.seek(0); plt.close(fig_c)

    # PIL Processing
    img_folds, img_cuts = Image.open(buf_folds).convert('RGB'), Image.open(buf_cuts).convert('RGB')
    w_folds, h_folds = img_folds.size
    w_cuts, h_cuts = img_cuts.size
    final_img_cuts = Image.new('RGB', (w_folds, h_cuts), (255, 255, 255))
    final_img_cuts.paste(img_cuts, ((w_folds - w_cuts) // 2, 0))
    img_folds.save(os.path.join(output_folder, f"{file_name}_1_folds.png"))
    final_img_cuts.save(os.path.join(output_folder, f"{file_name}_2_cuts.png"))

    # 3. ANSWERS
    q_final = all_cut_coords
    def reflect_fold2(cut): return [[1.0 - p[1], 1.0 - p[0]] for p in cut]
    def reflect_fold1(cut): return [[p[1], p[0]] for p in cut]
    q_correct = q_final + [reflect_fold2(c) for c in q_final]
    q_correct = q_correct + [reflect_fold1(c) for c in q_correct]
    q_dist1 = q_final + [reflect_fold2(c) for c in q_final]
    q_dist2 = q_final + [[[p[0], 1.0-p[1]] for p in c] for c in q_final]
    q_dist2 = q_dist2 + [[[1.0-p[0], p[1]] for p in c] for c in q_dist2]
    q_misplaced = [[ [p[0]+0.1, p[1]+0.1] for p in c] for c in q_correct]
    q_rotated = [[ [1.0-p[1], p[0]] for p in c] for c in q_correct]

    options_data = {'Correct': q_correct, 'Simple': q_dist1, 'Cartesian': q_dist2, 'Misplaced': q_misplaced, 'Rotated': q_rotated}

    fig_a, axes_a = plt.subplots(1, 5, figsize=(18, 5), facecolor='white')
    for i, label in enumerate(['A', 'B', 'C', 'D', 'E']):
        ax = axes_a[i]; ax.set_axis_off(); ax.set_xlim(0.05, 0.95); ax.set_ylim(0.05, 0.95); ax.set_aspect('equal')
        ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.5, zorder=1))
        draw_unfolded_paper(ax, [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]], options_data[label_mapping[label]], PAPER_COLOR)
        draw_ticks(ax)
        ax.text(0.5, -0.15, label, fontproperties=custom_font, fontsize=24, ha='center', fontweight='bold', transform=ax.transAxes)
    fig_a.savefig(os.path.join(output_folder, f"{file_name}_3_answers.png"), dpi=300, bbox_inches='tight', pad_inches=0.1); plt.close(fig_a)

# --- EXECUTION ---
num_questions = int(input("How many questions? ") or 1)
cut_mode = input("Cut type? (edge, corner, both, random): ").lower()
cut_size_input = input("Cut size? (medium, large, random): ").lower()

script_dir = os.path.dirname(os.path.abspath(__file__))
main_folder = os.path.join(script_dir, "Folding & Cutting double_triangle_fold")
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
for folder in subfolders.values(): os.makedirs(folder, exist_ok=True)

file_exists = os.path.isfile(csv_path)
with open(csv_path, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['ID', 'Batch', 'Mode', 'Size', 'Ans', 'Cuts'])
        
    for i in range(1, num_questions + 1):
        logics = ['Correct', 'Simple', 'Cartesian', 'Misplaced', 'Rotated']
        random.shuffle(logics)
        mapping = {label: logic for label, logic in zip(['A', 'B', 'C', 'D', 'E'], logics)}
        cuts, size, final_mode, final_count = generate_cuts(cut_mode, cut_size_input)
        
        unique_id = f"{batch_id}.{i:02d}"
        name = f"item_{unique_id}_{final_mode}_{final_count}cuts"
        item_folder = os.path.join(subfolders[final_mode], name)
        os.makedirs(item_folder, exist_ok=True)
        
        generate_spatial_files(item_folder, name, cuts, mapping)
        
        ans_letter = [k for k, v in mapping.items() if v == 'Correct'][0]
        writer.writerow([name, batch_id, final_mode, size, ans_letter, final_count])
        print(f"Generated Batch {batch_id}: {name}")

print(f"\nBatch complete. Files saved in: {main_folder}")