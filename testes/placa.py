"""Ajustes da placa (Premissas › Placa de vídeo deste PC): a seção no PC, com uma ponte de mentira no lugar do programa
(window.desktop.placa, que anota as chamadas em window.__placa); a leitura é a da RX 9070 XT do Alex (28/10/2026), com
dados inventados no resto. Assumir, aplicar, valor fora da faixa, confirmar um ajuste que travou, de fábrica, desfazer,
copiar, os avisos (Windows e celular, uma vez só), o Afterburner, o "abrir junto com o Windows", a min-placa, duas
placas iguais e a tela (claro e escuro, PC e 390 px).
Uso: python3 testes/placa.py [--fotos <pasta>]"""
import json, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

CHAVE = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019"
CHAVE2 = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&1A2B3C4D&0&00000039"
NOME = "AMD Radeon RX 9070 XT"
AJ = {"potencia": -20, "tensao": -75, "clock": 0, "memoria": 2518, "temporizacao": 0, "ventoinha": {"modo": "fixa", "pct": 74}}

ASSUMIR = ("O painel guardou o ajuste que a placa já tem e não mudou nada. A partir de agora ele confere a cada minuto e "
           "aplica de novo se a placa sair desse ajuste.")
SEM = "O painel não está cuidando dos ajustes desta placa."
TESTE15 = "Em teste: faltam 15 minutos com a placa minerando. Se ela travar, o painel volta para o ajuste anterior."
DICA = 'Marque "O painel cuida dos ajustes da placa" para mudar.'
AGORA_TXT = "Agora: 2.201 MHz · 273 W · 43 °C · uso 100%"
AB = ("O MSI Afterburner também está aberto. Para os dois não brigarem, desligue nele o 'Aplicar overclock ao iniciar o "
      "sistema' (ou desinstale).")
INICIO = ("O painel só aplica o ajuste quando está aberto. Para aplicar assim que o Windows ligar: Este computador › Abrir o "
          "painel junto com o Windows.")
APLICADO = "Aplicado. A placa leu: Potência −21% · Tensão −75 mV · Clock máximo +0 MHz · Memória 2518 MHz · Ventoinha fixa em 74%."
CORRIJA = "Corrija os campos marcados."
CONFIRMA = ("Esse ajuste travou a placa em 25/10 13:00 (o driver de vídeo reiniciou durante o teste). Clique de novo em até 6 "
            "segundos para aplicar mesmo assim.")
COPIADO = "Copiado. Cole na conversa com o Claude para conferir a leitura."
TRAVOU_T = "O ajuste da placa travou"
TRAVOU_C = f"{NOME}: o driver de vídeo reiniciou durante o teste. O painel voltou para o ajuste anterior."

# a ponte de mentira: o estado como o placa.js devolve (estado() entrega os avisos uma vez só), a leitura da 9070 XT e as
# ações (cuidar assume sem gravar; aplicar deixa em teste; fabrica volta tudo ao padrão)
_PONTE = """(() => {
  const CONF = %s;
  const CURVA_PADRAO = [[30, 15], [50, 32], [61, 49], [72, 66], [80, 100]];
  const num = (atual, min, max, padrao, offset) => ({suporta: true, min, max, passo: 1, atual, padrao, ...(offset ? {offset: true} : {})});
  const PLACA = (chave, bus, indice, v) => ({chave, nome: "AMD Radeon RX 9070 XT", bus, indice, deFabrica: !!v.deFabrica, modo: 3,
    potencia: num(v.potencia, -30, 10, 0), tensao: num(v.tensao, -200, 0, 0, true), clock: num(v.clock, -500, 1000, 0, true),
    memoria: num(v.memoria, 2518, 3000, 2518), temporizacao: {suporta: true, atual: v.temporizacao, padrao: 0, opcoes: [0, 1]},
    ventoinha: {suporta: true, velMin: 15, velMax: 100, tempMin: 25, tempMax: 100, curva: v.curva, curvaPadrao: CURVA_PADRAO,
      zeroRpm: {suporta: true, atual: v.zeroRpm, padrao: 1}},
    agora: {clockMHz: 2201, watts: 273, tempC: 43, usoPct: 100, ventoinhaRpm: 2554}});
  const INICIO = {potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, curva: [[30, 74], [50, 74], [61, 74], [72, 74], [80, 74]], zeroRpm: 0};
  const FABRICA = {potencia: 0, tensao: 0, clock: 0, memoria: 2518, temporizacao: 0, curva: CURVA_PADRAO, zeroRpm: 1, deFabrica: true};
  const AJ = {potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: {modo: "fixa", pct: 74}};
  const copia = (o) => o === undefined ? undefined : JSON.parse(JSON.stringify(o));
  const chaves = CONF.duas ? [[CONF.chave, 3, 0], [CONF.chave2, 7, 4]] : [[CONF.chave, 3, 0]];
  const valores = {}; for (const [c] of chaves) valores[c] = {...INICIO};
  const st = window.__pst = {cuidar: !!CONF.cuidar, afterburner: !!CONF.afterburner, leitura: null, erro: null, placas: {}, pend: []};
  const ler = () => ({quando: Date.now(), afterburner: st.afterburner, placas: chaves.map(([c, bus, i]) => PLACA(c, bus, i, valores[c]))});
  const entrada = (ajuste, desde) => ({nome: "AMD Radeon RX 9070 XT", salvo: copia(ajuste), bom: copia(ajuste), teste: null, travou: [], situacao: "bom", bomDesde: desde, faltam: null});
  if (st.cuidar) for (const [c] of chaves) st.placas[c] = entrada(AJ, Date.now() - 3600e3);
  if (st.cuidar && CONF.teste) Object.assign(st.placas[CONF.chave], {teste: {ajuste: copia(AJ), desde: Date.now() - 180e3, minutos: 3}, situacao: "teste", faltam: 12});
  st.leitura = ler();
  const publico = (eventos) => copia({cuidar: st.cuidar, leitura: st.leitura, erro: st.erro,
    placas: Object.fromEntries(Object.entries(st.placas).map(([c, e]) => [c, {...e, situacao: st.cuidar ? e.situacao : "sem"}])), eventos: eventos || []});
  const aplicarValores = (c, a) => {
    const v = valores[c];
    for (const k of ["potencia", "tensao", "clock", "memoria", "temporizacao"]) if (k in a) v[k] = a[k];
    const f = a.ventoinha;
    if (f && f.modo === "fixa") { v.curva = v.curva.map(([t]) => [t, f.pct]); v.zeroRpm = 0; }
    else if (f && f.modo === "auto") { v.curva = CURVA_PADRAO; v.zeroRpm = 1; }
    delete v.deFabrica;
  };
  window.__placa = []; window.__copiado = null; window.__resposta = null; window.__mudancas = [];
  window.desktop.copiar = async (t) => { window.__copiado = String(t); return true; };
  window.desktop.dadosMudaram = (k) => { window.__mudancas.push(k); };
  window.desktop.placa = {
    estado: async () => { window.__placa.push(["estado"]); const ev = st.pend; st.pend = []; return publico(ev); },
    ler: async () => { window.__placa.push(["ler"]); st.leitura = ler(); return copia(st.leitura); },
    cuidar: async (sim) => {
      window.__placa.push(["cuidar", sim]);
      if (sim && !st.cuidar) { st.cuidar = true; st.leitura = ler(); for (const [c] of chaves) st.placas[c] = entrada(AJ, Date.now()); return {...publico(), assumiu: true}; }
      if (!sim) st.cuidar = false;
      return publico();
    },
    aplicar: async (chave, ajuste, op) => {
      window.__placa.push(["aplicar", chave, copia(ajuste), copia(op)]);
      const r = window.__resposta && window.__resposta(chave, ajuste, op);
      if (r) return r;
      if (!st.cuidar || !st.placas[chave]) return {ok: false, erro: "sem-placa", msg: "a placa não foi encontrada"};
      aplicarValores(chave, ajuste); st.leitura = ler();
      Object.assign(st.placas[chave], {salvo: copia(ajuste), teste: {ajuste: copia(ajuste), desde: Date.now(), minutos: 0}, situacao: "teste", faltam: 15});
      return {ok: true, itens: {}, leitura: st.leitura.placas.find((p) => p.chave === chave)};
    },
    fabrica: async (chave) => {
      window.__placa.push(["fabrica", chave]);
      valores[chave] = {...FABRICA}; st.leitura = ler();
      const a = {potencia: 0, tensao: 0, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: {modo: "auto"}};
      Object.assign(st.placas[chave], {salvo: copia(a), bom: copia(a), teste: null, situacao: "bom", bomDesde: Date.now(), faltam: null});
      return {ok: true, itens: {}, leitura: st.leitura.placas.find((p) => p.chave === chave)};
    },
    aoMudar: (fn) => { window.__mudou = () => fn({tipo: "mudou"}); }
  };
  /* quantas vezes a página gravou a min-placa */
  window.__minPlaca = 0;
  const gravar = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) { if (k === "min-placa") window.__minPlaca++; return gravar.call(this, k, v); };
})();"""


def ponte(**conf):
    return _PONTE % json.dumps({"chave": CHAVE, "chave2": CHAVE2, **conf})


def parte(f):
    """roda uma parte do teste; se ela quebrar no meio (um elemento que não existe), vira uma falha com o motivo"""
    def rodar(*a):
        try:
            f(*a)
        except Exception as e:  # noqa: BLE001
            checa(f"{f.__name__}: rodou até o fim", False, str(e).splitlines()[0][:300])
    return rodar


def chamadas(pg, op=None):
    return [c for c in pg.evaluate("window.__placa") if op is None or c[0] == op]


def status(pg):
    return pg.locator("#placa-status").text_content()


def cartao(pg, i=0):
    return pg.locator("#placa-lista .placa-c").nth(i)


def campo(c, k):
    return c.locator(f'[data-campo="{k}"]')


def junto(c, k, sel):
    """um elemento no mesmo rótulo do campo k (o nome ou a faixa)"""
    return c.locator(f'label:has([data-campo="{k}"]) {sel}')


def mudancas(pg, k="min-placa"):
    """quantas vezes a página avisou o programa que a chave k mudou (o que vai para o celular)"""
    return len([x for x in pg.evaluate("window.__mudancas") if x == k])


def prep_segundo_plano(pg):
    pg.evaluate("""() => { window.__sp = []; window.desktop.segundoPlano = async (o) => { window.__sp.push(o); return {}; };
      apCfg ||= {ligado: false}; celCfg ||= {ligado: false}; acCfg ||= {ligado: false}; }""")


@parte
def sem_ponte(p):
    pg = abrir(p, dados=DADOS, pc=True, hash="premissas")
    pg.wait_for_timeout(300)
    h = pg.evaluate("(() => { const b = document.getElementById('placa-p'); return b ? b.hidden : 'sem a seção'; })()")
    checa("sem a ponte: a seção fica escondida", h is True, h)
    checa("sem erros (sem a ponte)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def textos(p):
    pg = abrir(p, dados=DADOS, pc=True, hash="premissas", extra=ponte())
    t = pg.evaluate("""() => [
      textoAjuste({potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: {modo: "fixa", pct: 74}}),
      textoAjuste({potencia: 5, tensao: -80, clock: 150, memoria: 2600, temporizacao: 1, ventoinha: {modo: "auto"}}),
      textoAjuste({potencia: 0, ventoinha: {modo: "curva", curva: [[30, 20], [50, 40], [60, 60], [70, 80], [80, 100]], zeroRpm: 1}}),
      textoSituacao({situacao: "teste", desde: %d, faltam: 15, travou: null}),
      textoSituacao({situacao: "teste", desde: %d, faltam: 1, travou: null}),
      textoSituacao({situacao: "bom", desde: %d, faltam: null, travou: null}),
      textoSituacao({situacao: "travou", desde: 0, faltam: null, travou: {quando: %d, motivo: "o PC desligou de repente durante o teste"}}),
      textoSituacao({situacao: "sem", desde: 0, faltam: null, travou: null})]""" % (AGORA_MS, AGORA_MS, AGORA_MS - 3600000, AGORA_MS - 1800000))
    esperado = ["Potência −20% · Tensão −75 mV · Clock máximo +0 MHz · Memória 2518 MHz · Ventoinha fixa em 74%",
                "Potência +5% · Tensão −80 mV · Clock máximo +150 MHz · Memória 2600 MHz · Temporização rápida · Ventoinha automática",
                "Potência +0% · Ventoinha personalizada",
                TESTE15,
                "Em teste: falta 1 minuto com a placa minerando. Se ela travar, o painel volta para o ajuste anterior.",
                "Ajuste bom desde 25/10 13:00.",
                "O ajuste de 25/10 13:30 travou a placa (o PC desligou de repente durante o teste). O painel voltou para o anterior.",
                SEM]
    for i, (a, b) in enumerate(zip(t, esperado)):
        checa(f"texto {i + 1}: {b[:40]}…", a == b, a)
    checa("sem erros (textos)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def pc(p):
    pg = abrir(p, dados=DADOS, pc=True, hash="premissas", extra=ponte())
    pg.wait_for_timeout(300)
    checa("seção aparece com a ponte", pg.locator("#placa-p").is_visible())
    cs = [c[0] for c in chamadas(pg)]
    checa("sem cuidar: lê a placa antes de pedir o estado", cs[:2] == ["ler", "estado"], cs)
    c = cartao(pg)
    checa("o cartão leva a chave da placa", c.get_attribute("data-chave") == CHAVE, c.get_attribute("data-chave"))
    checa("o nome da placa", NOME in c.locator(".placa-cab").text_content())
    checa("potência −20", campo(c, "potencia").input_value() == "-20", campo(c, "potencia").input_value())
    fx = junto(c, "potencia", ".faixa").text_content()
    checa("a faixa da potência", fx == "de −30% a +10% · padrão 0%", fx)
    fx = junto(c, "tensao", ".faixa").text_content()
    checa("a faixa da tensão (ajuste)", fx == "de −200 mV a 0 mV · padrão 0 mV", fx)
    fx = junto(c, "memoria", ".faixa").text_content()
    checa("a faixa da memória", fx == "de 2518 MHz a 3000 MHz · padrão 2518 MHz", fx)
    rot = junto(c, "tensao", ".lbl").text_content()
    checa("o rótulo da tensão diz que é ajuste", "ajuste" in rot, rot)
    checa("o rótulo do clock diz que é ajuste", "ajuste" in junto(c, "clock", ".lbl").text_content())
    checa("a temporização rápida desmarcada", campo(c, "temporizacao").is_checked() is False)
    checa("a ventoinha fixa em 74", campo(c, "ventoinha").input_value() == "fixa" and campo(c, "pct").input_value() == "74",
          [campo(c, "ventoinha").input_value(), campo(c, "pct").input_value()])
    ops = c.locator('[data-campo="ventoinha"] option').all_text_contents()
    checa("as opções da ventoinha (sem a personalizada, que não é a atual)", ops == ["Automática (a da AMD)", "Fixa em"], ops)
    checa("o agora da placa", c.locator(".placa-agora").text_content() == AGORA_TXT, c.locator(".placa-agora").text_content())
    checa("a situação sem cuidar", c.locator(".placa-sit").text_content() == SEM, c.locator(".placa-sit").text_content())
    desl = pg.evaluate("[...document.querySelectorAll('#placa-lista [data-campo]')].map(x => x.disabled)")
    checa("sem cuidar: os campos desligados", desl and all(desl), desl)
    bts = {a: c.locator(f'[data-acao="{a}"]') for a in ("aplicar", "desfazer", "fabrica", "copiar")}
    checa("sem cuidar: Aplicar, Desfazer e Voltar ao de fábrica desligados", all(bts[a].is_disabled() for a in ("aplicar", "desfazer", "fabrica")))
    checa("sem cuidar: Copiar continua", bts["copiar"].is_enabled())
    checa("os rótulos dos botões", [bts[a].text_content() for a in bts] == ["Aplicar", "Desfazer", "Voltar ao de fábrica", "Copiar o que o painel leu da placa"],
          [bts[a].text_content() for a in bts])
    checa("sem cuidar: a dica", c.locator(".placa-dica").is_visible() and c.locator(".placa-dica").text_content() == DICA)
    checa("o aviso do Afterburner escondido", pg.locator("#placa-ab").is_hidden())
    checa("sem cuidar: o aviso do Windows escondido", pg.locator("#placa-inicio").is_hidden())
    checa("sem cuidar: nada gravado na min-placa", pg.evaluate("window.__minPlaca") == 0 and pg.evaluate("localStorage.getItem('min-placa')") is None)
    # cada aviso do programa (aoMudar) faz a página pedir o estado de novo
    n = len(chamadas(pg, "estado"))
    pg.evaluate("window.__mudou()")
    pg.wait_for_timeout(200)
    checa("aoMudar: a página pede o estado de novo", len(chamadas(pg, "estado")) > n)

    # ---------- cuidar ----------
    prep_segundo_plano(pg)
    pg.click("#placa-cuidar")
    pg.wait_for_timeout(300)
    checa("cuidar: pede ao programa", ["cuidar", True] in chamadas(pg, "cuidar"), chamadas(pg, "cuidar"))
    checa("cuidar: o texto de assumir", status(pg) == ASSUMIR, status(pg))
    sp = pg.evaluate("window.__sp.at(-1) || null")
    checa("cuidar: o painel fica no ícone e abre com o Windows", bool(sp) and sp.get("bandeja") is True and sp.get("iniciar") is True, sp)
    checa("cuidar: os campos ligados", not any(pg.evaluate("[...document.querySelectorAll('#placa-lista [data-campo]')].map(x => x.disabled)")))
    checa("cuidar: a dica some", c.locator(".placa-dica").is_hidden())
    checa("cuidar: a situação", c.locator(".placa-sit").text_content() == "Ajuste bom desde 25/10 14:00.", c.locator(".placa-sit").text_content())
    checa("cuidar: o aviso do Windows (o painel não abre com ele)", pg.locator("#placa-inicio").is_visible() and pg.locator("#placa-inicio").text_content() == INICIO,
          pg.locator("#placa-inicio").text_content())
    checa("cuidar: a min-placa gravada uma vez", pg.evaluate("window.__minPlaca") == 1, pg.evaluate("window.__minPlaca"))
    checa("cuidar: o celular fica sabendo da min-placa uma vez", mudancas(pg) == 1, mudancas(pg))
    # com o painel cuidando e a leitura nova, só o estado; com a leitura de mais de 2 minutos, lê antes
    pg.evaluate("window.__placa = []")
    pg.evaluate("carregarPlaca()")
    checa("leitura nova: não lê de novo", [x[0] for x in chamadas(pg)] == ["estado"], chamadas(pg))
    checa("estado igual: a min-placa não é gravada de novo", pg.evaluate("window.__minPlaca") == 1, pg.evaluate("window.__minPlaca"))
    pg.evaluate("() => { __pst.leitura.quando = Date.now() - 3 * 60e3; }")
    pg.evaluate("carregarPlaca()")
    pg.evaluate("window.__placa = []")
    pg.evaluate("carregarPlaca()")
    checa("leitura de mais de 2 minutos: lê antes", [x[0] for x in chamadas(pg)] == ["ler", "estado"], chamadas(pg))

    # ---------- aplicar ----------
    pot = campo(c, "potencia")
    pot.fill("-40")
    c.locator('[data-acao="aplicar"]').click()
    pg.wait_for_timeout(200)
    checa("fora da faixa: o campo marcado", pot.get_attribute("aria-invalid") == "true")
    checa("fora da faixa: o recado", status(pg) == CORRIJA, status(pg))
    checa("fora da faixa: nada pedido", not chamadas(pg, "aplicar"))
    pot.fill("-21")
    c.locator('[data-acao="aplicar"]').click()
    pg.wait_for_timeout(300)
    esperado = {**AJ, "potencia": -21}
    ap = chamadas(pg, "aplicar")
    checa("aplicar: a chave e o ajuste completo", ap == [["aplicar", CHAVE, esperado, {"mesmoQueTravou": False}]], ap)
    checa("aplicar: a situação em teste", c.locator(".placa-sit").text_content() == TESTE15, c.locator(".placa-sit").text_content())
    checa("aplicar: o recado com o que a placa leu", status(pg) == APLICADO, status(pg))
    checa("aplicar: o campo sem a marca", pot.get_attribute("aria-invalid") is None)
    mp = pg.evaluate("JSON.parse(localStorage.getItem('min-placa'))")
    esp_mp = {"v": 1, "cuidar": True, "placas": [{"nome": NOME, "ajuste": esperado, "situacao": "teste", "desde": AGORA_MS, "faltam": 15, "travou": None}]}
    checa("min-placa: o ajuste e a situação", bool(mp) and {k: v for k, v in mp.items() if k != "quando"} == esp_mp and isinstance(mp.get("quando"), int), mp)
    checa("min-placa: gravada uma vez por mudança", pg.evaluate("window.__minPlaca") == 2, pg.evaluate("window.__minPlaca"))
    checa("min-placa: o celular fica sabendo uma vez por mudança", mudancas(pg) == 2, mudancas(pg))
    pg.evaluate("carregarPlaca()")
    checa("min-placa: o mesmo estado não grava de novo", pg.evaluate("window.__minPlaca") == 2, pg.evaluate("window.__minPlaca"))
    checa("min-placa: o mesmo estado não vai de novo para o celular", mudancas(pg) == 2, mudancas(pg))
    checa("o PC nunca mostra a seção do celular", pg.evaluate("(() => { const b = document.getElementById('placa-cel'); return b ? b.hidden : 'sem a seção'; })()") is True)

    # ---------- um ajuste que já travou a placa: confirmar ----------
    pg.evaluate("""() => { window.__resposta = (c, a, op) => op && op.mesmoQueTravou ? null
      : {ok: false, precisaConfirmar: true, travou: {quando: %d, motivo: "o driver de vídeo reiniciou durante o teste"}}; }""" % (AGORA_MS - 3600000))
    pot.fill("-22")
    bt = c.locator('[data-acao="aplicar"]')
    bt.click()
    pg.wait_for_timeout(200)
    checa("travou antes: o recado", status(pg) == CONFIRMA, status(pg))
    checa("travou antes: o botão de confirmar", bt.text_content() == "Confirmar: aplicar mesmo assim", bt.text_content())
    bt.click()
    pg.wait_for_timeout(300)
    ap = chamadas(pg, "aplicar")
    checa("travou antes: o segundo clique aplica mesmo assim", ap[-1] == ["aplicar", CHAVE, {**AJ, "potencia": -22}, {"mesmoQueTravou": True}], ap[-2:])
    checa("travou antes: o botão volta", bt.text_content() == "Aplicar", bt.text_content())
    pot.fill("-23")
    bt.click()
    pg.wait_for_timeout(200)
    checa("travou antes (de novo): o botão de confirmar", bt.text_content() == "Confirmar: aplicar mesmo assim", bt.text_content())
    pg.wait_for_timeout(6300)
    checa("depois de 6 s sem clicar, o botão volta", bt.text_content() == "Aplicar", bt.text_content())
    n = len(chamadas(pg, "aplicar"))
    bt.click()
    pg.wait_for_timeout(200)
    ap = chamadas(pg, "aplicar")
    checa("depois de 6 s, o clique pergunta de novo", len(ap) == n + 1 and ap[-1][3] == {"mesmoQueTravou": False}, ap[-1:])
    pg.evaluate("window.__resposta = null")
    pg.wait_for_timeout(6200)

    # ---------- não perde o que a pessoa digitou; desfazer ----------
    pot.fill("-26")
    pg.evaluate("carregarPlaca()")
    checa("o redesenho não apaga o que foi digitado", pot.input_value() == "-26", pot.input_value())
    c.locator('[data-acao="desfazer"]').click()
    pg.wait_for_timeout(100)
    checa("desfazer: os campos voltam para o ajuste guardado", pot.input_value() == "-22", pot.input_value())

    # ---------- de fábrica ----------
    fab = c.locator('[data-acao="fabrica"]')
    fab.click()
    pg.wait_for_timeout(150)
    checa("fábrica: o primeiro clique pede confirmação", fab.text_content() == "Confirmar: voltar ao de fábrica" and not chamadas(pg, "fabrica"), fab.text_content())
    fab.click()
    pg.wait_for_timeout(300)
    checa("fábrica: o segundo clique volta ao de fábrica", chamadas(pg, "fabrica") == [["fabrica", CHAVE]], chamadas(pg, "fabrica"))
    checa("fábrica: os campos com o de fábrica", pot.input_value() == "0" and campo(c, "ventoinha").input_value() == "auto" and campo(c, "pct").is_hidden(),
          [pot.input_value(), campo(c, "ventoinha").input_value()])
    checa("fábrica: o botão volta", fab.text_content() == "Voltar ao de fábrica", fab.text_content())
    checa("fábrica: o recado", status(pg).startswith("A placa voltou ao de fábrica. A placa leu: Potência +0% · Tensão +0 mV"), status(pg))

    # ---------- copiar ----------
    c.locator('[data-acao="copiar"]').click()
    pg.wait_for_timeout(200)
    cp = pg.evaluate("window.__copiado") or ""
    checa("copiar: o recado", status(pg) == COPIADO, status(pg))
    checa("copiar: a versão, a leitura e o estado", "1.6.0-teste" in cp and NOME in cp and '"cuidar": true' in cp and "2201" in cp, cp[:300])
    checa("copiar: sem o número de série da placa", "2B6F2D5B" not in cp, cp[:300])

    # ---------- avisos ----------
    pg.evaluate("celCfg = {...(celCfg || {}), ligado: true, topico: 't', maquinas: true}")
    pg.evaluate("""() => { __pst.pend.push({tipo: "travou", chave: %s, nome: %s, titulo: %s, corpo: %s, quando: Date.now()}); }"""
                % (json.dumps(CHAVE), json.dumps(NOME), json.dumps(TRAVOU_T), json.dumps(TRAVOU_C)))
    pg.evaluate("carregarPlaca()")
    pg.wait_for_timeout(100)
    nots = [x for x in pg.evaluate("window.__notificacoes") if x.get("titulo") == TRAVOU_T]
    checa("aviso no Windows", len(nots) == 1 and nots[0].get("corpo") == TRAVOU_C and nots[0].get("tela") == "premissas", nots)
    cel = [x for x in pg.evaluate("window.__celular") if x.get("titulo") == TRAVOU_T]
    checa("aviso no celular", len(cel) == 1 and cel[0].get("tipo") == "maquina" and cel[0].get("corpo") == TRAVOU_C, cel)
    pg.evaluate("carregarPlaca()")
    pg.wait_for_timeout(100)
    checa("o mesmo aviso não sai de novo", len([x for x in pg.evaluate("window.__notificacoes") if x.get("titulo") == TRAVOU_T]) == 1
          and len([x for x in pg.evaluate("window.__celular") if x.get("titulo") == TRAVOU_T]) == 1)

    # ---------- Afterburner ----------
    pg.evaluate("() => { __pst.afterburner = true; __pst.leitura.afterburner = true; }")
    pg.evaluate("carregarPlaca()")
    checa("o aviso do Afterburner", pg.locator("#placa-ab").is_visible() and pg.locator("#placa-ab").text_content() == AB, pg.locator("#placa-ab").text_content())

    # ---------- descuidar ----------
    pg.evaluate("celCfg = {ligado: false}")   # sem os avisos no celular, só a placa pedia o ícone perto do relógio
    pg.click("#placa-cuidar")
    pg.wait_for_timeout(300)
    checa("descuidar: pede ao programa", chamadas(pg, "cuidar")[-1] == ["cuidar", False], chamadas(pg, "cuidar"))
    sp = pg.evaluate("window.__sp.at(-1) || null")
    checa("descuidar: o painel não precisa mais do ícone", bool(sp) and sp.get("bandeja") is False and sp.get("iniciar") is False, sp)
    checa("descuidar: os campos desligados", all(pg.evaluate("[...document.querySelectorAll('#placa-lista [data-campo]')].map(x => x.disabled)")))
    checa("sem erros (PC)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def abrir_configuracoes(p):
    """ao abrir Configurações (Mineração), a página pede o estado da placa"""
    pg = abrir(p, dados=DADOS, pc=True, hash="resumo", extra=ponte(cuidar=True))
    pg.wait_for_timeout(300)
    n = len(chamadas(pg, "estado"))
    pg.locator('.item[data-area="config"]').click()
    pg.wait_for_timeout(200)
    checa("abrir Configurações pede o estado", len(chamadas(pg, "estado")) > n, [n, len(chamadas(pg, "estado"))])
    checa("com o painel cuidando: a situação", cartao(pg).locator(".placa-sit").text_content() == "Ajuste bom desde 25/10 13:00.", cartao(pg).locator(".placa-sit").text_content())
    checa("sem erros (abrir Configurações)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def duas(p):
    """duas placas iguais (o mesmo nome): cada cartão com a sua chave, e um não mexe no outro (Review Focus 3)"""
    pg = abrir(p, dados=DADOS, pc=True, hash="premissas", extra=ponte(duas=True, cuidar=True))
    pg.wait_for_timeout(300)
    cs = pg.locator("#placa-lista .placa-c")
    checa("duas placas: dois cartões", cs.count() == 2, cs.count())
    checa("duas placas: cada uma com a sua chave", [cs.nth(0).get_attribute("data-chave"), cs.nth(1).get_attribute("data-chave")] == [CHAVE, CHAVE2])
    cab = [cs.nth(i).locator(".placa-cab b").text_content() for i in (0, 1)]
    checa("duas placas: os nomes se distinguem", cab[0] != cab[1] and all(NOME in x for x in cab), cab)
    campo(cs.nth(0), "potencia").fill("-24")              # mexeu na primeira e não aplicou
    campo(cs.nth(1), "potencia").fill("-21")
    cs.nth(1).locator('[data-acao="aplicar"]').click()
    pg.wait_for_timeout(300)
    ap = chamadas(pg, "aplicar")
    checa("duas placas: aplica só na segunda, com os campos dela", ap == [["aplicar", CHAVE2, {**AJ, "potencia": -21}, {"mesmoQueTravou": False}]], ap)
    checa("duas placas: a primeira fica como estava", campo(cs.nth(0), "potencia").input_value() == "-24", campo(cs.nth(0), "potencia").input_value())
    checa("duas placas: a situação de cada uma", [cs.nth(i).locator(".placa-sit").text_content() for i in (0, 1)] == ["Ajuste bom desde 25/10 13:00.", TESTE15],
          [cs.nth(i).locator(".placa-sit").text_content() for i in (0, 1)])
    checa("sem erros (duas placas)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def contagem(p):
    """durante os 15 minutos do teste, a min-placa não vai para o celular a cada minuto (cada uma é uma mensagem do ntfy.sh):
    só no começo, com 10 e 5 minutos faltando e no fim"""
    pg = abrir(p, dados=DADOS, pc=True, hash="premissas", extra=ponte(cuidar=True))
    pg.wait_for_timeout(300)
    c = cartao(pg)
    campo(c, "potencia").fill("-21")
    c.locator('[data-acao="aplicar"]').click()
    pg.wait_for_timeout(300)
    n0, m0 = pg.evaluate("window.__minPlaca"), mudancas(pg)
    vistos = []
    for f in range(14, 0, -1):
        pg.evaluate("(a) => { const e = __pst.placas[a[0]]; e.faltam = a[1]; e.teste.minutos = 15 - a[1]; }", [CHAVE, f])
        pg.evaluate("carregarPlaca()")
        vistos.append((f, pg.evaluate("JSON.parse(localStorage.getItem('min-placa')).placas[0].faltam")))
    pg.evaluate("(k) => { Object.assign(__pst.placas[k], {teste: null, situacao: 'bom', faltam: null, bomDesde: Date.now(), bom: __pst.placas[k].salvo}); }", CHAVE)
    pg.evaluate("carregarPlaca()")
    checa("contagem: a min-placa só com 10 e 5 minutos faltando e no fim", pg.evaluate("window.__minPlaca") - n0 == 3, [pg.evaluate("window.__minPlaca") - n0, vistos])
    checa("contagem: o celular fica sabendo 3 vezes", mudancas(pg) - m0 == 3, mudancas(pg) - m0)
    checa("contagem: o que o celular vê", [v for _, v in vistos] == [15] * 4 + [10] * 5 + [5] * 5, vistos)
    checa("contagem: no fim, bom", pg.evaluate("JSON.parse(localStorage.getItem('min-placa')).placas[0].situacao") == "bom")
    checa("contagem: o PC mostra os minutos de verdade", cartao(pg).locator(".placa-sit").text_content() == "Ajuste bom desde 25/10 14:00.", cartao(pg).locator(".placa-sit").text_content())
    checa("sem erros (contagem)", not erros(pg), erros(pg)[:3])
    pg.context.close()


MIN_PLACA = {"v": 1, "quando": AGORA_MS - 120000, "cuidar": True,
             "placas": [{"nome": NOME, "ajuste": AJ, "situacao": "teste", "desde": AGORA_MS - 180000, "faltam": 12, "travou": None}]}
AJ_TXT = "Potência −20% · Tensão −75 mV · Clock máximo +0 MHz · Memória 2518 MHz · Ventoinha fixa em 74%"


def secao_cel(pg):
    return pg.evaluate("""(() => { const b = document.getElementById('placa-cel'); if (!b) return null;
      return {hidden: b.hidden, texto: b.textContent.replace(/\\s+/g, ' ').trim(), campos: b.querySelectorAll('input, select, textarea, button:not(.sec-bt)').length}; })()""")


@parte
def celular(p):
    """o celular mostra o ajuste e a situação que o PC guardou na min-placa, sem campos nem botões"""
    pg = abrir(p, 390, 844, dados={**DADOS, "min-placa": MIN_PLACA}, celular=True, hash="premissas")
    s = secao_cel(pg)
    checa("celular: a seção aparece", bool(s) and s["hidden"] is False, s)
    checa("celular: o título", bool(s) and "Placa de vídeo do PC" in s["texto"], s)
    checa("celular: o nome e o ajuste", bool(s) and NOME in s["texto"] and AJ_TXT in s["texto"], s)
    checa("celular: a situação", bool(s) and "Em teste: faltam 12 minutos com a placa minerando." in s["texto"], s)
    checa("celular: sem campos e sem botões", bool(s) and s["campos"] == 0, s)
    checa("celular: a seção do PC escondida", pg.evaluate("document.getElementById('placa-p').hidden") is True)
    # a min-placa nova chega do PC: a seção redesenha
    um = {**MIN_PLACA, "placas": [{**MIN_PLACA["placas"][0], "faltam": 1}]}
    pg.evaluate("(m) => { localStorage.setItem('min-placa', JSON.stringify(m)); recarregarDados(['min-placa']); }", um)
    s = secao_cel(pg)
    checa("celular: falta 1 minuto", bool(s) and "Em teste: falta 1 minuto com a placa minerando." in s["texto"], s)
    tr = {**MIN_PLACA, "placas": [{**MIN_PLACA["placas"][0], "situacao": "travou", "faltam": None, "desde": AGORA_MS - 7200000,
                                    "travou": {"quando": AGORA_MS - 1800000, "motivo": "o driver de vídeo reiniciou durante o teste"}}]}
    pg.evaluate("(m) => { localStorage.setItem('min-placa', JSON.stringify(m)); recarregarDados(['min-placa']); }", tr)
    s = secao_cel(pg)
    checa("celular: travou, com o motivo",
          bool(s) and "O ajuste de 25/10 13:30 travou a placa (o driver de vídeo reiniciou durante o teste). O painel voltou para o anterior." in s["texto"], s)
    sem = {**MIN_PLACA, "cuidar": False, "placas": [{**MIN_PLACA["placas"][0], "situacao": "sem", "faltam": None}]}
    pg.evaluate("(m) => { localStorage.setItem('min-placa', JSON.stringify(m)); recarregarDados(['min-placa']); }", sem)
    s = secao_cel(pg)
    checa("celular: sem o painel cuidar", bool(s) and SEM in s["texto"], s)
    checa("sem erros (celular)", not erros(pg), erros(pg)[:3])
    pg.context.close()
    pg = abrir(p, 390, 844, dados=DADOS, celular=True, hash="premissas")
    s = secao_cel(pg)
    checa("celular sem a min-placa: a seção escondida", bool(s) and s["hidden"] is True, s)
    checa("sem erros (celular sem a min-placa)", not erros(pg), erros(pg)[:3])
    pg.context.close()


@parte
def listas(p):
    """as duas listas de chaves que o PC e o celular dividem: iguais, com a min-placa"""
    lista = lambda arq: re.findall(r'"(min-[\w-]+)"', re.search(r"const SINCRONIZADAS = \[([^\]]*)\]", open(os.path.join(RAIZ, arq), encoding="utf-8").read()).group(1))
    a, b = lista("mineracao.html"), lista(os.path.join("desktop", "sincronia.js"))
    checa("min-placa nas duas listas de chaves do PC e do celular (iguais)", a == b and "min-placa" in a, [a, b])


@parte
def tela_celular(p, pasta):
    for tema in ("claro", "escuro"):
        pg = abrir(p, 390, 844, dados={**DADOS, "min-placa": MIN_PLACA}, celular=True, hash="premissas")
        pg.evaluate("(t) => { document.documentElement.dataset.tema = t; }", tema)
        pg.evaluate("() => { const b = document.querySelector('#placa-cel .sec-bt'); if (b && b.getAttribute('aria-expanded') !== 'true') b.click(); }")
        pg.locator("#placa-cel").scroll_into_view_if_needed()
        pg.wait_for_timeout(200)
        t = pg.locator("#placa-cel").inner_text()
        checa(f"celular ({tema}): sem NaN, Infinity nem undefined", not re.search(r"NaN|Infinity|undefined", t), t[:200])
        larg_doc = pg.evaluate("document.documentElement.scrollWidth")
        checa(f"celular ({tema}): sem rolagem para o lado", larg_doc <= 390, larg_doc)
        pg.locator("#placa-cel").screenshot(path=os.path.join(pasta, f"placa_celular_{tema}.png"))
        checa(f"celular ({tema}): sem erros", not erros(pg), erros(pg)[:3])
        pg.context.close()


@parte
def tela(p, pasta):
    """claro e escuro, no PC e a 390 px: sem rolagem para o lado, botões de 44 px no estreito, sem NaN; e as fotos"""
    for nome, larg, alt in (("pc", 1366, 900), ("estreito", 390, 844)):
        for tema in ("claro", "escuro"):
            pg = abrir(p, larg, alt, dados=DADOS, pc=True, hash="premissas", extra=ponte(cuidar=True, teste=True, afterburner=True))
            pg.wait_for_timeout(300)
            pg.evaluate("(t) => { document.documentElement.dataset.tema = t; }", tema)
            pg.evaluate("() => { const b = document.querySelector('#placa-p .sec-bt'); if (b && b.getAttribute('aria-expanded') !== 'true') b.click(); }")
            pg.locator("#placa-p").scroll_into_view_if_needed()
            pg.wait_for_timeout(200)
            t = pg.locator("#placa-p").inner_text()
            checa(f"tela {nome} ({tema}): sem NaN, Infinity nem undefined", not re.search(r"NaN|Infinity|undefined", t), re.findall(r".{0,30}(?:NaN|Infinity|undefined).{0,30}", t)[:3])
            checa(f"tela {nome} ({tema}): a situação em teste", "Em teste: faltam 12 minutos" in t)
            larg_doc = pg.evaluate("document.documentElement.scrollWidth")
            checa(f"tela {nome} ({tema}): sem rolagem para o lado", larg_doc <= larg, larg_doc)
            if larg < 900:
                alt_bt = pg.evaluate("[...document.querySelectorAll('#placa-p button:not(.sec-bt), #placa-p input:not([type=checkbox]), #placa-p select')].filter(x => x.getClientRects().length).map(x => Math.round(x.getBoundingClientRect().height))")
                checa(f"tela {nome} ({tema}): botões e campos com 44 px", alt_bt and min(alt_bt) >= 44, alt_bt)
            pg.locator("#placa-p").screenshot(path=os.path.join(pasta, f"placa_{nome}_{tema}.png"))
            checa(f"tela {nome} ({tema}): sem erros", not erros(pg), erros(pg)[:3])
            pg.context.close()


FOTOS = sys.argv[sys.argv.index("--fotos") + 1] if "--fotos" in sys.argv else tempfile.mkdtemp(prefix="placa-fotos-")
os.makedirs(FOTOS, exist_ok=True)
with sync_playwright() as p:
    sem_ponte(p)
    textos(p)
    pc(p)
    abrir_configuracoes(p)
    duas(p)
    contagem(p)
    celular(p)
    listas(p)
    tela(p, FOTOS)
    tela_celular(p, FOTOS)
print("fotos em", FOTOS, file=sys.stderr)
fim()
