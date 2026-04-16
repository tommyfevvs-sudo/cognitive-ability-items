import os
import random
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
from matplotlib import font_manager
from matplotlib.animation import FuncAnimation, PillowWriter

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
        fig = plt.figure(figsize=(8, 4.5), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1]) 
        ax.set_aspect('equal')
        ax.axis('off')
        
        shapes_metadata = []
        s0_pos = (random.randint(200, 600), 225) 
        # Reduced initial size from 85 to 50
        shapes_metadata.append({'type': types[0], 'pos': s0_pos, 'rot': unique_rots[0], 'path': get_shape_path(types[0], s0_pos, 50, unique_rots[0])})

        all_placed = True
        for i in range(1, num_shapes):
            placed = False
            for _ in range(2000):
                parent = random.choice(shapes_metadata)
                # Scaled down placement distance to match smaller shape size
                angle, dist = random.uniform(0, 2*np.pi), random.uniform(60, 90)
                nx, ny = parent['pos'][0] + dist*np.cos(angle), parent['pos'][1] + dist*np.sin(angle)
                
                if nx < -100 or nx > 900 or ny < -100 or ny > 500: continue
                
                # Reduced shape size from 85 to 50
                npth = get_shape_path(types[i], (nx, ny), 50, unique_rots[i])
                if npth.intersects_path(parent['path'], filled=True):
                    # Scaled down minimum overlap distance
                    if all(np.linalg.norm(np.array([nx, ny]) - np.array(s['pos'])) > 55 for s in shapes_metadata):
                        shapes_metadata.append({'type': types[i], 'pos': (nx, ny), 'rot': unique_rots[i], 'path': npth})
                        placed = True; break
            if not placed: all_placed = False; break
        if all_placed: success = True
        else: plt.close()

    # Find center to shift x-axis
    x_min, x_max = 999, -999
    for s in shapes_metadata:
        ext = s['path'].get_extents()
        x_min, x_max = min(x_min, ext.x0), max(x_max, ext.x1)

    shift_x = 400 - (x_min + x_max) / 2

    patches_list = []
    movement_params = []
    
    true_x_min, true_x_max = 9999.0, -9999.0
    true_y_min, true_y_max = 9999.0, -9999.0
    
    for i, s in enumerate(shapes_metadata):
        final_verts = s['path'].vertices + [shift_x, 0]
        shifted_path = Path(final_verts, s['path'].codes)
        
        p = patches.PathPatch(shifted_path, facecolor=fill_color, edgecolor=edge_color, lw=1.4, zorder=i, joinstyle='miter')
        ax.add_patch(p)
        patches_list.append((p, final_verts))
        
        # Slightly boosted movement to take advantage of the wider space
        ax_move = random.uniform(30, 70)
        ay_move = random.uniform(30, 70)
        
        ext = shifted_path.get_extents()
        
        s_x_min = ext.x0 - ax_move
        s_x_max = ext.x1 + ax_move
        s_y_min = ext.y0 - ay_move
        s_y_max = ext.y1 + ay_move
        
        if s_x_min < true_x_min: true_x_min = s_x_min
        if s_x_max > true_x_max: true_x_max = s_x_max
        if s_y_min < true_y_min: true_y_min = s_y_min
        if s_y_max > true_y_max: true_y_max = s_y_max
            
        movement_params.append({
            'ax': ax_move,                 
            'ay': ay_move,                 
            'fx': random.choice([1, 2]),                   
            'fy': random.choice([1, 2]),                   
            'px': random.uniform(0, 2 * np.pi),            
            'py': random.uniform(0, 2 * np.pi)             
        })

    # --- Precise Cropping Logic ---
    
    # Tight top and bottom padding
    pad_y = 2.0 
    final_y_min = true_y_min - pad_y
    final_y_max = true_y_max + pad_y

    # Restore full 800-unit horizontal canvas to provide movement whitespace
    content_width = true_x_max - true_x_min
    target_width = max(600.0, content_width + 40.0) # Ensures it's always at least 800 wide
    pad_x = (target_width - content_width) / 2.0
    
    final_x_min = true_x_min - pad_x
    final_x_max = true_x_max + pad_x

    ax.set_xlim(final_x_min, final_x_max)
    ax.set_ylim(final_y_min, final_y_max)
    
    # Scale figure dimensions maintaining exactly 100 units = 1 inch
    final_width_units = final_x_max - final_x_min
    final_height_units = final_y_max - final_y_min
    fig.set_size_inches(final_width_units / 100.0, final_height_units / 100.0)

    # --- Animation Setup ---
    frames = 90  
    def update(frame):
        t = (frame / frames) * 2 * np.pi
        
        for (patch_obj, orig_verts), params in zip(patches_list, movement_params):
            dx = params['ax'] * np.sin(params['fx'] * t + params['px'])
            dy = params['ay'] * np.sin(params['fy'] * t + params['py'])
            patch_obj.get_path().vertices = orig_verts + [dx, dy]
            
        return [p for p, _ in patches_list]

    ani = FuncAnimation(fig, update, frames=frames, blit=False)

    rot_label = {"1":"typ-typ", "2":"rnd-rnd", "3":"rnd-typ", "4":"typ-rnd"}.get(rot_mode, "dir")
    base_name = f"{index:03d}_{rot_label}_{style_mode}_s{num_shapes}"
    
    ani.save(f"{output_dir}/{base_name}_puzz.gif", writer=PillowWriter(fps=15))
    plt.close(fig)

    # --- Static Options Setup ---
    MAX_OPTS, SLOT_WIDTH = 5, 150
    TOTAL_WIDTH = MAX_OPTS * SLOT_WIDTH
    fig_opt = plt.figure(figsize=(MAX_OPTS * 2, 2.0), dpi=300)
    ax_opt = fig_opt.add_axes([0, 0, 1, 1]) 
    ax_opt.set_aspect('equal')
    ax_opt.axis('off')
    
    indices = [0] + random.sample(range(1, len(shapes_metadata)), num_options - 1)
    presentation = list(range(len(indices))); random.shuffle(presentation)
    
    start_offset = (TOTAL_WIDTH - (num_options * SLOT_WIDTH)) / 2
    option_paths, option_labels = [], []
    TARGET_Y_CENTER, SHAPE_SIZE = 135, 50 # <-- FIXED THIS LINE
    opt_min_y, opt_max_y = 999, -999

    for i, slot in enumerate(presentation):
        idx = indices[slot]; meta = shapes_metadata[idx]
        o_rot = meta['rot'] if rot_mode in ["2", "dir"] else (random.randint(0, 359) if rot_mode == "4" else 0)
        slot_x_center = start_offset + (SLOT_WIDTH / 2) + (i * SLOT_WIDTH)
        
        temp_path = get_shape_path(meta['type'], (slot_x_center, TARGET_Y_CENTER), SHAPE_SIZE, o_rot)
        ext = temp_path.get_extents()
        offset_y = TARGET_Y_CENTER - (ext.y0 + ext.y1) / 2
        final_path = get_shape_path(meta['type'], (slot_x_center, TARGET_Y_CENTER + offset_y), SHAPE_SIZE, o_rot)
        
        if final_path.get_extents().y0 < opt_min_y: opt_min_y = final_path.get_extents().y0
        if final_path.get_extents().y1 > opt_max_y: opt_max_y = final_path.get_extents().y1
        option_paths.append(final_path); option_labels.append(chr(65 + i))
        if slot == 0: correct_letter = chr(65 + i)

    for i, p_opt in enumerate(option_paths):
        ax_opt.add_patch(patches.PathPatch(p_opt, facecolor=fill_color, edgecolor=edge_color, lw=1.1, joinstyle='miter'))
        ax_opt.text((p_opt.get_extents().x0 + p_opt.get_extents().x1) / 2, opt_min_y - 15, option_labels[i], 
                    fontname=CUSTOM_FONT_NAME, fontsize=14, ha='center', va='top')

    ax_opt.set_xlim(0, TOTAL_WIDTH)
    ax_opt.set_ylim(opt_min_y - 40, opt_max_y + 2)
    
    opt_y_units = (opt_max_y + 2) - (opt_min_y - 40)
    fig_opt.set_size_inches((TOTAL_WIDTH / opt_y_units) * 2.0, 2.0)
    
    plt.savefig(f"{output_dir}/{base_name}_opts.png", transparent=True)
    plt.close()
    
    img_orient = "random" if rot_mode in ["2", "3"] else "typical"
    opt_orient = "random" if rot_mode in ["2", "4"] else "typical"
    if rot_mode == "dir":
        img_orient = opt_orient = "directional"
    
    color_val = f"RGB({int(fill_color[0]*255)},{int(fill_color[1]*255)},{int(fill_color[2]*255)})"

    return [
        base_name,          
        num_shapes,         
        num_options,        
        color_val,          
        img_orient,         
        opt_orient,         
        style_mode,         
        shape_mode,         
        correct_letter      
    ]

if __name__ == "__main__":
    choice = input("Randomised sample? ").lower().strip()
    if choice.startswith('y'):
        total = int(input("Total items? "))
        main_out = os.path.join(os.path.expanduser("~/Desktop"), "VS_layering_moving")
        os.makedirs(main_out, exist_ok=True)
        results = []
        
        print("Generating animations, please wait...")
        for i in range(total):
            s_cnt = random.randint(3, 7)
            sh = random.choice((["all"] * 9) + ["arrow"])
            st = random.choice(VISUAL_STYLES)
            rm = "dir" if sh == "arrow" else random.choice(["1", "2", "3", "4"])
            
            results.append(create_item(i+1, s_cnt, min(5, s_cnt), sh, st, rm, main_out))
            
        with open(os.path.join(main_out, "_key.csv"), "w", newline="") as f:
            header = ["Item Name", "Num Shapes", "Num Options", "Color", "Image Orientation", "Option Orientation", "Style", "Shape Mode", "Correct Answer"]
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(results)
            
    print(f"\nSuccess! Animated GIFs and metadata CSV generated.")