import numpy as np
import matplotlib.pyplot as plt
import os
import random
import csv
import io
import subprocess
from PIL import Image
from matplotlib import font_manager
from matplotlib.colors import LightSource
from mpl_toolkits.mplot3d import proj3d

# --- USER INPUT PROMPTS ---
def get_user_config():
    print("--- Visual Spatial Figure Generator ---")
    try:
        total = int(input("How many total items would you like to generate? (e.g., 10): "))
        style = input("Which tiers would you like? (ALL, EASY, MEDIUM, HARD): ").upper()
        grid_input = input("Grid size? (2, 3, 4, or RANDOM): ").strip().upper()
        if grid_input == "RANDOM":
            grid_size = 0  # 0 = sentinel for random per item
        else:
            grid_size = int(grid_input)
            if grid_size not in [2, 3, 4]:
                raise ValueError
    except ValueError:
        print("Invalid input, defaulting to 10 items, ALL, 3x3x3.")
        total, style, grid_size = 10, "ALL", 3
    return total, style, grid_size

TOTAL_ITEMS, TIER_STYLE, GRID_SIZE_CHOICE = get_user_config()
GRID_SIZE = GRID_SIZE_CHOICE if GRID_SIZE_CHOICE != 0 else 3  # fallback for module-level use

# --- CONFIGURATION ---
desktop = os.path.join(os.path.expanduser("~"), 'Desktop')

OUTPUT_DIR = os.path.join(desktop, 'Visual_Spatial_Mixed' if GRID_SIZE_CHOICE == 0 else f'Visual_Spatial_{GRID_SIZE}x{GRID_SIZE}')
ROTATION_PROBABILITY = 0.5 
STANDARD_AZIM = 50 
STANDARD_ELEV = 30 

# --- FONT SETUP ---
def _find_proxima_soft_path():
    font_dirs = [
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts",
        "/System/Library/Fonts",
    ]
    for d in font_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if ('proxima' in f.lower() and 'soft' in f.lower()
                        and not any(x in f.lower() for x in ['bold', 'italic', 'semibold', 'light', 'black'])
                        and f.lower().endswith(('.ttf', '.otf'))):
                    return os.path.join(d, f)
    return None

FONT_PATH = _find_proxima_soft_path()
try:
    font_manager.fontManager.addfont(FONT_PATH)
    proxima_prop = font_manager.FontProperties(fname=FONT_PATH)
    PROXIMA_FONT = proxima_prop.get_name()
except Exception:
    PROXIMA_FONT = 'sans-serif'

# --- SHAPE LOGIC ---

def get_canonical_form(coords):
    def normalize(pts):
        if not pts: return tuple()
        min_x, min_y, min_z = min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts)
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
    return all(0 <= coord < GRID_SIZE for coord in p)

def is_connected_vertex(coords):
    if not coords: return True
    visited, stack = set(), [coords[0]]
    while stack:
        curr = stack.pop()
        if curr not in visited:
            visited.add(curr)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if dx == 0 and dy == 0 and dz == 0: continue
                        nb = (curr[0]+dx, curr[1]+dy, curr[2]+dz)
                        if nb in coords and nb not in visited: stack.append(nb)
    return len(visited) == len(coords)

def generate_tiered_shape(num_blocks, tier):
    max_idx = GRID_SIZE - 1
    # For 2x2x2, we can't be too picky about start_z or it fails
    start_z = max_idx if tier == "EASY" else random.randint(0, max_idx)
    coords = [(random.randint(0, max_idx), random.randint(0, max_idx), start_z)]
    
    attempts = 0
    while len(coords) < num_blocks and attempts < 1000:
        base = random.choice(coords)
        dirs = [(dx, dy, 0) if (tier == "EASY" or GRID_SIZE == 2) else (dx, dy, dz) 
                for dx in [-1,0,1] for dy in [-1,0,1] for dz in [-1,0,1] if not (dx==0 and dy==0 and dz==0)]
        d = random.choice(dirs)
        new_p = (base[0]+d[0], base[1]+d[1], base[2]+d[2])
        if is_within_bounds(new_p) and new_p not in coords:
            # Relax constraints for small grids
            if GRID_SIZE > 2:
                if tier == "EASY" and new_p[2] != start_z: continue 
                if tier == "MEDIUM" and new_p[2] == 0: continue 
            coords.append(new_p)
        attempts += 1
    return sorted(list(set(coords)))

def mutate_shape_connected(original_coords, tier):
    attempts = 0
    # 2x2x2 needs many more attempts to find valid unique mutations
    max_attempts = 1000 if GRID_SIZE == 2 else 400
    while attempts < max_attempts:
        new_coords = list(original_coords)
        idx = random.randint(0, len(new_coords)-1)
        new_coords.pop(idx)
        if is_connected_vertex(new_coords):
            base = random.choice(new_coords)
            added = (base[0]+random.choice([-1,0,1]), base[1]+random.choice([-1,0,1]), base[2]+random.choice([-1,0,1]))
            if is_within_bounds(added) and added not in new_coords:
                new_coords.append(added)
                if is_connected_vertex(new_coords): return sorted(list(set(new_coords)))
        attempts += 1
    return original_coords

def draw_voxels(ax, coords, color, azim_angle=STANDARD_AZIM):
    voxels = np.zeros((GRID_SIZE, GRID_SIZE, GRID_SIZE), dtype=bool)
    for c in coords:
        if is_within_bounds(c): voxels[c[0], c[1], c[2]] = True
    # Dynamic light locked to camera angle so shading stays consistent during rotation
    dynamic_light = LightSource(azdeg=45 - azim_angle, altdeg=45)
    ax.voxels(voxels, facecolors=color, edgecolors='#111111', linewidth=1.5, alpha=1.0, lightsource=dynamic_light, shade=True)
    ax.set_xlim(0, GRID_SIZE); ax.set_ylim(0, GRID_SIZE); ax.set_zlim(0, GRID_SIZE)
    # Zoom adjustment
    ax.dist = 6 if GRID_SIZE == 2 else (7 if GRID_SIZE == 3 else 8)
    ax.view_init(elev=STANDARD_ELEV, azim=azim_angle)
    ax.set_axis_off()

def run_generator():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, "Assessment_Metadata.csv")
    
    batch_id = 1
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                batches = [int(row['Batch']) for row in reader if 'Batch' in row]
                if batches: batch_id = max(batches) + 1
        except Exception: pass

    answer_key, metadata_rows = [], []
    ASPECT_RATIO_VAL = 4.0

    for i in range(1, TOTAL_ITEMS + 1):
        # --- PER-ITEM GRID SIZE (supports RANDOM mode) ---
        global GRID_SIZE
        GRID_SIZE = random.choice([2, 3, 4]) if GRID_SIZE_CHOICE == 0 else GRID_SIZE_CHOICE

        # Block counts depend on current grid size, so compute per item
        if GRID_SIZE == 2:
            counts = {"EASY": 1, "MEDIUM": 2, "HARD": 2} # Only 1-2 pieces removed from 8-block cube
        elif GRID_SIZE == 4:
            counts = {"EASY": 6, "MEDIUM": 10, "HARD": 14} # Out of 64 total blocks
        else:
            counts = {"EASY": 4, "MEDIUM": 6, "HARD": 8} # Out of 27 total blocks

        if TIER_STYLE == "EASY": tier, num_b, color = "EASY", counts["EASY"], '#9ACD32'
        elif TIER_STYLE == "MEDIUM": tier, num_b, color = "MEDIUM", counts["MEDIUM"], '#4DB6AC'
        elif TIER_STYLE == "HARD": tier, num_b, color = "HARD", counts["HARD"], '#F06292'
        else:
            if i <= TOTAL_ITEMS // 3: tier, num_b, color = "EASY", counts["EASY"], '#9ACD32'
            elif i <= (2 * TOTAL_ITEMS) // 3: tier, num_b, color = "MEDIUM", counts["MEDIUM"], '#4DB6AC'
            else: tier, num_b, color = "HARD", counts["HARD"], '#F06292'

        rot_tag = "ROTATED" if random.random() < ROTATION_PROBABILITY else "STANDARD"
        unique_id = f"{batch_id}.{i:02d}"
        item_name = f"item_{unique_id}_{GRID_SIZE}x{GRID_SIZE}_{tier}_{rot_tag}"
        item_folder = os.path.join(OUTPUT_DIR, item_name)
        os.makedirs(item_folder, exist_ok=True)

        correct_coords = generate_tiered_shape(num_b, tier)
        correct_canonical = get_canonical_form(correct_coords)
        layer_type = "Single Layer" if len(set(p[2] for p in correct_coords)) == 1 else "Multi-Layer"

        # --- QUESTION IMAGE (ANIMATED GIF) ---
        fig_q = plt.figure(figsize=(6, 6))
        ax_q = fig_q.add_subplot(111, projection='3d')
        all_coords = [(x,y,z) for x in range(GRID_SIZE) for y in range(GRID_SIZE) for z in range(GRID_SIZE)]
        base_coords = [c for c in all_coords if c not in correct_coords]
        draw_voxels(ax_q, base_coords, color, azim_angle=STANDARD_AZIM)

        fig_q.canvas.draw()
        tight_bbox = fig_q.get_tightbbox(fig_q.canvas.get_renderer())
        width_diff = (tight_bbox.height * ASPECT_RATIO_VAL) - tight_bbox.width
        new_bbox = tight_bbox.expanded(1, 1)
        new_bbox.x0 -= (width_diff / 2); new_bbox.x1 += (width_diff / 2)

        # Generate frames for 360-degree rotation
        frames = []
        for angle in range(0, 360, 10):
            ax_q.clear()
            draw_voxels(ax_q, base_coords, color, azim_angle=angle)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', transparent=True, dpi=150, bbox_inches=new_bbox)
            buf.seek(0)
            frames.append(Image.open(buf).copy())
            buf.close()

        plt.close(fig_q)

        # Save as looping GIF
        gif_path = os.path.join(item_folder, f"{item_name}_Base.gif")
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=133,  # ~7.5 FPS
            loop=0,
            disposal=2
        )

        # --- OPTIONS STRIP ---
        option_angle = random.choice([140, 230, 320]) if rot_tag == "ROTATED" else STANDARD_AZIM
        fig_s, axes = plt.subplots(1, 5, figsize=(25, 6), subplot_kw={'projection': '3d'})
        correct_pos = random.randint(0, 4)
        labels = ['A', 'B', 'C', 'D', 'E']
        answer_key.append(f"Item {unique_id} ({tier}) [{rot_tag}]: {labels[correct_pos]}")
        
        metadata_rows.append({
            'Item_Name': item_name, 'Batch': batch_id, 'Difficulty': tier, 'Is_Rotated': "Yes" if rot_tag == "ROTATED" else "No",
            'Layers': layer_type, 'Block_Count': num_b, 'Correct_Answer': labels[correct_pos]
        })

        used_canonical = [correct_canonical]
        all_shapes_in_item = []
        for idx in range(5):
            ax = axes[idx]
            if idx == correct_pos: current_shape = correct_coords
            else:
                if GRID_SIZE == 2:
                    # For 2x2x2 the canonical-form space is too small to mutate reliably.
                    # Instead, pick a random 1-, 2-, or 3-block configuration from all 8 cells.
                    all_cells = [(x,y,z) for x in range(2) for y in range(2) for z in range(2)]
                    found = False
                    for _ in range(500):
                        count = random.randint(1, 3)
                        cand = sorted(random.sample(all_cells, count))
                        can_id = get_canonical_form(cand)
                        if can_id not in used_canonical:
                            current_shape = cand
                            used_canonical.append(can_id)
                            found = True
                            break
                    if not found:
                        # Absolute fallback: just use any random 1-3 block config
                        count = random.randint(1, 3)
                        current_shape = sorted(random.sample(all_cells, count))
                else:
                    while True:
                        cand = mutate_shape_connected(correct_coords, tier)
                        can_id = get_canonical_form(cand)
                        if can_id not in used_canonical:
                            current_shape = cand
                            used_canonical.append(can_id)
                            break
            all_shapes_in_item.append(current_shape)
            draw_voxels(ax, current_shape, color, azim_angle=option_angle)

        fig_s.canvas.draw()

        # --- VERTICAL ALIGNMENT ---
        # Project the grid floor centre for each subplot and shift all to the same pixel height.
        mid = GRID_SIZE / 2.0
        floor_ys_px = []
        for ax in axes:
            x2d, y2d, _ = proj3d.proj_transform(mid, mid, 0, ax.get_proj())
            _, py = ax.transData.transform((x2d, y2d))
            floor_ys_px.append(py)

        target_py = np.mean(floor_ys_px)
        fig_h_px = fig_s.get_figheight() * fig_s.dpi
        for idx, ax in enumerate(axes):
            shift = (target_py - floor_ys_px[idx]) / fig_h_px
            pos = ax.get_position()
            ax.set_position([pos.x0, pos.y0 + shift, pos.width, pos.height])

        fig_s.canvas.draw()  # re-render after repositioning

        # --- LABELS ---
        # Project every corner of every voxel block across all five shapes to find
        # the true lowest pixel point, then place labels just below that.
        LABEL_BUFFER_PX = 10  # small gap in pixels between lowest voxel edge and label

        global_bottom_px = float('inf')
        subplot_x_centers = []
        for idx, shape in enumerate(all_shapes_in_item):
            ax = axes[idx]
            for (bx, by, bz) in shape:
                for cx in [bx, bx + 1]:
                    for cy in [by, by + 1]:
                        for cz in [bz, bz + 1]:
                            x2d, y2d, _ = proj3d.proj_transform(cx, cy, cz, ax.get_proj())
                            _, py = ax.transData.transform((x2d, y2d))
                            if py < global_bottom_px:
                                global_bottom_px = py
            # X centre: project the grid floor centre for each subplot
            x2d_m, y2d_m, _ = proj3d.proj_transform(mid, mid, 0, ax.get_proj())
            px_m, _ = ax.transData.transform((x2d_m, y2d_m))
            fx_m, _ = fig_s.transFigure.inverted().transform((px_m, 0))
            subplot_x_centers.append(fx_m)

        # Convert pixel baseline to figure coordinates
        label_y_px = global_bottom_px - LABEL_BUFFER_PX
        _, label_fy = fig_s.transFigure.inverted().transform((0, label_y_px))

        for idx in range(5):
            fig_s.text(subplot_x_centers[idx], label_fy, labels[idx],
                       fontsize=35, fontweight='bold', ha='center', va='top',
                       fontname=PROXIMA_FONT)

        plt.savefig(os.path.join(item_folder, f"{item_name}_Options.png"), transparent=True, dpi=300, bbox_inches='tight', pad_inches=0.2)
        plt.close()
        print(f"Exported: {item_name}")

    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=metadata_rows[0].keys())
        if not file_exists: writer.writeheader()
        writer.writerows(metadata_rows)
        
    with open(os.path.join(OUTPUT_DIR, "Answer_Key.txt"), "a") as f:
        f.write("\n" + "\n".join(answer_key))

    print(f"\nComplete! Grid {GRID_SIZE} Batch {batch_id} generated.")
    subprocess.Popen(['open', os.path.realpath(OUTPUT_DIR)])

if __name__ == "__main__":
    run_generator()
