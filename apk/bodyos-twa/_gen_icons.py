
import os
from PIL import Image, ImageDraw

def make_icon(size, bg, fg):
    img = Image.new('RGBA', (size, size), bg)
    draw = ImageDraw.Draw(img)
    margin = size * 0.18
    draw.rounded_rectangle([margin, margin, size-margin, size-margin], radius=int(size*0.08), fill=fg)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(size * 0.42))
    except:
        font = ImageFont.load_default(size=int(size * 0.4))
    bbox = draw.textbbox((0, 0), 'B', font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), 'B', font=font, fill=(255, 255, 255, 255))
    return img

for d in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
    os.makedirs('/home/ubuntu/life-os/apk/bodyos-twa/app/src/main/res/mipmap-' + d, exist_ok=True)
    for name in ['ic_launcher.png','ic_maskable.png']:
        make_icon({'mdpi':48,'hdpi':72,'xhdpi':96,'xxhdpi':144,'xxxhdpi':192}[d], (10,14,18,255), (255,123,0,255)).save('/home/ubuntu/life-os/apk/bodyos-twa/app/src/main/res/mipmap-' + d + '/' + name)

# Splash images
for d in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
    os.makedirs('/home/ubuntu/life-os/apk/bodyos-twa/app/src/main/res/drawable-' + d, exist_ok=True)
    make_icon({'mdpi':300,'hdpi':450,'xhdpi':600,'xxhdpi':900,'xxxhdpi':1200}[d], (10,14,18,255), (255,123,0,255)).save('/home/ubuntu/life-os/apk/bodyos-twa/app/src/main/res/drawable-' + d + '/splash.png')

# Shortcut backgrounds
for d in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
    make_icon({'mdpi':48,'hdpi':72,'xhdpi':96,'xxhdpi':144,'xxxhdpi':192}[d], (255,255,255,0), (255,255,255,255)).save('/home/ubuntu/life-os/apk/bodyos-twa/app/src/main/res/drawable-' + d + '/shortcut_legacy_background.png')
