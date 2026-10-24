"""Gera os ícones do app Android a partir do ícone do painel (desktop/build/icon.png) e tira as imagens de exemplo do Capacitor.

- ícone adaptável (Android 8+): fundo laranja (cor) + a placa de vídeo desenhada no meio (ic_launcher_foreground) e a
  versão monocromática (ícones temáticos do Android 13+);
- ícones antigos (Android 7): o quadrado arredondado (ic_launcher) e o redondo (ic_launcher_round);
- a tela de abertura usa o próprio ícone (res/drawable/splash.xml), sem as imagens do Capacitor.

Uso: python3 scripts/icones.py  (de dentro de celular/; precisa do Pillow)
"""
import pathlib
from PIL import Image, ImageDraw

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RES = RAIZ / "android" / "app" / "src" / "main" / "res"
fonte = Image.open(RAIZ.parent / "desktop" / "build" / "icon.png").convert("RGBA")
LARANJA, ESCURO = (242, 167, 61), (23, 24, 27)

# a placa (desenho escuro) separada do fundo laranja: opacidade pela "distância" entre as duas cores
def luz(c): return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
L0, L1 = luz(LARANJA), luz(ESCURO)
mascara = Image.new("L", fonte.size, 0)
px, mx = fonte.load(), mascara.load()
for y in range(fonte.size[1]):
    for x in range(fonte.size[0]):
        r, g, b, a = px[x, y]
        if a < 250: continue          # a borda do quadrado (laranja meio transparente) não é a placa
        t = (L0 - luz((r, g, b))) / (L0 - L1)
        v = int(max(0, min(1, t)) * a)
        mx[x, y] = v if v > 12 else 0     # variações mínimas do laranja não contam
caixa = mascara.getbbox()
desenho = mascara.crop(caixa)                     # só a placa, em tons de opacidade
print("placa no ícone original:", caixa, desenho.size)

def placa(cor, largura):
    """a placa na cor pedida, com a largura pedida (em px), fundo transparente"""
    alt = round(desenho.size[1] * largura / desenho.size[0])
    m = desenho.resize((largura, alt), Image.LANCZOS)
    img = Image.new("RGBA", m.size, cor + (0,)); img.putalpha(m)
    return img

DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
for nome, f in DENS.items():
    pasta = RES / f"mipmap-{nome}"; pasta.mkdir(parents=True, exist_ok=True)
    # adaptável: tela de 108 dp; a placa com 52 dp de largura cabe no círculo seguro de 66 dp
    lado = round(108 * f)
    for arq, cor in (("ic_launcher_foreground.png", ESCURO), ("ic_launcher_monochrome.png", (255, 255, 255))):
        tela = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        p = placa(cor, round(52 * f))
        tela.alpha_composite(p, ((lado - p.size[0]) // 2, (lado - p.size[1]) // 2))
        tela.save(pasta / arq, optimize=True)
    # antigos: 48 dp
    lado = round(48 * f)
    fonte.resize((lado, lado), Image.LANCZOS).save(pasta / "ic_launcher.png", optimize=True)
    grande = lado * 4
    red = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    ImageDraw.Draw(red).ellipse([grande * 0.04, grande * 0.04, grande * 0.96, grande * 0.96], fill=LARANJA + (255,))
    p = placa(ESCURO, round(grande * 0.56))
    red.alpha_composite(p, ((grande - p.size[0]) // 2, (grande - p.size[1]) // 2))
    red.resize((lado, lado), Image.LANCZOS).save(pasta / "ic_launcher_round.png", optimize=True)

ADAPTAVEL = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>
</adaptive-icon>
"""
(RES / "mipmap-anydpi-v26").mkdir(exist_ok=True)
for arq in ("ic_launcher.xml", "ic_launcher_round.xml"):
    (RES / "mipmap-anydpi-v26" / arq).write_text(ADAPTAVEL, encoding="utf-8")
(RES / "values" / "ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#F2A73D</color>\n</resources>\n', encoding="utf-8")

# tela de abertura: a cor de fundo do painel (clara ou escura, como o celular) com o ícone no meio
(RES / "drawable").mkdir(exist_ok=True)
(RES / "drawable" / "splash.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/fundo"/>
    <item android:width="96dp" android:height="96dp" android:gravity="center" android:drawable="@mipmap/ic_launcher"/>
</layer-list>
""", encoding="utf-8")

# fora as imagens de exemplo do Capacitor
apagados = 0
for p in list(RES.glob("drawable*/splash.png")) + [RES / "drawable-v24" / "ic_launcher_foreground.xml", RES / "drawable" / "ic_launcher_background.xml"]:
    if p.exists(): p.unlink(); apagados += 1
for p in RES.glob("drawable-*"):
    if p.is_dir() and not any(p.iterdir()): p.rmdir()
print("ícones gerados; imagens de exemplo apagadas:", apagados)
