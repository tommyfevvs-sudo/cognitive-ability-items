import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely.geometry import Polygon
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

def draw_ghost_lines(ax, show_vertical=True, show_horizontal=False):
    """Draws only the requested ghost lines at a low z-order."""
    # Outer Square
    ax.add_patch(patches.Rectangle((0.1, 0.1), 0.8, 0.8, fill=False, linestyle='--', color='gray', lw=0.6, zorder=1))
    
    # Vertical Reference (Middle Fold)
    if show_vertical:
        ax.plot([0.5, 0.5], [0.1, 0.9], color='gray', linestyle='--', lw=0.6, zorder=1)
    
    # Horizontal Reference (The 'Top Line' for the folded triangle/square)
    if show_horizontal:
        # Specifically drawing from 0.5 to 0.9 on the horizontal line at Y=0.5
        ax.plot([0.5, 0.9], [0.5, 0.5], color='gray', linestyle='--', lw=0.6, zorder=1)

def draw_unfolded_paper(ax, base_rect, all_cuts, facecolor, show_fold_lines=True, show_horizontal_ghost=False):
    """Geometrically subtracts cuts and renders clean outlines."""
    x, y, w, h = base_rect
    
    # Draw ghosts as background
    draw_ghost_lines(ax, show_vertical=show_fold_lines, show_horizontal=show_horizontal_ghost)
    
    paper_poly = Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    cut_polys = [Polygon(cut).buffer(0.0001) for cut in all_cuts if len(cut) >= 3]
    
    if cut_polys:
        result_poly = paper_poly.difference(unary_union(cut_polys))
    else:
        result_poly = paper_poly

    if result_poly.is_empty: return
    polys = [result_poly] if result_poly.geom_type == 'Polygon' else list(result_poly.geoms)

    for poly in polys:
        ext_coords = np.array(poly.exterior.coords)
        ax.add_patch(patches.Polygon(ext_coords, facecolor=facecolor, edgecolor='black', lw=0.8, zorder=10))
        for interior in poly.interiors:
            ax.add_patch(patches.Polygon(np.array(interior.coords), facecolor='white', edgecolor='black', lw=0.8, zorder=11))

# --- REFINED SPLINE CUT GENERATOR ---
def generate_precise_corner_cuts(count_input):
    all_cuts = []
    corner_anchors = [(0.5, 0.5), (0.9, 0.1), (0.5, 0.1), (0.9, 0.5)]
    random.shuffle(corner_anchors)
    
    num_cuts = random.randint(1, 3) if count_input == "random" else int(count_input)
    selected = corner_anchors[:num_cuts]

    for cx, cy in selected:
        base_radius = random.uniform(0.12, 0.15)
        spline_amplitude = random.uniform(0.02, 0.035)
        num_waves = random.choice([2, 3, 4])
        
        if cx == 0.5 and cy == 0.5: start, end = 0, -np.pi/2 
        elif cx == 0.9 and cy == 0.1: start, end = np.pi/2, np.pi 
        elif cx == 0.5 and cy == 0.1: start, end = 0, np.pi/2 
        else: start, end = np.pi, 1.5*np.pi 

        cut_points = [[cx, cy]]
        num_pts = 50 
        angles = np.linspace(start, end, num_pts)
        for i, theta in enumerate(angles):
            modulation = np.sin(i / (num_pts - 1) * np.pi * num_waves)
            r = base_radius + (modulation * spline_amplitude)
            px = cx + r * np.cos(theta)
            py = cy + r * np.sin(theta)
            cut_points.append([px, py])
            
        cut_points.append([cx, cy])
        all_cuts.append(cut_points)
            
    return all_cuts, num_cuts

def generate_spatial_files(output_folder, file_name, all_cut_coords, label_mapping):
    PAPER_COLOR, FOLDED_COLOR = '#d6eaf8', '#aed6f1'
    ARROW_STYLE = dict(arrowstyle="->", connectionstyle="arc3,rad=.5", lw=2.0)

    L_horiz, R_horiz = -0.22, 1.22 
    L_vert, R_vert = 0.08, 0.92 

    # 1. Fold Steps
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
            ax.add_patch(patches.Rectangle((0.5, 0.1), 0.4, 0.4, facecolor=FOLDED_COLOR, edgecolor='black', lw=0.75, zorder=10))
            ax.annotate('', xy=(0.7, 0.38), xytext=(0.7, 0.62), arrowprops=ARROW_STYLE, zorder=60)
        draw_ticks(ax)
    buf_f = io.BytesIO(); fig_f.savefig(buf_f, format='png', dpi=300, bbox_inches='tight', pad_inches=0.1); buf_f.seek(0); plt.close(fig_f)

    # 2. Cut Detail
    fig_c = plt.figure(figsize=(4, 4), facecolor='white')
    ax_c = fig_c.add_subplot(111)
    ax_c.set_axis_off(); ax_c.set_xlim(L_horiz, R_horiz); ax_c.set_ylim(L_vert, R_vert); ax_c.set_aspect('equal')
    # show_horizontal_ghost=True added here for the 'top line' under the paper
    draw_unfolded_paper(ax_c, (0.5, 0.1, 0.4, 0.4), all_cut_coords, FOLDED_COLOR, show_fold_lines=True, show_horizontal_ghost=True)
    draw_ticks(ax_c)
    buf_c = io.BytesIO(); fig_c.savefig(buf_c, format='png', dpi=300, bbox_inches='tight', pad_inches=0.05); buf_c.seek(0); plt.close(fig_c)

    # PIL Processing
    img_f, img_c = Image.open(buf_f).convert('RGB'), Image.open(buf_c).convert('RGB')
    wf, wc = img_f.size[0], img_c.size[0]
    final_img_c = Image.new('RGB', (wf, img_c.size[1]), (255, 255, 255))
    final_img_c.paste(img_c, ((wf - wc) // 2, 0))
    img_f.save(os.path.join(output_folder, f"{file_name}_1_folds.png"))
    final_img_c.save(os.path.join(output_folder, f"{file_name}_2_cuts.png"))

    # 3. Alternatives Logic
    q_br = all_cut_coords
    q_bl = [[[1.0 - p[0], p[1]] for p in c] for c in q_br]
    q_tr = [[[p[0], 1.0 - p[1]] for p in c] for c in q_br]
    q_tl = [[[1.0 - p[0], 1.0 - p[1]] for p in c] for c in q_br]
    
    options_data = {
        'Correct': q_br + q_bl + q_tr + q_tl,
        'Half-H': q_br + q_bl, 
        'Half-V': q_br + q_tr, 
        'No-TL': q_br + q_bl + q_tr,
        'Stamping': q_br + [[[p[0]-0.4, p[1]] for p in c] for c in q_br] + \
                    [[[p[0], p[1]+0.4] for p in c] for c in q_br] + \
                    [[[p[0]-0.4, p[1]+0.4] for p in c] for c in q_br]
    }

    fig_a, axes_a = plt.subplots(1, 5, figsize=(18, 5), facecolor='white')
    for i, label in enumerate(['A', 'B', 'C', 'D', 'E']):
        ax = axes_a[i]; ax.set_axis_off(); ax.set_xlim(0.05, 0.95); ax.set_ylim(0.05, 0.95); ax.set_aspect('equal')
        # show_fold_lines=False here removes vertical and horizontal ghosts from answers
        draw_unfolded_paper(ax, (0.1, 0.1, 0.8, 0.8), options_data[label_mapping[label]], PAPER_COLOR, show_fold_lines=False, show_horizontal_ghost=False)
        draw_ticks(ax)
        ax.text(0.5, -0.15, label, fontproperties=custom_font, fontsize=24, ha='center', fontweight='bold', transform=ax.transAxes)
    fig_a.savefig(os.path.join(output_folder, f"{file_name}_3_answers.png"), dpi=300, bbox_inches='tight', pad_inches=0.1); plt.close(fig_a)

# --- EXECUTION ---
num_questions = int(input("How many questions? ") or 1)
cut_count_input = input("How many corners to cut? (1-4, or 'random'): ").lower()

script_dir = os.path.dirname(os.path.abspath(__file__))
main_folder = os.path.join(script_dir, "square_fold_spline_cut")
os.makedirs(main_folder, exist_ok=True)

csv_path = os.path.join(main_folder, "batch_metadata.csv")

batch_id = 1
if os.path.exists(csv_path):
    try:
        with open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            batches = [int(row['Batch']) for row in reader if 'Batch' in row]
            if batches:
                batch_id = max(batches) + 1
    except: pass

file_exists = os.path.isfile(csv_path)
with open(csv_path, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['ID', 'Batch', 'Num_Cuts', 'Ans'])
    
    for i in range(1, num_questions + 1):
        logics = ['Correct', 'Half-H', 'Half-V', 'No-TL', 'Stamping']
        random.shuffle(logics)
        mapping = {label: logic for label, logic in zip(['A', 'B', 'C', 'D', 'E'], logics)}
        cuts, count = generate_precise_corner_cuts(cut_count_input)
        
        unique_id = f"{batch_id}.{i:02d}"
        name = f"spline_item_{unique_id}_{count}cuts"
        item_folder = os.path.join(main_folder, name)
        os.makedirs(item_folder, exist_ok=True)
        
        generate_spatial_files(item_folder, name, cuts, mapping)
        
        ans = [k for k, v in mapping.items() if v == 'Correct'][0]
        writer.writerow([name, batch_id, count, ans])
        print(f"Generated Batch {batch_id}: {name}")

print(f"\nBatch complete. Files saved in: {main_folder}")