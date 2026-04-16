import base64
import os
import io
from PIL import Image

# Your path
file_path = "/Users/thomasfeather/Downloads/TemplateV1.png"

# Output destinations
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
output_image = os.path.join(desktop, 'Final_Perfect_Clean_V4.png')
output_txt = os.path.join(desktop, 'Final_Perfect_String_V4.txt')

def clean_perfectly_v4(path):
    if not os.path.exists(path):
        print(f"ERROR: I can't find the file at {path}")
        return

    img = Image.open(path).convert("RGBA")
    width, height = img.size
    datas = img.getdata()

    new_data = []
    
    # Margin settings to wipe out the outer frame entirely
    v_margin = 45  # Top and Bottom (clears red border and grey shadow)
    h_margin = 25  # Left and Right (clears those vertical red lines)

    for index, item in enumerate(datas):
        y = index // width
        x = index % width
        r, g, b, a = item
        
        # 1. THE FRAME KILLER
        # If the pixel is near ANY of the four edges, it is deleted immediately.
        is_in_edge_frame = (y < v_margin or y > (height - v_margin) or 
                            x < h_margin or x > (width - h_margin))
        
        # 2. THE WHITELIST (for the middle section)
        is_grey = abs(r - g) < 25 and abs(g - b) < 25 and abs(r - b) < 25
        is_red = r > 150 and g < 100 and b < 100
        is_white = r > 240 and g > 240 and b > 240

        # --- LOGIC ---
        if is_in_edge_frame:
            # Force transparency for the outer frame
            new_data.append((255, 255, 255, 0))
        elif is_grey or is_red or is_white:
            # Keep the machine and boxes in the center
            new_data.append(item)
        else:
            # Delete the peach background
            new_data.append((255, 255, 255, 0))

    img.putdata(new_data)

    # Save PNG
    img.save(output_image, "PNG")
    
    # Save Base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
    with open(output_txt, "w") as f:
        f.write(encoded_string)
        
    print(f"Success! Full frame and peach background removed.")
    os.system(f"open '{output_image}'")

if __name__ == "__main__":
    clean_perfectly_v4(file_path)