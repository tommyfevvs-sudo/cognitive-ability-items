import base64
import os

# Your path
file_path = "/Users/thomasfeather/Downloads/Template.png"
# Output destination
output_file = os.path.join(os.path.expanduser('~'), 'Desktop', 'image_string.txt')

if os.path.exists(file_path):
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # Write the string to a text file on your desktop
    with open(output_file, "w") as f:
        f.write(encoded_string)
        
    print(f"Success! The string was too big for the terminal, so I saved it here:")
    print(f"--> {output_file}")
    print("\nOpen that file, copy everything inside, and paste it into your main script.")
else:
    print(f"ERROR: I can't find the file at {file_path}")
