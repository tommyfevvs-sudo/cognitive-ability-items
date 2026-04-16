import numpy as np
import matplotlib.pyplot as plt
import os
import random
import csv  # Added for CSV export
from matplotlib import font_manager
from mpl_toolkits.mplot3d import proj3d

# --- CONFIGURATION ---
OUTPUT_DIR = os.path.expanduser('~/Desktop/Visual_Spatial_Figures')
TOTAL_ITEMS = 45
ROTATION_PROBABILITY = 0.5 
STANDARD_AZIM = 50          
STANDARD_ELEV = 30          

# --- FONT SETUP ---
FONT_PATH = '/Users/thomasfeather/Library/Fonts/Proxima Soft Semibold.otf'

try:
    font_manager.fontManager.addfont(FONT_PATH)
    proxima_prop = font_manager.FontProperties(fname=FONT_PATH)
    PROXIMA_FONT = proxima_prop.get_name()
except Exception as e:
    PROXIMA_FONT = 'sans-serif'

# --- SHAPE LOGIC & DUPLICATE PREVENTION ---

def get_canonical_form(coords):
    """Finds a unique ID for a shape regardless of its 3D rotation."""
    def normalize(pts):
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        min_z = min(p[2] for p in pts)
        return tuple(sorted([(p[0]-min_x, p[1]-min_y, p[2]-min_z) for p in pts]))

    coords = [(c[0], c[1], c[2]) for c in coords]
    rotations = []
    for axes in [(0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)]:
        for sx in [1, -1]:
            for sy in [1, -1]:
                for sz in [1, -1]:
                    if (sx * sy * sz) * (1 if axes in [(0,1,2), (1,2,0), (2,0,1)] else -1) == 1:
                        rotated = [(p[axes[0]]*sx, p[axes[1]]*sy, p[axes[2]]*sz) for p in coords]
                        rotations.append(normalize(rotated))
    return min(rotations)

def is_within_bounds(p):
    return all(0 <= coord <= 2 for coord in p)

def is_connected_vertex(coords):
    if not coords: return True
    visited = set()
    stack = [coords[0]]
    while stack:
        curr = stack.pop()
        if curr not in visited:
            visited.add(curr)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if dx == 0 and dy == 0 and dz == 0: continue
                        nb = (curr[0]+dx, curr[1]+dy, curr[2]+dz)
                        if nb in coords and nb not in visited:
                            stack.append(nb)
    return len(visited) == len(coords)

def generate_tiered_shape(num_blocks, tier):
    start_z = 2 if tier == "EASY" else random.randint(0,2)
    coords = [(random.randint(0,2), random.randint(0,2), start_z)]
    while len(coords) < num_blocks:
        base = random.choice(coords)
        dirs = [(dx, dy, 0) if tier == "EASY" else (dx, dy, dz) for dx in [-1,0,1] for dy in [-1,0,1] for dz in [-1,0,1] if not (dx==0 and dy==0 and dz==0)]
        d = random.choice(dirs)
        new_p = (base[0]+d[0], base[1]+d[1], base[2]+d[2])
        if is_within_bounds(new_p) and new_p not in coords:
            if tier == "EASY" and new_p[2] != start_z: continue 
            if tier == "MEDIUM" and new_p[2] == 0: continue 
            coords.append(new_p)
    return sorted(list(set(coords)))

def mutate_shape_connected(original_coords, tier):
    attempts = 0
    while attempts < 400:
        new_coords = list(original_coords)
        idx = random.randint(0, len(new_coords)-1)
        removed = new_coords.pop(idx)
        if is_connected_vertex(new_coords):
            base = random.choice(new_coords)
            dirs = [(dx, dy, dz) for dx in [-1,0,1] for dy in [-1,0,1] for dz in [-1,0,1] if not (dx==0 and dy==0 and dz==0)]
            added = (base[0]+random.choice([-1,0,1]), base[1]+random.choice([-1,0,1]), base[2]+random.choice([-1,0,1]))
            if is_within_bounds(added) and added not in new_coords:
                new_coords.append(added)
                if is_connected_vertex(new_coords): return sorted(list(set(new_coords)))
        attempts += 1
    return original_coords

def draw_voxels(ax, coords, color, azim_angle=STANDARD_AZIM):
    voxels = np.zeros((3, 3, 3), dtype=bool)
    for c in coords:
        if is_within_bounds(c): voxels[c[0], c[1], c[2]] = True
    ax.voxels(voxels, facecolors=color, edgecolors='#111111', linewidth=1.5, alpha=1.0)
    ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.set_zlim(0, 3)
    ax.dist = 7 # Standardized distance for consistent scale
    ax.view_init(elev=STANDARD_ELEV, azim=azim_angle)
    ax.set_axis_off()

def get_projected_floor_center(ax):
    x2d, y2d, _ = proj3d.proj_transform(1.5, 1.5, 0, ax.get_proj())
    return ax.transData.transform((x2d, y2d))

def run_generator():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    answer_key = []
    metadata_rows = [] # Added for CSV

    # 4.0 ratio ensures significant horizontal whitespace
    ASPECT_RATIO_VAL = 4.0 

    for i in range(1, TOTAL_ITEMS + 1):
        if i <= 15: tier, num_b, color = "EASY", 4, '#9ACD32' 
        elif i <= 30: tier, num_b, color = "MEDIUM", 6, '#4DB6AC'
        else: tier, num_b, color = "HARD", 8, '#F06292'

        rot_tag = "ROTATED" if random.random() < ROTATION_PROBABILITY else "STANDARD"
        item_name = f"{tier}_{i:02d}_{rot_tag}"
        item_folder = os.path.join(OUTPUT_DIR, item_name)
        os.makedirs(item_folder, exist_ok=True)

        correct_coords = generate_tiered_shape(num_b, tier)
        correct_canonical = get_canonical_form(correct_coords)

        # --- ASSESSMENT METADATA CALCULATION ---
        unique_z_layers = len(set(p[2] for p in correct_coords))
        layer_desc = "Single Layer" if unique_z_layers == 1 else "Multi-Layer"

        # --- 1. QUESTION IMAGE ---
        fig_q = plt.figure(figsize=(6, 6)) 
        ax_q = fig_q.add_subplot(111, projection='3d')
        
        all_coords = [(x,y,z) for x in range(3) for y in range(3) for z in range(3)]
        base_coords = [c for c in all_coords if c not in correct_coords]
        draw_voxels(ax_q, base_coords, color, azim_angle=STANDARD_AZIM)
        
        fig_q.canvas.draw()
        tight_bbox = fig_q.get_tightbbox(fig_q.canvas.get_renderer())
        
        height = tight_bbox.height
        target_width = height * ASPECT_RATIO_VAL
        width_diff = target_width - tight_bbox.width
        
        new_bbox = tight_bbox.expanded(1, 1)
        new_bbox.x0 -= (width_diff / 2); new_bbox.x1 += (width_diff / 2)
        
        plt.savefig(os.path.join(item_folder, f"{item_name}_Base.png"), 
                    transparent=True, dpi=300, bbox_inches=new_bbox)
        plt.close()

        # --- 2. OPTIONS STRIP ---
        option_angle = random.choice([140, 230, 320]) if rot_tag == "ROTATED" else STANDARD_AZIM
        fig_s, axes = plt.subplots(1, 5, figsize=(25, 5), subplot_kw={'projection': '3d'})
        correct_pos = random.randint(0, 4)
        labels = ['A', 'B', 'C', 'D', 'E']
        answer_key.append(f"Item {i:02d} ({tier}) [{rot_tag}]: {labels[correct_pos]}")
        
        # Build CSV metadata row
        metadata_rows.append({
            'Item_Name': item_name,
            'Difficulty': tier,
            'Is_Rotated': "Yes" if rot_tag == "ROTATED" else "No",
            'Layers': layer_desc,
            'Block_Count': num_b,
            'Correct_Answer': labels[correct_pos]
        })

        used_canonical_forms = [correct_canonical]; shape_data = []

        for idx in range(5):
            ax = axes[idx]
            if idx == correct_pos: current_shape = correct_coords
            else:
                while True:
                    cand = mutate_shape_connected(correct_coords, tier)
                    can_id = get_canonical_form(cand)
                    if can_id not in used_canonical_forms:
                        current_shape = cand
                        used_canonical_forms.append(can_id)
                        break
            draw_voxels(ax, current_shape, color, azim_angle=option_angle)
            shape_data.append(current_shape)

        fig_s.canvas.draw()
        for idx in range(5):
            ax = axes[idx]
            floor_pix = get_projected_floor_center(ax)
            fig_x, fig_y = fig_s.transFigure.inverted().transform(floor_pix)
            
            fig_s.text(fig_x, fig_y - 0.05, labels[idx], 
                       fontsize=35, fontweight='bold', ha='center', va='top', fontname=PROXIMA_FONT)

        plt.savefig(os.path.join(item_folder, f"{item_name}_Options.png"), 
                    transparent=True, dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        print(f"Exported: {item_name}")

    # --- SAVE METADATA CSV ---
    csv_path = os.path.join(OUTPUT_DIR, "Assessment_Metadata.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=metadata_rows[0].keys())
        writer.writeheader()
        writer.writerows(metadata_rows)

    with open(os.path.join(OUTPUT_DIR, "Answer_Key.txt"), "w") as f:
        f.write("\n".join(answer_key))

if __name__ == "__main__":
    run_generator()