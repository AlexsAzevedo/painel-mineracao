#!/usr/bin/env python3
"""Gera a página do Simulador de placas na web a partir do painel (mineracao.html), como o gerar-index.py faz para o
programa do PC: do painel vêm o catálogo, os preços, a curva da fonte, os formatos de número e data, as cores, o CSS e o
bloco JS do simulador e a seção #v-sim; a casca (web/simulador-casca.html) põe "Seus números", "Seus PCs", o jeito de
guardar e as peças do painel que o simulador usa, adaptadas aos PCs da página.

Se uma peça mudar de nome ou de lugar no painel, para com "não achei <peça> no painel" e não gera nada.
Uso: python3 web/gerar-simulador.py [--painel mineracao.html] [--saida web/dist/simulador.html]"""
import argparse, os, re, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)


class Falta(Exception):
    pass


def const_linha(t, nome):
    """uma const de uma linha: `const NOME = …;` (com um comentário depois, ou não). Se ela passou a ocupar várias
    linhas, a primeira não termina em ; e o gerador para, em vez de copiar meia const"""
    m = re.search(r"^const " + re.escape(nome) + r"\s*=.*$", t, re.M)
    if not m:
        raise Falta("const " + nome)
    if not re.search(r";\s*(?:/\*.*?\*/\s*)*$", m.group(0)):
        raise Falta("const " + nome + " numa linha só, terminando em ;")
    return m.group(0)


def const_bloco(t, nome):
    """uma const de várias linhas, até a primeira linha `};` ou `}};`"""
    m = re.search(r"^const " + re.escape(nome) + r"\s*=", t, re.M)
    if not m:
        raise Falta("const " + nome)
    fim = re.compile(r"^\}\}?;", re.M).search(t, m.end())
    if not fim:
        raise Falta("fim de const " + nome)
    return t[m.start():t.index("\n", fim.start())]


def funcao(t, nome):
    """uma função de topo: numa linha só, ou até a linha `}`"""
    m = re.search(r"^(?:async )?function " + re.escape(nome) + r"\(.*$", t, re.M)
    if not m:
        raise Falta("function " + nome)
    linha = m.group(0)
    if linha.count("{") == linha.count("}") and linha.rstrip().endswith("}"):
        return linha
    fim = t.find("\n}\n", m.start())
    if fim < 0:
        raise Falta("fim de function " + nome)
    trecho = t[m.start():fim + 2]
    # fechada de outro jeito (com um comentário depois da chave, por exemplo), a busca pela linha "}" passaria por cima
    # das funções seguintes: só pode vir uma
    if len(re.findall(r"^(?:async )?function ", trecho, re.M)) != 1:
        raise Falta("fim de function " + nome + " (uma linha só com })")
    return trecho


def entre(t, ini, fim, nome, com_fim=False):
    """o trecho de `ini` até `fim` (sem o `fim`, ou com ele)"""
    a = t.find(ini)
    b = t.find(fim, a + len(ini)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise Falta(nome)
    return t[a:b + (len(fim) if com_fim else 0)]


def bloco_css(t, seletor):
    """as declarações de um bloco de topo do CSS, sem chaves dentro (`:root{…}`)"""
    m = re.search(r"^" + re.escape(seletor) + r"\{([^{}]*)\}", t, re.M)
    if not m:
        raise Falta("CSS " + seletor)
    return m.group(1).strip()


def cores(t):
    """as cores do painel no formato do artifact: claras no :root (por cima das escuras, que trazem as fontes), escuras
    no tema escuro do aparelho (sem a escolha "claro" do claude.ai) e na escolha "escuro" """
    escuro, claro = bloco_css(t, ":root"), bloco_css(t, ':root[data-tema="claro"]')
    return (":root{\n  " + escuro + "\n  " + claro + "\n}\n"
            "@media (prefers-color-scheme: dark){ :root:not([data-theme=\"light\"]){\n  " + escuro + "\n} }\n"
            ":root[data-theme=\"dark\"]{\n  " + escuro + "\n}")


# o que a casca dá ao bloco do simulador no lugar do painel: se o bloco deixou de usar um desses nomes, o painel mudou e a
# casca precisa acompanhar (senão a página sai e quebra na primeira conta)
DA_CASCA = ["cfg", "calcMaq", "maqsReais", "maqBase", "deprecModelo", "gravarCfg", "kxaSnap", "kxa", "PODE_KXA", "anuncios",
            "nomePlaca", "acharModelo", "dados"]


def conferir_js(pagina):
    """o JS da página sem erro de sintaxe (pelo node, quando ele está instalado: ele vem junto com o resto do projeto)"""
    if not shutil.which("node"):
        print("(sem o node: o JS da página não foi conferido)")
        return
    script = pagina[pagina.index("<script>") + len("<script>"):pagina.rindex("</script>")]
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
        f.write(script)
    try:
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
    finally:
        os.remove(f.name)
    if r.returncode != 0:
        erro = next((l for l in r.stderr.splitlines() if "Error" in l), r.stderr.strip()[-200:])
        raise Falta("um JS sem erro de sintaxe (" + erro.strip() + ")")


CONSTS = ["CATALOGO_RAW", "marcaDe", "nomeCompleto", "slug", "CATALOGO", "LEGADO", "novoId", "byId", "brl", "brl0", "n1", "$",
          "isoLocal", "hojeISO", "sinal", "esc", "SELOS", "CARGAS", "CPU_PARADO"]
FUNCOES = ["eficiencia", "somaMesesIso", "mesAnoIso", "mercado", "melhorPreco"]


def gerar(painel, casca):
    css = painel[painel.index("<style>"):painel.index("</style>")]
    pecas = [const_linha(painel, n) for n in CONSTS] + [const_bloco(painel, "MERCADO")] + [funcao(painel, n) for n in FUNCOES]
    js = entre(painel, "/* ---------- simulador de compra ----------", "/* ---------- carga inicial ---------- */", "bloco do simulador")
    css_sim = entre(css, "/* simulador de compra: as opções lado a lado", "/* fim do simulador de compra */", "CSS do simulador")
    tela = entre(painel, '<section class="view" id="v-sim"', "</section>", "seção #v-sim", com_fim=True)
    # a seção inteira: todos os elementos que o bloco procura pelo id (uma <section> dentro dela cortaria a cópia)
    ids = set(re.findall(r'\$\("([A-Za-z][\w-]*)"\)', js)) | set(re.findall(r'querySelector(?:All)?\("#([A-Za-z][\w-]*)', js))
    for i in sorted(ids):
        if f'id="{i}"' not in tela:
            raise Falta(f'a seção #v-sim inteira (sem o id="{i}" que o bloco do simulador usa)')
    codigo = re.sub(r"/\*.*?\*/", "", js + "\n".join(pecas), flags=re.S)   # sem os comentários, que citam os nomes
    for n in DA_CASCA:
        if not re.search(r"(?<![\w$.])" + re.escape(n) + r"(?![\w$])", codigo):
            raise Falta(f"o uso de {n} no bloco do simulador (a casca dá {n}: se o painel mudou o nome, mude a casca)")
    trocas = {"/*@@CORES@@*/": cores(css), "/*@@CSS_SIM@@*/": css_sim, "<!--@@TELA@@-->": tela,
              "/*@@PAINEL@@*/": "\n".join(pecas), "/*@@SIMULADOR@@*/": js}
    for marca in trocas:
        if casca.count(marca) != 1:
            raise Falta("marcador " + marca + " na casca")
    pos = [casca.index(m) for m in trocas]
    if pos != sorted(pos):
        raise Falta("os marcadores da casca na ordem certa")
    for marca, conteudo in trocas.items():
        casca = casca.replace(marca, conteudo)
    conferir_js(casca)
    return casca


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--painel", default=os.path.join(RAIZ, "mineracao.html"))
    ap.add_argument("--casca", default=os.path.join(AQUI, "simulador-casca.html"))
    ap.add_argument("--saida", default=os.path.join(AQUI, "dist", "simulador.html"))
    a = ap.parse_args()
    try:
        pagina = gerar(open(a.painel, encoding="utf-8").read(), open(a.casca, encoding="utf-8").read())
    except Falta as e:
        print(f"não achei {e} no painel (ou na casca): nada foi gerado")
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        f.write(pagina)
    print(f"gerado: {a.saida} ({len(pagina.encode('utf-8')) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
