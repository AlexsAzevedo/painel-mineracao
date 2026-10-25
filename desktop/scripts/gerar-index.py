"""Monta app/index.html para o aplicativo do computador a partir do painel (mineracao.html).

- troca as fontes do Google por cópias locais (funciona sem internet)
- põe uma política de segurança (a página não acessa a internet sozinha)
- liga o painel ao navegador escondido do aplicativo (window.claude -> window.desktop)
- opcional (só para uso próprio): grava dados iniciais copiados do painel online, para a primeira vez que o app abrir.
  Sem a pasta de dados, o aplicativo começa vazio e pergunta nome, cidade, luz etc. na primeira vez (é o que vai para outras pessoas).

Uso: python3 scripts/gerar-index.py <mineracao.html> [--com-dados <pasta-com-os-dados-exportados>]
"""
import json, pathlib, re, shutil, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
args = sys.argv[1:]
pasta_dados = None
if "--com-dados" in args:
    i = args.index("--com-dados"); pasta_dados = pathlib.Path(args[i + 1]); del args[i:i + 2]
fonte = pathlib.Path(args[0] if args else RAIZ.parent / "mineracao.html")
html = fonte.read_text(encoding="utf-8")

# ---------- fontes locais ----------
FONTES = [("Sora", "sora", [600, 700]),
          ("Inter", "inter", [400, 500, 600, 700]),
          ("JetBrains Mono", "jetbrains-mono", [400])]
shutil.rmtree(RAIZ / "app" / "fonts", ignore_errors=True)   # sem sobras de fontes antigas
(RAIZ / "app" / "fonts").mkdir(parents=True, exist_ok=True)
css = []
for familia, pacote, pesos in FONTES:
    for p in pesos:
        nome = f"{pacote}-latin-{p}-normal.woff2"
        shutil.copy(RAIZ / "node_modules" / "@fontsource" / pacote / "files" / nome, RAIZ / "app" / "fonts" / nome)
        css.append(f'@font-face{{font-family:"{familia}";font-style:normal;font-weight:{p};font-display:swap;src:url(fonts/{nome}) format("woff2")}}')
antes = len(html)
html = re.sub(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">',
              "<style>" + "".join(css) + "</style>", html, count=1)
assert len(html) != antes, "não achei o link das fontes do Google"

# ---------- dados iniciais (cópia do painel online) ----------
iniciais = {}
if pasta_dados and pasta_dados.exists():
    def doc(caminho):
        p = pasta_dados / caminho
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    def colecao(nome):
        itens = []
        for p in sorted((pasta_dados / nome).glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8")); d["_id"] = p.stem; itens.append(d)
        return sorted(itens, key=lambda d: d.get("criado") or d.get("data") or 0)
    cfg = doc("config/geral.json")
    if cfg: iniciais["min-cfg"] = cfg
    iniciais["min-placas"] = colecao("placas")
    iniciais["min-anuncios"] = colecao("anuncios")
    setup = doc("setup/principal.json")
    if setup: iniciais["min-setup"] = setup
    diario = colecao("diario") if (pasta_dados / "diario").exists() else []
    for d in diario: d["_id"] = d.get("data", d["_id"])
    iniciais["min-diario"] = diario

semente = ("""
/* aplicativo do computador: dados iniciais (só na primeira vez) */
(function(){
  var d = %s;
  try{
    if(localStorage.getItem("min-desktop-iniciado")) return;
    Object.keys(d).forEach(function(k){ if(localStorage.getItem(k) === null) localStorage.setItem(k, JSON.stringify(d[k])); });
    localStorage.setItem("min-desktop-iniciado", String(Date.now()));
  }catch(e){}
})();""" % json.dumps(iniciais, ensure_ascii=False)) if iniciais else ""

ponte = """<script>%s
/* o painel conversa com "o navegador do app" pela interface window.claude; aqui ela vira o navegador escondido do aplicativo */
(function(){
  if(!window.desktop || !window.desktop.navegar) return;   /* no celular (pelo navegador), quem lê as páginas é o PC */
  var ABA = "painel";
  function resp(t){ return {content:[{type:"text", text:t}]}; }
  var mcp = Object.freeze({
    callTool: async function(server, tool, input){
      try{
        if(tool === "navigate"){ var r = await window.desktop.navegar(String((input && input.url) || "")); return resp("navigated to " + r.url + "\\n\\nTab Context:\\n- Executed on tabId: " + ABA); }
        if(tool === "get_page_text"){ var t = await window.desktop.texto(Number(input && input.max_chars) || 50000); return resp("Title: " + t.title + "\\nURL: " + t.url + "\\nSource element: <" + t.el + ">\\n---\\n" + t.text + "\\n\\nTab Context:\\n- Executed on tabId: " + ABA); }
        if(tool === "preview_start") return resp("ok");
      }catch(e){ throw {code:"tool_error", message:String((e && e.message) || e)}; }
      throw {code:"not_in_manifest", message:"ferramenta indisponível no aplicativo"};
    }
  });
  window.claude = Object.freeze({use: async function(n){ return n === "mcp" ? mcp : null; }});
})();
</script>
""" % semente

i = html.index("<script>")
html = html[:i] + ponte + html[i:]

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
       "img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'")
pagina = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          f'<meta http-equiv="Content-Security-Policy" content="{CSP}">' + html + "</html>")
(RAIZ / "app" / "index.html").write_text(pagina, encoding="utf-8")
print(f"app/index.html: {len(pagina)//1024} KB · " + ("dados iniciais: " + ", ".join(f"{k} ({len(v) if isinstance(v, list) else 'ok'})" for k, v in iniciais.items()) if iniciais else "sem dados pessoais (começa pela configuração inicial)"))
