import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont, ImageChops

# --- CONFIGURATION ---
SCALE = 0.5 

# Colors
TEXT_COLOR = (30, 30, 30)
BG_EXTENSION_COLOR = (255, 255, 255)

# Item Definitions
NUMBERS = [
    {"in": "12", "out": "17"},
    {"in": "34", "out": "39"},
    {"in": "7",  "out": "?"} 
]

# Scaled coordinates based purely on the uncropped image bounds
# Your original unscaled Y bounds were 500 to 780. Scaled by 0.5 = 250 to 390.
# The Y coordinates (280, 320, 360) now fit perfectly inside that vertical space.
START_POS = [(320, 280), (480, 320), (380, 360)] 
END_POS = [(1280, 280), (1420, 320), (1320, 360)] 

# --- HELPER FUNCTIONS ---
def find_font(size):
    font_path = "/Users/thomasfeather/Library/Fonts/Copy of Proxima Soft.otf"
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

def remove_vertical_whitespace(img):
    """Auto-crops dead white space from the top and bottom of the image"""
    bg = Image.new(img.mode, img.size, BG_EXTENSION_COLOR)
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        # Add 20px padding to the top and bottom crop
        top = max(0, bbox[1] - 20)
        bottom = min(img.height, bbox[3] + 20)
        return img.crop((0, top, img.width, bottom))
    return img

def main():
    string_file = os.path.join(os.path.expanduser('~'), 'Desktop', 'NR_NM_template.txt')
    if not os.path.exists(string_file): 
        print(f"Error: {string_file} not found on Desktop.")
        return
        
    with open(string_file, 'r') as f: 
        base64_data = f.read().strip()

    print("Loading base image...")
    # 1. Load and convert to RGB
    img = Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGB")
    
    # 2. Scale down FIRST
    scaled_width = int(img.width * SCALE)
    scaled_height = int(img.height * SCALE)
    img = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    
    draw = ImageDraw.Draw(img)
    font_num = find_font(int(95 * SCALE))

    print("Rendering static question...")
    # 3. Draw text SECOND (Before any cropping happens)
    for i in range(3):
        # Draw Input on the left
        draw.text(START_POS[i], NUMBERS[i]["in"], font=font_num, fill=TEXT_COLOR, anchor="mm")
        
        # Draw Output on the right
        draw.text(END_POS[i], NUMBERS[i]["out"], font=font_num, fill=TEXT_COLOR, anchor="mm")

    print("Cropping image...")
    # 4. Crop LAST (This crops the boxes and the text together)
    img = remove_vertical_whitespace(img)

    print("Saving PNG...")
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    save_path = os.path.join(desktop, "number_machine_tutorial_static.png")
    
    img.save(save_path, "PNG")
    print(f"Done! Saved static image to {save_path}")

if __name__ == "__main__":
    main()