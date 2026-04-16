import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont

def get_desktop_path(filename):
    return os.path.join(os.path.expanduser('~'), 'Desktop', filename)

# Load your template from the file we created earlier
string_file_path = get_desktop_path('image_string.txt')
if not os.path.exists(string_file_path):
    print("Error: image_string.txt not found on Desktop.")
else:
    with open(string_file_path, 'r') as f:
        base64_data = f.read()

    img_data = base64.b64decode(base64_data)
    base_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    draw = ImageDraw.Draw(base_img)
    w, h = base_img.size

    # Use a basic font
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Draw Vertical Grid Lines and X-Coordinates
    for x in range(0, w, 50):
        line_width = 2 if x % 100 == 0 else 1
        draw.line([(x, 0), (x, h)], fill="red", width=line_width)
        if x % 100 == 0:
            draw.text((x + 2, 10), f"X:{x}", fill="blue", font=font)

    # Draw Horizontal Grid Lines and Y-Coordinates
    for y in range(0, h, 50):
        line_width = 2 if y % 100 == 0 else 1
        draw.line([(0, y), (w, y)], fill="red", width=line_width)
        if y % 100 == 0:
            draw.text((10, y + 2), f"Y:{y}", fill="blue", font=font)

    # Output the result
    base_img.save(get_desktop_path("Coordinate_Finder.png"))
    print("Success! Open 'Coordinate_Finder.png' on your Desktop.")
    print("Find the 'Box Fence' coordinates for the white areas inside the red boxes.")
