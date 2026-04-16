import os
import io
import base64
import math
from PIL import Image, ImageDraw, ImageFont, ImageChops

# --- CONFIGURATION ---
FPS = 30
DURATION_MS = int(1000 / FPS)
SCALE = 0.5 
EXTRA_CANVAS_HEIGHT = 280 

# Offset set to -250 as requested
STACK_X_OFFSET = -250 
RULE_Y_NUDGE = -4 

# Colors
TEXT_COLOR = (30, 30, 30)
EQUATION_COLOR = (0, 114, 178) 
BG_EXTENSION_COLOR = (255, 255, 255) 

# Item Definitions
NUMBERS = [
    {"in": "12", "out": "17", "op": " + 5 =", "full": "12 + 5 = 17"},
    {"in": "34", "out": "39", "op": " + 5 =", "full": "34 + 5 = 39"},
    {"in": "7",  "out": "12", "op": " + 5 =", "full": "7 + 5 = 12"}
]

# --- TIMINGS PER ROW ---
MOVE_IN_DUR = 35    
BUILD_EQ_DUR = 40   
PAUSE_BEFORE_FLY = 10
MOVE_OUT_DUR = 35   
ROW_GAP = 10        

TIME_PER_ROW = MOVE_IN_DUR + BUILD_EQ_DUR + PAUSE_BEFORE_FLY + MOVE_OUT_DUR + ROW_GAP

# Global Timeline
HOLD_START = 20
ANIM_START = HOLD_START
ALL_ROWS_DONE = ANIM_START + (TIME_PER_ROW * 3)
EMPHASIZE_DUR = 30
HOLD_END = 45
FADE_DUR = 30 
TOTAL_FRAMES = ALL_ROWS_DONE + EMPHASIZE_DUR + HOLD_END + FADE_DUR

# --- HELPER FUNCTIONS ---
def find_font(size):
    font_path = "/Users/thomasfeather/Library/Fonts/Copy of Proxima Soft.otf"
    try: return ImageFont.truetype(font_path, size)
    except: return ImageFont.load_default()

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def lerp(start, end, t):
    return (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)

def color_fade(color, target_bg, t):
    return tuple(int(color[j] + (target_bg[j] - color[j]) * t) for j in range(3))

def get_t(frame, start, duration):
    return max(0.0, min(1.0, (frame - start) / duration))

def process_base_and_coords(base64_data):
    img = Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGB")
    sw, sh = int(img.width * SCALE), int(img.height * SCALE)
    img = img.resize((sw, sh), Image.Resampling.LANCZOS)
    bg = Image.new(img.mode, img.size, BG_EXTENSION_COLOR)
    bbox = ImageChops.difference(img, bg).getbbox()
    crop_t = max(0, bbox[1] - 20) if bbox else 0
    img = img.crop((0, crop_t, sw, (bbox[3] + 20) if bbox else sh))
    canvas = Image.new("RGB", (sw, img.height + EXTRA_CANVAS_HEIGHT), BG_EXTENSION_COLOR)
    canvas.paste(img, (0, 0))
    adj_start = [(320, 280 - crop_t), (480, 320 - crop_t), (380, 360 - crop_t)]
    adj_end = [(1280, 280 - crop_t), (1420, 320 - crop_t), (1320, 360 - crop_t)]
    return canvas, sw, img.height, adj_start, adj_end

def render_frame(f_idx, base_img, sw, ch, adj_start, adj_end):
    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    base_f_size = int(95 * SCALE)
    font = find_font(base_f_size)
    
    # Reset fade timing (for equations and last result)
    t_reset_fade = get_t(f_idx, ALL_ROWS_DONE + EMPHASIZE_DUR + HOLD_END, FADE_DUR)
    
    eq_x_start = (sw // 2) + STACK_X_OFFSET
    
    # 1. Static Elements (Persistent)
    # These stay solid throughout the entire loop
    for i in range(3):
        draw.text(adj_start[i], NUMBERS[i]["in"], font=font, fill=TEXT_COLOR, anchor="mm")
    for i in range(2):
        draw.text(adj_end[i], NUMBERS[i]["out"], font=font, fill=TEXT_COLOR, anchor="mm")
    
    # Question mark handling: Fades out when result arrives, Fades back in at the end
    last_row_fly_start = ANIM_START + (2 * TIME_PER_ROW) + MOVE_IN_DUR + BUILD_EQ_DUR + PAUSE_BEFORE_FLY
    t_q_hide = get_t(f_idx, last_row_fly_start, 10)
    
    if t_reset_fade > 0:
        # Fading back in to reset
        q_col = color_fade(BG_EXTENSION_COLOR, TEXT_COLOR, t_reset_fade)
        draw.text(adj_end[2], "?", font=font, fill=q_col, anchor="mm")
    elif t_q_hide < 1.0:
        # Fading out to make room for result
        q_col = color_fade(TEXT_COLOR, BG_EXTENSION_COLOR, t_q_hide)
        draw.text(adj_end[2], "?", font=font, fill=q_col, anchor="mm")

    # 2. Sequential Animation
    for i in range(3):
        row_start = ANIM_START + (i * TIME_PER_ROW)
        row_y = ch + 60 + (80 * i)
        
        t_in = get_t(f_idx, row_start, MOVE_IN_DUR)
        t_build = get_t(f_idx, row_start + MOVE_IN_DUR, BUILD_EQ_DUR)
        t_out = get_t(f_idx, row_start + MOVE_IN_DUR + BUILD_EQ_DUR + PAUSE_BEFORE_FLY, MOVE_OUT_DUR)

        # STAMP: Equation building (Fades out at end)
        if t_in >= 1.0:
            curr_eq_col = color_fade(EQUATION_COLOR, BG_EXTENSION_COLOR, t_reset_fade)
            if t_build < 0.7:
                op_prog = get_t(f_idx, row_start + MOVE_IN_DUR, BUILD_EQ_DUR * 0.7)
                txt = NUMBERS[i]["in"] + NUMBERS[i]["op"][:int(len(NUMBERS[i]["op"]) * op_prog)]
            else:
                txt = NUMBERS[i]["full"]
            draw.text((eq_x_start, row_y + RULE_Y_NUDGE), txt, font=font, fill=curr_eq_col, anchor="lm")

        # FLYING: Left -> Center (Equation Start)
        if 0 < t_in < 1.0:
            in_w = draw.textlength(NUMBERS[i]['in'], font=font)
            target_in = (eq_x_start + (in_w / 2), row_y + RULE_Y_NUDGE)
            pos = lerp(adj_start[i], target_in, ease_in_out_cubic(t_in))
            draw.text(pos, NUMBERS[i]["in"], font=font, fill=TEXT_COLOR, anchor="mm")

        # FLYING: Center -> Right
        prefix_str = f"{NUMBERS[i]['in']}{NUMBERS[i]['op']} "
        prefix_w = draw.textlength(prefix_str, font=font)
        res_w = draw.textlength(NUMBERS[i]['out'], font=font)
        res_origin = (eq_x_start + prefix_w + (res_w / 2), row_y + RULE_Y_NUDGE)

        if 0 < t_out < 1.0:
            pos = lerp(res_origin, adj_end[i], ease_in_out_cubic(t_out))
            draw.text(pos, NUMBERS[i]["out"], font=font, fill=TEXT_COLOR, anchor="mm")
        elif t_out >= 1.0:
            if i == 2:
                # The final answer "12" fades out at the end
                curr_res_col = color_fade(TEXT_COLOR, BG_EXTENSION_COLOR, t_reset_fade)
                t_e = get_t(f_idx, ALL_ROWS_DONE, EMPHASIZE_DUR)
                eased_t = ease_in_out_cubic(t_e)
                
                # Scaling logic
                s = int(base_f_size * (1.0 + (0.35 * eased_t)))
                
                # Emboldening logic: add a stroke that grows with the emphasis
                curr_stroke = int(2 * eased_t) 
                
                draw.text(adj_end[2], NUMBERS[2]["out"], font=find_font(s), 
                          fill=curr_res_col, anchor="mm",
                          stroke_width=curr_stroke, stroke_fill=curr_res_col)
            else:
                # Row 1 and 2 outputs are already drawn by static block, but ensuring layering
                draw.text(adj_end[i], NUMBERS[i]["out"], font=font, fill=TEXT_COLOR, anchor="mm")

    return img

def main():
    path = os.path.join(os.path.expanduser('~'), 'Desktop', 'NR_NM_template.txt')
    if not os.path.exists(path): return
    with open(path, 'r') as f: data = f.read().strip()
    base, sw, ch, start, end = process_base_and_coords(data)
    frames = [render_frame(i, base, sw, ch, start, end) for i in range(TOTAL_FRAMES)]
    save_p = os.path.join(os.path.expanduser('~'), 'Desktop', "number_machine_tutorial.gif")
    frames[0].save(save_p, save_all=True, append_images=frames[1:], duration=DURATION_MS, loop=0, disposal=2)

if __name__ == "__main__":
    main()