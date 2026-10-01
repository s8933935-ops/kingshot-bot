import os

# Update web_tierlist/index.html to include Chenko and Yeonwoo
path = r'web_tierlist\index.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Let's check if chenko and yeonwoo icons exist
c_icon = os.path.exists(r'web_tierlist\icons\chenko.png')
y_icon = os.path.exists(r'web_tierlist\icons\yeonwoo.png')
print(f"Chenko icon exists: {c_icon}, Yeonwoo icon exists: {y_icon}")
