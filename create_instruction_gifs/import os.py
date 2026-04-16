import os
import io
import base64
import math
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
FPS = 30
DURATION_MS = int(1000 / FPS)
SCALE = 0.5 

# We will add 400 pixels of extra space underneath the scaled image
EXTRA_CANVAS_HEIGHT = 400 

# Colors
TEXT_COLOR = (30, 30, 30)
NEW_TEXT_COLOR = (40, 167, 69) # Green flash when rule applies
RULE_COLOR = (220, 53, 69)     # Red for the rule text
BG_EXTENSION_COLOR = (255, 255, 255) # Assuming your template background is white

# Item Definitions
NUMBERS = [
    {"in": "12", "out": "17"},
    {"in": "34", "out": "39"},
    {"in": "7",  "out": "12"}
]

# Scaled coordinates
START_POS = [(300, 300), (450, 320), (350, 360)] 
# Updated to ensure wide separation inside the output box bounds
END_POS = [(1450, 350), (1280, 280), (1380, 320)] 

# Animation Timings (in frames)
HOLD_START = 30       
MOVE_DOWN = 45        
HOLD_MACHINE = 15     
APPLY_RULE = 90       # EXTENDED: 90 frames (3 seconds) to allow 1-by-1 dissolving
HOLD_AFTER_RULE = 30  # EXTENDED: Pause longer to admire the new numbers
MOVE_UP = 45          
HOLD_END = 60         

# --- HELPER FUNCTIONS ---
def find_font(size):
    font_path = "/Users/thomasfeather/Library/Fonts/Copy of Proxima Soft.otf"
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

def ease_in_out_cubic(t):
    if t < 0.5: return 4 * t * t * t
    else: return 1 - math.pow(-2 * t + 2, 3) / 2

def lerp(start, end, t):
    """Linear interpolation for coordinates"""
    return (
        start[0] + (end[0] - start[0]) * t,
        start[1] + (end[1] - start[1]) * t
    )

def color_lerp(c1, c2, t):
    """Linear interpolation for RGB colors to create a 'dissolve' effect"""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[j] + (c2[j] - c1[j]) * t) for j in range(3))

def get_base_image(base64_data):
    """Loads, scales, and extends the base64 template, ensuring NO transparency (RGB)."""
    base_img = Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGB")
    
    scaled_width = int(base_img.width * SCALE)
    scaled_height = int(base_img.height * SCALE)
    base_img = base_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    
    extended_canvas = Image.new("RGB", (scaled_width, scaled_height + EXTRA_CANVAS_HEIGHT), BG_EXTENSION_COLOR)
    extended_canvas.paste(base_img, (0, 0))
    
    return extended_canvas, scaled_width, scaled_height

def render_frame(frame_idx, base_img, scaled_width, scaled_height):
    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    
    font_num = find_font(int(95 * SCALE))
    font_rule = find_font(int(120 * SCALE))
    
    # Global phase progression (0.0 to 1.0)
    t_move_down = max(0, min(1, (frame_idx - HOLD_START) / MOVE_DOWN))
    t_rule = max(0, min(1, (frame_idx - (HOLD_START + MOVE_DOWN + HOLD_MACHINE)) / APPLY_RULE))
    t_move_up = max(0, min(1, (frame_idx - (HOLD_START + MOVE_DOWN + HOLD_MACHINE + APPLY_RULE + HOLD_AFTER_RULE)) / MOVE_UP))
    
    # Vertical stack positions (Underneath the image)
    mid_x = scaled_width // 2 - 100
    mid_y_start = scaled_height + 80
    vertical_spacing = 100
    
    MID_POS = [
        (mid_x, mid_y_start), 
        (mid_x, mid_y_start + vertical_spacing), 
        (mid_x, mid_y_start + (vertical_spacing * 2))
    ]
    
    # Render Rule Text next to the currently active number
    if t_move_down == 1 and t_move_up == 0 and 0 < t_rule < 1:
        # Determine which of the 3 numbers is currently transforming
        active_i = min(2, int(t_rule * 3))
        
        # Calculate local rule time (0.0 to 1.0) just for this specific number's turn
        t_rule_local = (t_rule - (active_i / 3.0)) * 3.0
        
        # Pulse the rule text: fade in to red, fade out to background color
        rule_intensity = math.sin(t_rule_local * math.pi)
        current_rule_color = color_lerp(BG_EXTENSION_COLOR, RULE_COLOR, rule_intensity)
        
        rule_x = mid_x + 200 
        rule_y = MID_POS[active_i][1]
        draw.text((rule_x, rule_y), "+ 5", font=font_rule, fill=current_rule_color, anchor="md")

    # Render Numbers
    for i in range(3):
        # 1. Calculate Position
        if t_move_down < 1:
            eased_t = ease_in_out_cubic(t_move_down)
            pos = lerp(START_POS[i], MID_POS[i], eased_t)
        elif t_move_up > 0:
            eased_t = ease_in_out_cubic(t_move_up)
            pos = lerp(MID_POS[i], END_POS[i], eased_t)
        else:
            pos = MID_POS[i]
            
        # 2. Calculate One-by-One Dissolve Logic
        t_local = max(0.0, min(1.0, (t_rule - (i / 3.0)) * 3.0))
        
        if t_rule == 0:
            # Phase 1: Sitting as old numbers
            val = NUMBERS[i]["in"]
            color = TEXT_COLOR
        elif t_move_up > 0:
            # Phase 3: Moving up, smoothly fade green back to standard dark gray
            val = NUMBERS[i]["out"]
            color = color_lerp(NEW_TEXT_COLOR, TEXT_COLOR, t_move_up)
        else:
            # Phase 2: Active Transformation (Dissolve)
            if t_local < 0.5:
                # First half of local time: Fade old text out into background color
                val = NUMBERS[i]["in"]
                color = color_lerp(TEXT_COLOR, BG_EXTENSION_COLOR, t_local * 2)
            else:
                # Second half of local time: Fade new text in from background color
                val = NUMBERS[i]["out"]
                color = color_lerp(BG_EXTENSION_COLOR, NEW_TEXT_COLOR, (t_local - 0.5) * 2)

        draw.text(pos, val, font=font_num, fill=color, anchor="mm")
        
    return img

def main():
    string_file = os.path.join(os.path.expanduser('~'), 'Desktop', 'NR_NM_template.txt')
    if not os.path.exists(string_file): 
        print(f"Error: {string_file} not found on Desktop.")
        return
        
    with open(string_file, 'r') as f: 
        base64_data = f.read().strip()

    print("Loading and extending base image...")
    base_img, s_width, s_height = get_base_image(base64_data)

    print("Generating frames...")
    frames = []
    total_frames = HOLD_START + MOVE_DOWN + HOLD_MACHINE + APPLY_RULE + HOLD_AFTER_RULE + MOVE_UP + HOLD_END
    
    for i in range(total_frames):
        if i % 10 == 0:
            print(f" - Rendering frame {i}/{total_frames}")
        frames.append(render_frame(i, base_img, s_width, s_height))
        
    print("Saving GIF (this might take a moment)...")
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    save_path = os.path.join(desktop, "number_machine_tutorial.gif")
    
    frames[0].save(
        save_path,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        disposal=2 
    )
    print(f"Done! Saved to {save_path}")

if __name__ == "__main__":
    main()