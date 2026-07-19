import os
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def get_font(size, bold=False):
    # Try to find a sans font
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans" + ("-Bold" if bold else "") + ".ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans" + ("Bold" if bold else "") + ".ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def format_name(filename):
    name = os.path.splitext(filename)[0]
    parts = name.split('-', 1)
    if len(parts) == 2:
        num = parts[0]
        title = parts[1].replace('-', ' ').capitalize()
        return f"{num} — {title}"
    return name

def main():
    d = "/home/oumalik-younes/Documents/ProdServeur/docs/design/nebula-mockups"
    if not os.path.exists(d):
        print("Directory not found")
        return
        
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
    
    A4_W, A4_H = 1240, 1753  # 150 dpi
    
    # Fonts
    font_title = get_font(72, bold=True)
    font_sub = get_font(40)
    font_meta_k = get_font(28)
    font_meta_v = get_font(28, bold=True)
    font_sommaire = get_font(36, bold=True)
    font_item = get_font(24)
    font_footer = get_font(20)
    
    # 1. Cover page
    cover = Image.new("RGB", (A4_W, A4_H), "white")
    draw = ImageDraw.Draw(cover)
    
    # Top bar
    draw.rectangle([0, 0, A4_W, 60], fill="#5e45ce")
    
    # Title
    draw.text((100, 150), "Hermes Nebula", fill="#111", font=font_title)
    draw.text((100, 240), "Mockups UI — Mobile (PWA)", fill="#666", font=font_sub)
    
    # Divider
    draw.line([(100, 320), (A4_W - 100, 320)], fill="#5e45ce", width=4)
    
    # Meta
    draw.text((100, 380), "Nombre d'écrans :", fill="#666", font=font_meta_k)
    draw.text((450, 380), str(len(files)), fill="#111", font=font_meta_v)
    
    draw.text((100, 440), "Date de génération :", fill="#666", font=font_meta_k)
    draw.text((450, 440), datetime.now().strftime("%Y-%m-%d"), fill="#111", font=font_meta_v)
    
    draw.text((100, 500), "Source :", fill="#666", font=font_meta_k)
    draw.text((450, 500), "docs/design/nebula-mockups/", fill="#111", font=font_meta_v)
    
    # Sommaire
    draw.text((100, 650), "Sommaire", fill="#111", font=font_sommaire)
    draw.line([(100, 710), (400, 710)], fill="#5e45ce", width=3)
    
    # Items (2 columns)
    items_per_col = math.ceil(len(files) / 2)
    for i, f in enumerate(files):
        col = i // items_per_col
        row = i % items_per_col
        x = 100 + col * 500
        y = 760 + row * 45
        label = format_name(f)
        draw.text((x, y), f"• {label}", fill="#111", font=font_item)
        
    # Footer
    draw.text((100, A4_H - 80), "Hermes OS v4 · Nebula design previews · Tous formats 738x1600 (mobile portrait)", fill="#666", font=font_footer)
    
    pages = []
    
    # 2. Mockup pages
    for i, f in enumerate(files):
        page = Image.new("RGB", (A4_W, A4_H), "white")
        draw = ImageDraw.Draw(page)
        
        # Top bar
        draw.rectangle([0, 0, A4_W, 10], fill="#5e45ce")
        
        # Header
        label = format_name(f)
        draw.text((100, 40), label, fill="#111", font=font_sub)
        draw.text((100, 90), f"{f}  ·  page {i+1}/{len(files)}", fill="#666", font=font_meta_k)
        draw.line([(0, 140), (A4_W, 140)], fill="#5e45ce", width=2)
        
        # Image
        img_path = os.path.join(d, f)
        img = Image.open(img_path)
        img.thumbnail((A4_W - 300, A4_H - 300), Image.Resampling.LANCZOS)
        
        # Draw shadow
        ix = (A4_W - img.width) // 2
        iy = 160 + (A4_H - 160 - img.height) // 2
        draw.rectangle([ix+10, iy+10, ix+img.width+10, iy+img.height+10], fill="#ddd")
        
        page.paste(img, (ix, iy))
        pages.append(page)
        
    # Save PDF
    out_path = "/home/oumalik-younes/Documents/ProdServeur/docs/design/nebula-mockups.pdf"
    cover.save(out_path, "PDF", resolution=150.0, save_all=True, append_images=pages)
    print(f"Saved {out_path} with cover + {len(pages)} pages")

if __name__ == "__main__":
    main()
