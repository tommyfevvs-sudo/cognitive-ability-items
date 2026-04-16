import numpy as np
import matplotlib.pyplot as plt
import os
import io
from PIL import Image
from matplotlib.colors import LightSource
from matplotlib import font_manager

# --- CONFIGURATION ---
OUTPUT_DIR = os.path.expanduser('~/Desktop/Visual_Spatial_Figures')
STANDARD_AZIM = 50          
STANDARD_ELEV = 30          
BASE_COLOR = '#eeeeee'      
PIECE_COLOR = '#9ACD32'     

# --- FONT SETUP ---
FONT_PATH = '/Users/thomasfeather/Library/Fonts/Proxima Soft Semibold.otf'

try:
    font_manager.fontManager.addfont(FONT_PATH)
    proxima_prop = font_manager.FontProperties(fname=FONT_PATH)
    PROXIMA_FONT = proxima_prop.get_name()
except Exception as e:
    PROXIMA_FONT = 'sans-serif'

# --- SHAPE LOGIC ---
# The front-most L-shape corner piece
CORRECT_COORDS = [(2, 2, 2), (2, 2, 1), (2, 1, 2), (1, 2, 2)]

# Structurally distinct wrong options (Flat shapes so they share a perfect visual baseline)
WRONG_OPTIONS = [
    [(0, 0, 0), (1, 0, 0), (2, 0, 0), (1, 1, 0)], # Option A: T-Shape
    [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], # Option B: 2x2 Square
    [(0, 0, 0), (1, 0, 0), (1, 1, 0), (2, 1, 0)], # Option D: Zig-zag
    [(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0)]  # Option E: Flat L-Shape
]

def draw_shape(ax, coords, color):
    """Draws a 3D shape on the given axis."""
    voxels = np.zeros((3, 3, 3), dtype=bool)
    for c in coords:
        voxels[c[0], c[1], c[2]] = True
        
    dynamic_light = LightSource(azdeg=45 - STANDARD_AZIM, altdeg=45)
    ax.voxels(voxels, facecolors=color, edgecolors='#111111', 
              linewidth=1.0, alpha=1.0, lightsource=dynamic_light, shade=True)
    
    ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.set_zlim(0, 3)
    ax.dist = 7 
    ax.view_init(elev=STANDARD_ELEV, azim=STANDARD_AZIM)
    ax.set_axis_off()

def generate_static_assets():
    print("Generating static example images...")
    
    # --- 1. Static Base ---
    fig_base = plt.figure(figsize=(6, 6))
    ax_base = fig_base.add_subplot(111, projection='3d')
    base_coords = [(x,y,z) for x in range(3) for y in range(3) for z in range(3) if (x,y,z) not in CORRECT_COORDS]
    
    draw_shape(ax_base, base_coords, PIECE_COLOR)
    
    fig_base.canvas.draw()
    tight_bbox = fig_base.get_tightbbox(fig_base.canvas.get_renderer())
    
    height = tight_bbox.height
    ASPECT_RATIO_VAL = 4.0 
    target_width = max(height * ASPECT_RATIO_VAL, tight_bbox.width)
    width_diff = target_width - tight_bbox.width
    
    new_bbox = tight_bbox.expanded(1, 1)
    new_bbox.x0 -= (width_diff / 2); new_bbox.x1 += (width_diff / 2)
    
    base_path = os.path.join(OUTPUT_DIR, "Tutorial_Example_Base.png")
    plt.savefig(base_path, transparent=True, dpi=150, bbox_inches=new_bbox) 
    plt.close(fig_base)

    # --- 2. Static Options Strip ---
    fig_opts, axes = plt.subplots(1, 5, figsize=(25, 5), subplot_kw={'projection': '3d'})
    fig_opts.subplots_adjust(bottom=0.15) 
    labels = ['A', 'B', 'C', 'D', 'E']
    
    shapes = [WRONG_OPTIONS[0], WRONG_OPTIONS[1], CORRECT_COORDS, WRONG_OPTIONS[2], WRONG_OPTIONS[3]]
    
    for i, shape in enumerate(shapes):
        ax = axes[i]
        draw_shape(ax, shape, PIECE_COLOR)
        ax.text2D(0.5, 0.0, labels[i], transform=ax.transAxes, 
                  fontsize=35, fontweight='bold', ha='center', va='top', fontname=PROXIMA_FONT)

    opts_path = os.path.join(OUTPUT_DIR, "Tutorial_Example_Options.png")
    plt.savefig(opts_path, transparent=True, dpi=150, bbox_inches='tight', pad_inches=0.0)
    plt.close(fig_opts)
    
    print("Static images saved.")

def generate_animated_tutorial():
    print("Rendering animation frames (this may take a moment)...")
    
    frames = []
    
    MAIN_RECT = [0.375, 0.38, 0.25, 0.40] 
    OPT_RECTS = [[0.02 + i*0.195, 0.08, 0.175, 0.28] for i in range(5)]
    
    START_RECT = OPT_RECTS[2] 
    END_RECT = MAIN_RECT
    
    steps = 25
    linear_t = np.linspace(0, 1, steps)
    smooth_t = (1 - np.cos(linear_t * np.pi)) / 2  
    
    timeline = np.concatenate([
        smooth_t,           
        np.ones(15),        
        smooth_t[::-1],     
        np.zeros(15)        
    ])

    fig = plt.figure(figsize=(16, 10))
    
    ax_main = fig.add_axes(MAIN_RECT, projection='3d')
    base_coords = [(x,y,z) for x in range(3) for y in range(3) for z in range(3) if (x,y,z) not in CORRECT_COORDS]
    draw_shape(ax_main, base_coords, BASE_COLOR)
    
    labels = ['A', 'B', 'C', 'D', 'E']
    wrong_idx = 0
    for i in range(5):
        ax = fig.add_axes(OPT_RECTS[i], projection='3d')
        if i == 2:
            ax.set_axis_off() 
        else:
            draw_shape(ax, WRONG_OPTIONS[wrong_idx], BASE_COLOR)
            wrong_idx += 1
        
        fig.text(OPT_RECTS[i][0] + (OPT_RECTS[i][2]/2), OPT_RECTS[i][1] - 0.02, labels[i], 
                 fontsize=26, fontweight='bold', ha='center', va='top', fontname=PROXIMA_FONT)

    ax_anim = fig.add_axes(START_RECT, projection='3d')
    draw_shape(ax_anim, CORRECT_COORDS, PIECE_COLOR)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    
    main_bbox_pixels = ax_main.get_tightbbox(renderer)
    main_bbox_inches = main_bbox_pixels.transformed(fig.dpi_scale_trans.inverted())
    composite_bbox = fig.get_tightbbox(renderer)
    
    ASPECT_RATIO_VAL = 4.0
    target_width = main_bbox_inches.height * ASPECT_RATIO_VAL
    
    fixed_bbox = composite_bbox.expanded(1, 1)
    center_x = composite_bbox.x0 + (composite_bbox.width / 2)
    
    fixed_bbox.x0 = center_x - (target_width / 2)
    fixed_bbox.x1 = center_x + (target_width / 2)

    for idx, t in enumerate(timeline):
        current_rect = [
            START_RECT[0] + t * (END_RECT[0] - START_RECT[0]),
            START_RECT[1] + t * (END_RECT[1] - START_RECT[1]),
            START_RECT[2] + t * (END_RECT[2] - START_RECT[2]),
            START_RECT[3] + t * (END_RECT[3] - START_RECT[3])
        ]
        
        ax_anim.set_position(current_rect)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, dpi=150, bbox_inches=fixed_bbox)
        buf.seek(0)
        frames.append(Image.open(buf).copy())
        buf.close()
        
    plt.close(fig)

    gif_path = os.path.join(OUTPUT_DIR, "Tutorial_Master_Animation.gif")
    frames[0].save(
        gif_path, 
        save_all=True, 
        append_images=frames[1:], 
        duration=60, 
        loop=0,       
        disposal=2    
    )
    print(f"Animation saved to: {gif_path}")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generate_static_assets()
    generate_animated_tutorial()
    print("\nAll tutorial assets generated successfully!")