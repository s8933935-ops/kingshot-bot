import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_telop_image():
    input_path = "assets/images/x_post_image.jpg"
    output_path = "assets/images/x_post_with_telop.jpg"
    
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    
    # Fonts
    font_bold = "C:\\Windows\\Fonts\\meiryob.ttc"
    
    # Overlay layer for darkened gradients
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Top banner gradient shadow
    for y in range(int(h * 0.38)):
        alpha = int(180 * (1.0 - y / (h * 0.38)))
        draw_overlay.line([(0, y), (w, y)], fill=(10, 5, 25, alpha))
        
    # Bottom banner gradient shadow
    for y in range(int(h * 0.65), h):
        progress = (y - int(h * 0.65)) / (h * 0.35)
        alpha = int(220 * progress)
        draw_overlay.line([(0, y), (w, y)], fill=(10, 5, 25, alpha))
        
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Helper for text with thick stroke and shadow
    def draw_text_with_outline(xy, text, font, fill_color, outline_color, outline_width=6, shadow_offset=(4, 5)):
        x, y = xy
        # Shadow
        if shadow_offset:
            sx, sy = shadow_offset
            draw.text((x + sx, y + sy), text, font=font, fill=(0, 0, 0, 220))
        # Outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        # Main text
        draw.text((x, y), text, font=font, fill=fill_color)

    # 1. Top Hook Badge (Red-Orange Warning Pill)
    badge_h = int(h * 0.075)
    badge_w = int(w * 0.90)
    badge_x = int((w - badge_w) / 2)
    badge_y = int(h * 0.03)
    
    # Draw pill background
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=22, fill=(230, 25, 60, 245), outline=(255, 230, 0, 255), width=4)
    
    f_badge = ImageFont.truetype(font_bold, int(h * 0.038))
    badge_text = "【警告】知らないと大損!? 余ったキャンディは終了後ゴミ化！"
    bbox = draw.textbbox((0, 0), badge_text, font=f_badge)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((badge_x + (badge_w - tw) / 2, badge_y + (badge_h - th) / 2 - 3), badge_text, font=f_badge, fill=(255, 255, 255, 255))

    # 2. Main Title (Upper area, clear off character face)
    f_title = ImageFont.truetype(font_bold, int(h * 0.078))
    f_sub = ImageFont.truetype(font_bold, int(h * 0.052))
    
    title_text = "キングショット ハロウィン大作戦"
    bbox_t = draw.textbbox((0, 0), title_text, font=f_title)
    tw_t = bbox_t[2] - bbox_t[0]
    draw_text_with_outline(((w - tw_t) / 2, h * 0.12), title_text, f_title, fill_color=(255, 220, 0), outline_color=(20, 5, 40), outline_width=7)
    
    sub_text = "★【超保存版】完全攻略バイブル★"
    bbox_s = draw.textbbox((0, 0), sub_text, font=f_sub)
    tw_s = bbox_s[2] - bbox_s[0]
    draw_text_with_outline(((w - tw_s) / 2, h * 0.205), sub_text, f_sub, fill_color=(255, 255, 255), outline_color=(255, 60, 0), outline_width=6)

    # 3. Bottom 3 Key Points Cards (Infographic Badges)
    cards = [
        {"icon": "◆", "title": "無料キャンディ", "sub": "7,000個 回収上限", "color": (0, 245, 155)},
        {"icon": "◆", "title": "イタズランキング", "sub": "7日間フェーズ日程表", "color": (255, 220, 0)},
        {"icon": "◆", "title": "魔女大作戦ガチャ", "sub": "大賞1.0% ジャックポット", "color": (0, 229, 255)}
    ]
    
    card_w = int(w * 0.29)
    card_h = int(h * 0.15)
    spacing = int((w - card_w * 3) / 4)
    card_y = int(h * 0.81)
    
    f_card_t = ImageFont.truetype(font_bold, int(h * 0.036))
    f_card_s = ImageFont.truetype(font_bold, int(h * 0.032))
    
    for i, c in enumerate(cards):
        cx = spacing + i * (card_w + spacing)
        # Background card
        draw.rounded_rectangle([cx, card_y, cx + card_w, card_y + card_h], radius=16, fill=(12, 8, 30, 235), outline=c["color"], width=3)
        
        # Text inside card
        line1 = f"{c['icon']} {c['title']}"
        bbox_l1 = draw.textbbox((0, 0), line1, font=f_card_t)
        w_l1 = bbox_l1[2] - bbox_l1[0]
        draw.text((cx + (card_w - w_l1) / 2, card_y + 14), line1, font=f_card_t, fill=(255, 255, 255))
        
        line2 = c["sub"]
        bbox_l2 = draw.textbbox((0, 0), line2, font=f_card_s)
        w_l2 = bbox_l2[2] - bbox_l2[0]
        draw.text((cx + (card_w - w_l2) / 2, card_y + 48), line2, font=f_card_s, fill=c["color"])

    # Convert back to RGB and save
    final_img = img.convert("RGB")
    final_img.save(output_path, quality=95)
    print(f"Telop image created successfully at: {output_path}")

if __name__ == "__main__":
    create_telop_image()
