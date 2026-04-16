import os
from moviepy import VideoFileClip
from PIL import Image

# 1. Locate the Desktop
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
input_path = os.path.join(desktop_path, "balances_instructions.mov")
output_path = os.path.join(desktop_path, "balances_ultra_sharp.webp")

print(f"Loading ProRes video from: {input_path}")

try:
    # 2. Load the video
    clip = VideoFileClip(input_path)
    
    print("Extracting frames (reducing to 15 FPS for web optimization)...")
    frames = []
    
    # 3. Pull out the frames as arrays and convert them to Pillow Images
    for frame in clip.iter_frames(fps=15, dtype='uint8'):
        frames.append(Image.fromarray(frame))
        
    print(f"Successfully extracted {len(frames)} frames.")
    print("Encoding to Animated WebP... this takes a moment to process the lossless compression.")
    
    # 4. Save the frames as a looping, lossless WebP
    frames[0].save(
        output_path,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / 15), # duration of each frame in milliseconds
        loop=0, # 0 means loop infinitely
        lossless=True
    )
    
    print(f"\nSuccess! Your razor-sharp WebP is saved at: {output_path}")

except Exception as e:
    print(f"\nAn error occurred: {e}")