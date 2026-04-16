import os
import random
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
from matplotlib import font_manager

# --- MacOS Font Discovery ---
def find_proxima_soft_macos():
    search_dirs = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts", "/System/Library/Fonts/Supplemental"]
    targets = ["Proxima Soft Semibold.otf", "ProximaSoft-Bold.otf", "Proxima Soft Bold.otf", "proximasoft-bold.otf", "ProximaSoft-Bold.ttf"]
    for directory in search_dirs:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if any(t in filename for t in targets) or "proximasoft" in filename.lower():
                    path = os.path.join(directory, filename)
                    return path if os.path.isfile(path) else None
    return None

FOUND_FONT_PATH = find_proxima_soft_macos()
CUSTOM_FONT_NAME = font_manager.FontProperties(fname=FOUND_FONT_PATH).get_name() if FOUND_FONT_PATH else "sans-serif"

BASE_COLORS = [(173/255, 216/255, 230/255), (255/255, 192/255, 203/255), (180/255, 230/255, 180/255), (255/255, 220/255, 150/255)]
SHAPE_POOL = ["arrow", "pentagon", "trapezoid", "circle", "rect", "square", "hexagon", "triangle", "scalene", "semicircle"]
DIRECTIONAL_SHAPES = ["arrow"]
VISUAL_STYLES = ["color", "monochrome", "outlines"]

def get_shape_path(stype, pos, size, rotation):
    x, y = pos
    if stype == "circle": return Path.circle((x, y), size * 0.82)
    if stype == "semicircle":
        theta = np.linspace(0, np.pi, 50)
        verts = np.column_stack([size * np.cos(theta), size * np.sin(theta)])
    elif stype == "scalene": verts = np.array([[-size, -size*0.4], [size*0.8, -size*0.7], [-size*0.2, size]])
    elif stype == "rect": verts = np.array([[-size, -size*0.5], [size, -size*0.5], [size, size*0.5], [-size, size*0.5]])
    elif stype == "square": verts = np.array([[-size*0.7, -size*0.7], [size*0.7, -size*0.7], [size*0.7, size*0.7], [-size*0.7, size*0.7]])
    elif stype == "triangle": verts = np.array([[0, size * 0.9], [size * 0.8, -size * 0.6], [-size * 0.8, -size * 0.6]])
    elif stype == "hexagon": verts = np.array([[size * 0.9 * np.cos(np.radians(i*60)), size * 0.9 * np.sin(np.radians(i*60))] for i in range(6)])
    elif stype == "pentagon": verts = np.array([[size * 0.9 * np.cos(np.radians(i*72-90)), size * 0.9 * np.sin(np.radians(i*72-90))] for i in range(5)])
    elif stype == "arrow": 
        verts = np.array([[-size, -size*0.2], [0, -size*0.2], [0, -size*0.4], [size, 0], [0, size*0.4], [0, size*0.2], [-size, size*0.2]])
    elif stype == "trapezoid": verts = np.array([[-size, -size*0.5], [size, -size*0.5], [size*0.6, size*0.5], [-size*0.6, size*0.5]])
    
    angle = np.radians(rotation)
    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    rotated_verts = np.dot(verts, R.T) + pos
    return Path(np.concatenate([rotated_verts, [rotated_verts[0]]]), [Path.MOVETO] + [Path.LINETO]*(len(rotated_verts)-1) + [Path.CLOSEPOLY])

def create_item(index, num_shapes, num_options, shape_mode, style_mode, rot_mode, output_dir):
    fill_color = random.choice(BASE_COLORS) if style_mode != "outlines" else (1.0, 1.0, 1.0)
    edge_color = (0, 0, 0)
    
    types = random.sample(SHAPE_POOL, num_shapes) if shape_mode == "all" else [shape_mode] * num_shapes
    unique_rots = [(0 if rot_mode in ["1", "4"] else random.randint(0, 359)) for _ in range(num_shapes)]
    if shape_mode in DIRECTIONAL_SHAPES:
        unique_rots = []
        while len(unique_rots) < num_shapes:
            r = random.randint(15, 345)
            if all(min(abs(r-ex), 360-abs(r-ex)) >= 35 for ex in unique_rots): unique_rots.append(r)

    success = False
    while not success:
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
        ax.set_aspect('equal'); ax.axis('off')
        
        shapes_metadata = []
        s0_pos = (random.randint(150, 650), 225) 
        shapes_metadata.append({'type': types[0], 'pos': s0_pos, 'rot': unique_rots[0], 'path': get_shape_path(types[0], s0_pos, 85, unique_rots[0])})

        all_placed = True
        for i in range(1, num_shapes):
            placed = False
            for _ in range(2000):
                parent = random.choice(shapes_metadata)
                angle, dist = random.uniform(0, 2*np.pi), random.uniform(105, 145)
                nx, ny = parent['pos'][0] + dist*np.cos(angle), parent['pos'][1] + dist*np.sin(angle)
                if nx < 85 or nx > 715 or ny < 50 or ny > 400: continue
                npth = get_shape_path(types[i], (nx, ny), 85, unique_rots[i])
                if npth.intersects_path(parent['path'], filled=True):
                    if all(np.linalg.norm(np.array([nx, ny]) - np.array(s['pos'])) > 90 for s in shapes_metadata):
                        shapes_metadata.append({'type': types[i], 'pos': (nx, ny), 'rot': unique_rots[i], 'path': npth})
                        placed = True; break
            if not placed: all_placed = False; break
        if all_placed: success = True
        else: plt.close()

    y_min, y_max = 999, -999
    for s in shapes_metadata:
        ext = s['path'].get_extents()
        y_min, y_max = min(y_min, ext.y0), max(y_max, ext.y1)

    for i, s in enumerate(shapes_metadata):
        ax.add_patch(patches.PathPatch(s['path'], facecolor=fill_color, edgecolor=edge_color, lw=1.4, zorder=i+1, joinstyle='miter'))

    ax.set_xlim(0, 800)
    ax.set_ylim(y_min - 1.5, y_max + 1.5) 
    
    cluster_height = (y_max + 1.5) - (y_min - 1.5)
    new_fig_height = (cluster_height / 800.0) * 8.0
    fig.set_size_inches(8, new_fig_height)

    rot_label = {"1":"typ-typ", "2":"rnd-rnd", "3":"rnd-typ", "4":"typ-rnd"}.get(rot_mode, "dir")
    base_name = f"{index:03d}_{rot_label}_{style_mode}_s{num_shapes}"
    plt.savefig(f"{output_dir}/{base_name}_puzz.png", transparent=True, pad_inches=0)
    plt.close()

    fig_opt, ax_opt = plt.subplots(figsize=(num_options * 2, 2.0), dpi=300)
    ax_opt.set_aspect('equal'); ax_opt.axis('off')
    indices = [0] + random.sample(range(1, len(shapes_metadata)), num_options - 1)
    presentation = list(range(len(indices))); random.shuffle(presentation)
    
    option_paths, option_labels, global_min_y = [], [], 999
    TARGET_Y_CENTER = 135 
    for i, slot in enumerate(presentation):
        idx = indices[slot]; meta = shapes_metadata[idx]
        o_rot = meta['rot'] if rot_mode in ["2", "dir"] else (random.randint(0, 359) if rot_mode == "4" else 0)
        slot_x_center = 75 + i * 150
        temp_path = get_shape_path(meta['type'], (slot_x_center, TARGET_Y_CENTER), 50, o_rot)
        offset_y = TARGET_Y_CENTER - (temp_path.get_extents().y0 + temp_path.get_extents().y1) / 2
        final_path = get_shape_path(meta['type'], (slot_x_center, TARGET_Y_CENTER + offset_y), 50, o_rot)
        if final_path.get_extents().y0 < global_min_y: global_min_y = final_path.get_extents().y0
        option_paths.append(final_path); option_labels.append(chr(65 + i))
        if slot == 0: correct_letter = chr(65 + i)

    unified_letter_y = global_min_y - 8 
    for i, p_opt in enumerate(option_paths):
        ax_opt.add_patch(patches.PathPatch(p_opt, facecolor=fill_color, edgecolor=edge_color, lw=1.1, joinstyle='miter'))
        ax_opt.text((p_opt.get_extents().x0 + p_opt.get_extents().x1) / 2, unified_letter_y, option_labels[i], 
                    fontname=CUSTOM_FONT_NAME, fontsize=14, ha='center', va='top')

    ax_opt.relim(); ax_opt.autoscale_view()
    plt.savefig(f"{output_dir}/{base_name}_opts.png", bbox_inches='tight', pad_inches=0.05, transparent=True)
    plt.close()
    
    # Logic for descriptive columns
    img_orient = "random" if rot_mode in ["2", "3"] else "typical"
    opt_orient = "random" if rot_mode in ["2", "4"] else "typical"
    if rot_mode == "dir": img_orient = opt_orient = "directional"
    
    color_desc = f"RGB({int(fill_color[0]*255)},{int(fill_color[1]*255)},{int(fill_color[2]*255)})"
    
    return [
        base_name,
        num_shapes,
        num_options,
        color_desc,
        img_orient,
        opt_orient,
        style_mode,
        shape_mode,
        correct_letter,
        f"Shapes_{num_shapes}/{base_name}"
    ]

if __name__ == "__main__":
    choice = input("Randomised sample? ").lower().strip()
    if choice.startswith('y'):
        total = int(input("Total items? "))
        main_out = os.path.join(os.path.expanduser("~/Desktop"), "Layering_Randomised_Selection")
        os.makedirs(main_out, exist_ok=True)
        results = []
        for i in range(total):
            s_cnt = random.randint(3, 7)
            sh = random.choice((["all"] * 9) + ["arrow"])
            st = random.choice(VISUAL_STYLES)
            rm = "dir" if sh == "arrow" else random.choice(["1", "2", "3", "4"])
            
            sub = os.path.join(main_out, f"Shapes_{s_cnt}")
            os.makedirs(sub, exist_ok=True)
            
            results.append(create_item(i+1, s_cnt, min(5, s_cnt), sh, st, rm, sub))
        
        with open(os.path.join(main_out, "_key.csv"), "w", newline="") as f:
            header = ["Item Name", "Num Shapes", "Num Options", "Color", "Image Orientation", "Option Orientation", "Style", "Shape Mode", "Correct Answer", "Path"]
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(results)

    print(f"\nSuccess! Everything is categorized by shape count with detailed CSV.")
