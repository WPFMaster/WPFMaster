import json
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
import numpy as np
import math

# ==========================================
# CONFIGURATION
# ==========================================
JSON_FILE = "data.json"
GRID_RADIUS = 4
HEX_SIZE = 1.0

# --- FIX 1: Set a font that definitely supports Czech ---
plt.rcParams['font.family'] = 'DejaVu Sans' 

# Visual Colors
COLORS = {
    0: "#ffcccc",  # Red-ish
    1: "#ccffcc",  # Green-ish
    2: "#ccccff",  # Blue-ish
    "hidden": "#f0f0f0"
}
EDGE_COLOR = "#555555"
KNIGHT_ICON = "♞"

# ==========================================
# MATH ENGINE
# ==========================================

def get_hex_color_group(q, r):
    return (q - r) % 3

def get_knight_moves(q, r):
    offsets = [
        (1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)
    ]
    return [(q + dq, r + dr) for dq, dr in offsets]

def generate_grid_nodes():
    nodes = []
    for q in range(-GRID_RADIUS, GRID_RADIUS + 1):
        for r in range(-GRID_RADIUS, GRID_RADIUS + 1):
            if max(abs(q), abs(r), abs(q + r)) <= GRID_RADIUS:
                nodes.append((q, r))
    return nodes

def solve_independent_set(nodes):
    # Sort by 'r' then 'q' for consistent placement
    sorted_nodes = sorted(nodes, key=lambda x: (x[1], x[0]))
    knights = set()
    
    for node in sorted_nodes:
        threats = get_knight_moves(*node)
        is_safe = True
        for t in threats:
            if t in knights:
                is_safe = False
                break
        if is_safe:
            knights.add(node)
    return knights

def hex_to_pixel(q, r):
    x = HEX_SIZE * 1.5 * q
    y = HEX_SIZE * math.sqrt(3) * (r + q / 2.0)
    return x, y

# ==========================================
# RENDER ENGINE
# ==========================================

def render_scene(scene):
    print(f"Generating: {scene['filename']}...")
    
    # Setup Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Title - ensures Matplotlib renders the strings correctly
    plt.title(f"{scene['title']}\n{scene['description']}", fontsize=14, pad=20)

    # Prepare Data
    all_nodes = generate_grid_nodes()
    
    active_nodes = []
    for q, r in all_nodes:
        layer = get_hex_color_group(q, r)
        if scene['filter_layer'] is None or scene['filter_layer'] == layer:
            active_nodes.append((q, r))

    placed_knights = set()
    if scene['show_knights'] and scene['auto_solve']:
        placed_knights = solve_independent_set(active_nodes)

    # Draw Edges
    if scene['show_edges']:
        node_set = set(active_nodes)
        for q, r in active_nodes:
            targets = get_knight_moves(q, r)
            x1, y1 = hex_to_pixel(q, r)
            for tq, tr in targets:
                if (tq, tr) in node_set and (tq > q or (tq == q and tr > r)):
                    x2, y2 = hex_to_pixel(tq, tr)
                    ax.plot([x1, x2], [y1, y2], color='black', alpha=0.3, linewidth=1, zorder=1)

    # Draw Hexagons
    for q, r in all_nodes:
        layer_id = get_hex_color_group(q, r)
        
        if (q, r) in active_nodes:
            fill_color = COLORS[layer_id]
        else:
            fill_color = COLORS["hidden"]
            
        x, y = hex_to_pixel(q, r)
        
        hex_patch = RegularPolygon(
            (x, y), numVertices=6, radius=HEX_SIZE, 
            orientation=math.radians(30), 
            facecolor=fill_color, edgecolor="#999999", linewidth=1, zorder=2
        )
        ax.add_patch(hex_patch)

        if (q, r) in placed_knights:
            ax.text(x, y, KNIGHT_ICON, ha='center', va='center', fontsize=20, zorder=3)

    ax.autoscale_view()
    plt.savefig(scene['filename'], bbox_inches='tight')
    plt.close()

# ==========================================
# MAIN LOOP
# ==========================================

if __name__ == "__main__":
    try:
        # --- FIX 2: Explicitly set encoding="utf-8" here ---
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            scenes = json.load(f)
        
        for scene in scenes:
            render_scene(scene)
            
        print("Done! Check your folder for PDFs.")
        
    except FileNotFoundError:
        print(f"Error: Could not find {JSON_FILE}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")