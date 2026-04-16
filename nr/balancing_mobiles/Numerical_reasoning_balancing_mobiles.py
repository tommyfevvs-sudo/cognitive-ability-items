import os
import random
import platform
import csv
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
OUTPUT_DIR = "assessment_bank_final"
WIDE_CANVAS_WIDTH = 2000           
LEGEND_HEIGHT = 180 
BG_COLOR = (255, 255, 255)
LINE_COLOR = (60, 60, 60)
ICON_SIZE = (100, 100)             
FONT_SIZE = 85

# --- SEARCH DIRECTORY ---
FONT_FOLDER = next((d for d in [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
] if os.path.exists(d)), "")

SHAPE_COLORS = {
    "star": "#B39DDB", "sq": "#90CAF9", "tri": "#F48FB1", "circ": "#FFE082"
}

class MobileNode:
    def __init__(self, shapes=None, left=None, right=None, is_decorative=False):
        self.shapes = shapes or [] 
        self.left = left
        self.right = right
        self.is_decorative = is_decorative 

    def get_all_shapes(self):
        found = set()
        for s_name, _ in self.shapes: found.add(s_name)
        if self.left: found.update(self.left.get_all_shapes())
        if self.right: found.update(self.right.get_all_shapes())
        return found

    def count_metrics(self):
        tiers = 1
        branches = 0
        if self.left or self.right:
            branches += 1
            l_tiers, l_br = self.left.count_metrics() if self.left else (0, 0)
            r_tiers, r_br = self.right.count_metrics() if self.right else (0, 0)
            tiers += max(l_tiers, r_tiers)
            branches += (l_br + r_br)
        return tiers, branches

    def get_max_depth_px(self, current_y, drop=100, v_padding=12, top_buffer=35):
        total_shapes = sum(count for _, count in self.shapes)
        shape_depth = current_y + top_buffer + (total_shapes * (ICON_SIZE[1] + v_padding))
        branch_depth = 0
        if self.left and self.right:
            start_y = max(shape_depth, current_y + drop)
            left_d = self.left.get_max_depth_px(start_y, drop, v_padding, top_buffer)
            right_d = self.right.get_max_depth_px(start_y, drop, v_padding, top_buffer)
            branch_depth = max(left_d, right_d)
        return max(shape_depth, branch_depth)

    def get_required_width(self, min_spacing=150):
        if not self.left and not self.right:
            return ICON_SIZE[0] // 2 + 20
        left_w = self.left.get_required_width(min_spacing)
        right_w = self.right.get_required_width(min_spacing)
        return left_w + right_w + min_spacing

def get_structure(difficulty_target, shapes_pool):
    random.shuffle(shapes_pool)
    
    def get_mixed_stack(pool, min_total=1, max_total=4):
        count = random.randint(min_total, max_total)
        if len(pool) >= 2 and random.random() < 0.6 and count > 1:
            s1_count = random.randint(1, count - 1)
            s2_count = count - s1_count
            s1, s2 = random.sample(pool, 2)
            return [(s1, s1_count), (s2, s2_count)]
        return [(random.choice(pool), count)]

    if difficulty_target == "Easy":
        sub = shapes_pool[:3]
        while True:
            left_stack = get_mixed_stack(sub, 1, 4)
            right_stack = get_mixed_stack(sub, 1, 4)
            l_total = sum(c for _, c in left_stack)
            r_total = sum(c for _, c in right_stack)
            if left_stack != right_stack and l_total != r_total:
                break
        root = MobileNode(shapes=[], left=MobileNode(shapes=left_stack), right=MobileNode(shapes=right_stack))
        
    else: # Medium
        num_shapes = random.choice([3, 4])
        sub = shapes_pool[:num_shapes]
        l_stem = get_mixed_stack(sub, 1, 1) if random.random() < 0.8 else []
        r_stem = get_mixed_stack(sub, 1, 1) if random.random() < 0.8 else []
        flip = random.random() > 0.5

        if random.random() > 0.5:
            is_redundant = random.random() < 0.15 
            l_bottom_left = get_mixed_stack(sub, 1, 3)
            l_bottom_right = get_mixed_stack(sub, 1, 3)
            while sum(c for _, c in l_bottom_left) == sum(c for _, c in l_bottom_right):
                l_bottom_right = get_mixed_stack(sub, 1, 3)
            r_bottom_left = l_bottom_left if is_redundant else get_mixed_stack(sub, 1, 3)
            r_bottom_right = l_bottom_right if is_redundant else get_mixed_stack(sub, 1, 3)
            
            root = MobileNode(shapes=[],
                              left=MobileNode(shapes=l_stem, 
                                              left=MobileNode(shapes=l_bottom_left), 
                                              right=MobileNode(shapes=l_bottom_right)),
                              right=MobileNode(shapes=r_stem, 
                                               left=MobileNode(shapes=r_bottom_left), 
                                               right=MobileNode(shapes=r_bottom_right),
                                               is_decorative=is_redundant))
        else:
            stack_side = MobileNode(shapes=get_mixed_stack(sub, 1, 4))
            branch_side = MobileNode(shapes=r_stem, 
                                     left=MobileNode(shapes=get_mixed_stack(sub, 1, 3)), 
                                     right=MobileNode(shapes=get_mixed_stack(sub, 1, 3)))
            if flip: root = MobileNode(shapes=[], left=branch_side, right=stack_side)
            else: root = MobileNode(shapes=[], left=stack_side, right=branch_side)
    return root

def get_total_weight(node, weights):
    w = sum(weights.get(name, 5) * count for name, count in node.shapes)
    if node.left and node.right:
        w += get_total_weight(node.left, weights) + get_total_weight(node.right, weights)
    return w

def is_balanced(node, weights):
    if not node.left or not node.right: return True
    left_w = get_total_weight(node.left, weights)
    right_w = get_total_weight(node.right, weights)
    if left_w != right_w: return False
    return is_balanced(node.left, weights) and is_balanced(node.right, weights)

def solve_mobile(node, target_shape):
    all_shapes = list(node.get_all_shapes())
    def find_essential_shapes(n):
        essential = set()
        if not n.is_decorative:
            for s_name, _ in n.shapes: essential.add(s_name)
        if n.left: essential.update(find_essential_shapes(n.left))
        if n.right: essential.update(find_essential_shapes(n.right))
        return essential
    essential_shapes = find_essential_shapes(node)
    redundant_shapes = [s for s in all_shapes if s not in essential_shapes]
    known_shapes = [s for s in essential_shapes if s != target_shape]
    for _ in range(30000):
        known_vals = random.sample(range(1, 11), len(known_shapes))
        weights = dict(zip(known_shapes, known_vals))
        for s in redundant_shapes: weights[s] = random.randint(1, 10)
        for val in range(1, 21):
            if val in known_vals: continue 
            weights[target_shape] = val
            if is_balanced(node, weights):
                return weights, val, essential_shapes
    return None, None, None

def render_mobile_only(draw, canvas, icons, node, x, y):
    drop, v_padding, top_buffer = 100, 12, 35 
    total_shapes = sum(count for _, count in node.shapes)
    y_shape_start = y + top_buffer
    shape_end_y = y_shape_start + (total_shapes * (ICON_SIZE[1] + v_padding)) - v_padding - (ICON_SIZE[1]//2) if total_shapes > 0 else y
    line_start_y = shape_end_y if total_shapes > 0 else y
    if node.left and node.right:
        raw_width = node.get_required_width(min_spacing=180)
        beam_w = max(220, min(raw_width // 2, 480))
        line_end_y = line_start_y + drop
        draw.line([(x, y), (x, line_end_y)], fill=LINE_COLOR, width=4)
        draw.line([(x - beam_w, line_end_y), (x + beam_w, line_end_y)], fill=LINE_COLOR, width=5)
        render_mobile_only(draw, canvas, icons, node.left, x - beam_w, line_end_y)
        render_mobile_only(draw, canvas, icons, node.right, x + beam_w, line_end_y)
    else:
        draw.line([(x, y), (x, shape_end_y)], fill=LINE_COLOR, width=4)
    if total_shapes > 0:
        curr_y = y_shape_start
        for name, count in node.shapes:
            for _ in range(count):
                canvas.paste(icons[name], (int(x - ICON_SIZE[0]//2), int(curr_y)), icons[name])
                curr_y += ICON_SIZE[1] + v_padding

def stamp_legend(canvas, icons, essential_shapes, target_shape, weights, font):
    draw = ImageDraw.Draw(canvas)
    items = [(s, weights[s]) for s in essential_shapes if s != target_shape]
    items += [(target_shape, "?")]
    box_width, y_mid = 380, LEGEND_HEIGHT // 2
    start_x = (canvas.width - (len(items) * box_width)) // 2
    for i, (name, val) in enumerate(items):
        cx = start_x + (i * box_width) + (box_width // 2)
        # Paste icon centered on y_mid
        icon_y = y_mid - (ICON_SIZE[1] // 2)
        canvas.paste(icons[name], (cx - 110, icon_y), icons[name])
        
        # Calculate text bounding box to center it vertically relative to the icon
        text_str = f"= {val}"
        bbox = draw.textbbox((0, 0), text_str, font=font)
        text_height = bbox[3] - bbox[1]
        # Align text center to y_mid
        text_y = y_mid - (text_height // 2) - bbox[1]
        draw.text((cx + 5, text_y), text_str, fill="black", font=font)

def create_shape_icons():
    icons = {}
    for name, color in SHAPE_COLORS.items():
        icon = Image.new('RGBA', ICON_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        if name == "sq": draw.rectangle([5, 5, 95, 95], fill=color, outline="black", width=3)
        elif name == "circ": draw.ellipse([5, 5, 95, 95], fill=color, outline="black", width=3)
        elif name == "tri": draw.polygon([(50, 5), (5, 95), (95, 95)], fill=color, outline="black", width=3)
        elif name == "star":
            pts = [(50, 2), (61, 38), (98, 38), (68, 60), (79, 96), (50, 75), (21, 96), (32, 60), (2, 38), (39, 38)]
            draw.polygon(pts, fill=color, outline="black", width=3)
        icons[name] = icon
    return icons

def main():
    total_in = input("How many mobiles? ")
    total = int(total_in) if total_in.isdigit() else 10
    abs_path = os.path.abspath(OUTPUT_DIR)
    if not os.path.exists(abs_path): os.makedirs(abs_path)
    icons, metadata_rows, i = create_shape_icons(), [], 0
    font = None
    if os.path.exists(FONT_FOLDER):
        for filename in os.listdir(FONT_FOLDER):
            if ("proxima" in filename.lower() and "soft" in filename.lower()
                    and not any(x in filename.lower() for x in ['bold', 'italic', 'semibold', 'light', 'black'])
                    and filename.lower().endswith(('.ttf', '.otf'))):

                try:
                    font = ImageFont.truetype(os.path.join(FONT_FOLDER, filename), FONT_SIZE)
                    break
                except: pass
    if font is None: font = ImageFont.load_default(size=FONT_SIZE)

    # --- 1. BATCHING LOGIC FROM CSV ---
    csv_path = os.path.join(abs_path, "item_bank_metadata.csv")
    batch_id = 1
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                batches = [int(row['Batch']) for row in reader if 'Batch' in row]
                if batches: batch_id = max(batches) + 1
        except: pass

    half_point = total // 2
    while i < total:
        base_diff = "Easy" if i < half_point else "Medium"
        root = get_structure(base_diff, list(SHAPE_COLORS.keys()))
        all_shapes = list(root.get_all_shapes())
        target_shape = random.choice(all_shapes) 
        final_weights, answer_value, essential_shapes = solve_mobile(root, target_shape)
        if final_weights is None or target_shape not in essential_shapes: continue 
        
        tiers, branches = root.count_metrics()
        diff_score = (branches * 2) + len(essential_shapes)
        
        # Unique ID for naming
        unique_id = f"{batch_id}.{i+1:02d}"
        file_name = f"item{unique_id}_{branches}_{diff_score}.png"
        
        temp_h = root.get_max_depth_px(LEGEND_HEIGHT) + 300
        img = Image.new('RGB', (WIDE_CANVAS_WIDTH, int(temp_h)), BG_COLOR)
        stamp_legend(img, icons, essential_shapes, target_shape, final_weights, font)
        render_mobile_only(ImageDraw.Draw(img), img, icons, root, WIDE_CANVAS_WIDTH // 2, LEGEND_HEIGHT)
        
        bbox = Image.eval(img, lambda px: 255 - px).getbbox()
        if bbox:
            padding = 20
            crop_y1 = max(0, bbox[1] - padding)
            crop_y2 = min(img.height, bbox[3] + padding)
            img = img.crop((0, crop_y1, WIDE_CANVAS_WIDTH, crop_y2))
            
        img.save(os.path.join(abs_path, file_name))
        metadata_rows.append([file_name, batch_id, branches, diff_score, answer_value])
        print(f"Generated Batch {batch_id}: {file_name}")
        i += 1

    # --- 2. APPEND EXPORTS TO CSV ---
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Filename", "Batch", "Branches", "Difficulty_Score", "Answer"])
        writer.writerows(metadata_rows)
        
    if platform.system() == "Windows":
        os.startfile(abs_path)
    elif platform.system() == "Darwin":
        import subprocess; subprocess.call(["open", abs_path])

if __name__ == "__main__":
    main()