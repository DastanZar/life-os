const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TEMPLATE = '/home/ubuntu/.local/lib/node_modules/@bubblewrap/cli/node_modules/@bubblewrap/core/template_project';
const OUT = '/home/ubuntu/life-os/apk/bodyos-twa';

const CFG = {
  packageId: 'com.lifeos.bodyos',
  host: 'does-diagram-fairly-ran.trycloudflare.com',
  startUrl: '/index.html',
  name: 'BODY OS',
  launcherName: 'BODY OS',
  themeColor: '#ff7b00',
  themeColorDark: '#ff7b00',
  navigationColor: '#0a0e12',
  navigationColorDark: '#0a0e12',
  navigationDividerColor: '#00000000',
  navigationDividerColorDark: '#00000000',
  backgroundColor: '#0a0e12',
  enableNotifications: false,
  fallbackType: 'customtabs',
  enableSiteSettingsShortcut: false,
  orientation: 'portrait',
  splashScreenFadeOutDuration: 300,
  generatorApp: 'bubblewrap-cli',
  appVersionCode: 1,
  appVersionName: '1.0',
  minSdkVersion: 21,
  shortcuts: [],
  buildGradle: { configs: [], repositories: ['google()', 'mavenCentral()'], dependencies: ['androidx.browser:browser:1.8.0', 'com.google.androidbrowserhelper:androidbrowserhelper:2.5.0'] },
};

function esc(s) {
  if (typeof s !== 'string') return s;
  return s.replace(/'/g, "\\'");
}

function escapeGradleString(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

function escapeJsonString(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

function escapeEJS(str) {
  return str
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');
}

function renderEJS(template, data) {
  let t = template;
  // Replace <%= expr %> - evaluate expr in context of data
  t = t.replace(/<%=([\s\S]*?)%>/g, (match, expr) => {
    try {
      // Create function with data keys as variables
      const keys = Object.keys(data);
      const values = Object.values(data);
      const fn = new Function(...keys, `return ${expr};`);
      const result = fn(...values);
      return String(result);
    } catch(e) {
      return `__EJS_ERROR_${e.message}__`;
    }
  });
  // Replace <% if (expr) { %> ... <% } %> 
  t = t.replace(/<%(\s*)if\s*\(([\s\S]*?)\)\s*\{?\s*%>([\s\S]*?)<%\s*\}\s*%>/g, (match, _, cond, body) => {
    try {
      const keys = Object.keys(data);
      const values = Object.values(data);
      const fn = new Function(...keys, `return ${cond};`);
      return fn(...values) ? body : '';
    } catch(e) { return ''; }
  });
  // Replace <% for (const x of arr) { %> ... <% } %>
  t = t.replace(/<%\s*for\s*\(\s*const\s+(\w+)\s+of\s+([\s\S]*?)\s*\)\s*\{?\s*%>([\s\S]*?)<%\s*\}\s*%>/g, (match, varName, arrExpr, body) => {
    try {
      const keys = Object.keys(data);
      const values = Object.values(data);
      const fn = new Function(...keys, `return ${arrExpr};`);
      const arr = fn(...values);
      return arr.map(item => {
        let b = body;
        // Replace references to the loop variable
        const loopKeys = Object.keys(item || {});
        const loopValues = Object.values(item || {});
        const loopFn = new Function(varName, ...keys, `return ${JSON.stringify(body)};`);
        // Simpler: just string replace the variable references
        return body.replace(new RegExp(`\\$\\{${varName}\\.(\\w+)\\}|${varName}\\.(\\w+)`, 'g'), (m, p1, p2) => {
          const prop = p1 || p2;
          return String(item[prop] || '');
        }).replace(new RegExp(`\\b${varName}\\.(\\w+)\\b`, 'g'), (m, prop) => String(item[prop] || ''));
      }).join('');
    } catch(e) { return ''; }
  });
  return t;
}

function renderTemplateFile(filePath, data) {
  let content = fs.readFileSync(filePath, 'utf8');
  content = renderEJS(content, data);
  const outPath = path.join(OUT, path.relative(TEMPLATE, filePath));
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, content);
}

// Generate icons using Python/Pillow
const iconPy = `
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
    os.makedirs('${OUT}/app/src/main/res/mipmap-' + d, exist_ok=True)
    for name in ['ic_launcher.png','ic_maskable.png']:
        make_icon({'mdpi':48,'hdpi':72,'xhdpi':96,'xxhdpi':144,'xxxhdpi':192}[d], (10,14,18,255), (255,123,0,255)).save('${OUT}/app/src/main/res/mipmap-' + d + '/' + name)

# Splash images
for d in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
    os.makedirs('${OUT}/app/src/main/res/drawable-' + d, exist_ok=True)
    make_icon({'mdpi':300,'hdpi':450,'xhdpi':600,'xxhdpi':900,'xxxhdpi':1200}[d], (10,14,18,255), (255,123,0,255)).save('${OUT}/app/src/main/res/drawable-' + d + '/splash.png')

# Shortcut backgrounds
for d in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
    make_icon({'mdpi':48,'hdpi':72,'xhdpi':96,'xxhdpi':144,'xxxhdpi':192}[d], (255,255,255,0), (255,255,255,255)).save('${OUT}/app/src/main/res/drawable-' + d + '/shortcut_legacy_background.png')
`;

// Clean and create output dir
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

// Copy static files
const copyList = [
  'settings.gradle', 'gradle.properties', 'build.gradle',
  'gradlew', 'gradlew.bat',
  'gradle/wrapper/gradle-wrapper.jar',
  'gradle/wrapper/gradle-wrapper.properties',
  'app/src/main/res/values/colors.xml',
  'app/src/main/res/xml/filepaths.xml',
  'app/src/main/res/xml/shortcuts.xml',
  'app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml',
  'app/src/main/res/drawable-anydpi/shortcut_legacy_background.xml',
  'app/src/main/res/drawable-anydpi/shortcut_monochrome.xml',
  'app/src/main/res/drawable-anydpi-v26/shortcut_maskable.xml',
  'app/src/main/res/drawable-anydpi-v26/shortcut_monochrome.xml',
];
for (const f of copyList) {
  const src = path.join(TEMPLATE, f);
  const dst = path.join(OUT, f);
  if (fs.existsSync(src)) {
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
  }
}

// Copy Java source files
const javaSrc = path.join(TEMPLATE, 'app/src/main/java');
if (fs.existsSync(javaSrc)) {
  fs.cpSync(javaSrc, path.join(OUT, 'app/src/main/java'), { recursive: true });
}

// Render EJS template files
renderTemplateFile(path.join(TEMPLATE, 'app/build.gradle'), CFG);
renderTemplateFile(path.join(TEMPLATE, 'app/src/main/AndroidManifest.xml'), CFG);
renderTemplateFile(path.join(TEMPLATE, 'app/src/main/res/values/strings.xml'), CFG);

// Generate icons via Python
fs.writeFileSync(path.join(OUT, '_gen_icons.py'), iconPy);
execSync('python3 ' + path.join(OUT, '_gen_icons.py'));

// Write twaManifest.json
fs.writeFileSync(path.join(OUT, 'twaManifest.json'), JSON.stringify(CFG, null, 2));

console.log('Project written to', OUT);
console.log('Top-level:', fs.readdirSync(OUT).join(', '));
console.log('Java files:', fs.readdirSync(path.join(OUT, 'app/src/main/java')).join(', '));
