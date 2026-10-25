# Novo visual e app da Kryptex (1.6.0): plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** aplicar o visual aprovado (escuro por padrão, menu em grupos, barra de baixo no celular, Resumo com gráficos, ofertas com foto) e ligar o painel do PC ao app da Kryptex do próprio computador (ao vivo, pausar e voltar, proteção de temperatura), publicando como 1.6.0.

**Arquitetura:** a página continua sendo um arquivo só (`mineracao.html`), mudada por partes: primeiro as cores e fontes (variáveis CSS), depois o menu, o Resumo, a leitura do app da Kryptex e as ofertas. O aplicativo ganha um módulo pequeno (`desktop/kryptex-app.js`) que só sabe fazer 5 leituras e 2 ações no `localhost:8107`; o painel guarda e calcula tudo, como já faz com a conta da Kryptex. O celular vê um retrato sincronizado (`min-kx-app`) e pede ao PC para pausar ou atualizar pelos pedidos que já existem (`pedirAoPc`).

**Tecnologia:** HTML/CSS/JS sem biblioteca; Electron 44 (Node `http`); Capacitor 8; Python 3 + Playwright para os testes de navegador; `@fontsource/sora` e `@fontsource/inter` 5.x.

**Especificação:** `docs/superpowers/specs/2026-10-25-redesign-e-app-kryptex-design.md` (prévia: https://claude.ai/artifact/3C2zoebUjjp65qgBc2FFYL).

## Global Constraints

- Textos da tela em português do Brasil, frases curtas, sem jargão.
- Nunca `--com-dados`. Nenhum dado pessoal em commit, teste ou instalador: os testes usam dados inventados.
- Nada vai para o `main` sem o OK do Alex: o push no `main` publica a release.
- Durante o desenvolvimento, nenhum `PUT`/`POST` no app da Kryptex de verdade (porta 8107 do PC do Alex). Ações só no app de mentira.
- Os nomes de variável de hoje continuam (`--bg`, `--fg`, `--surface`, `--sunk`, `--line`, `--muted`, `--accent`, `--accent-soft`, `--good(-soft)`, `--warn(-soft)`, `--bad(-soft)`, `--side-*`, `--viz-*`, `--body`, `--display`, `--mono`): `celular/src/ponte-app.js` usa vários deles.
- Ids e classes de que `desktop/scripts/teste.js` e `celular/src/ponte-app.js` dependem continuam existindo: `.app`, `#bv`, `#bv-depois`, `#t-resumo`, `#nav-ofertas`, `#of-lista .of`, `.of-tit`, `.of-ret .pill`, `.of-preco s`, `.of.destaque`, `#kx-p`, `#kx-corpo`, `#kx-acoes [data-kx]`, `#kx-status`, `#kx-sug`, os `#b-*` e todos os `#v-*`.
- Paleta (escuro é o `:root`; claro é `:root[data-tema="claro"]`):

  | variável | escuro | claro |
  |---|---|---|
  | `--bg` | `#0C1016` | `#F3F5F8` |
  | `--surface` | `#131921` | `#FFFFFF` |
  | `--sunk` | `#1A222D` | `#EEF1F5` |
  | `--line` | `#243040` | `#DFE4EC` |
  | `--fg` | `#E8EDF4` | `#0F1726` |
  | `--muted` | `#8E9AAE` | `#566175` |
  | `--accent` / `--accent-soft` | `#F5A524` / `rgba(245,165,36,.14)` | `#A35F00` / `#FCEFD9` |
  | `--onaccent` | `#1B1203` | `#FFFFFF` |
  | `--good` / `--good-soft` | `#3DD68C` / `rgba(61,214,140,.13)` | `#0B6B47` / `#DCF3E8` |
  | `--warn` / `--warn-soft` | `#F2B544` / `rgba(242,181,68,.12)` | `#8A5A00` / `#FBEFD2` |
  | `--bad` / `--bad-soft` | `#FF7B72` / `rgba(255,123,114,.13)` | `#B42318` / `#FCE6E3` |
  | `--side-bg` / `--side-fg` / `--side-muted` | `#090C11` / `#E8EDF4` / `#8E9AAE` | `#FFFFFF` / `#0F1726` / `#566175` |
  | `--side-hover` / `--side-active` / `--side-accent` / `--side-line` / `--side-bad` | `#131921` / `rgba(245,165,36,.14)` / `#F5A524` / `#1A222D` / `#FF7B72` | `#F3F5F8` / `#FCEFD9` / `#A35F00` / `#DFE4EC` / `#B42318` |
  | `--viz-real` / `--viz-est` / `--viz-grid` / `--viz-axis` | `#F5A524` / `#66758C` / `#1A2330` / `#243040` | `#E59A1C` / `#8E9AAD` / `#EEF1F5` / `#C9D1DC` |
  | `--foto` / `--scrim` / `--onscrim` | `#202A37` / `rgba(5,8,12,.66)` / `#FFFFFF` | `#E6EAF0` / `rgba(12,16,22,.62)` / `#FFFFFF` |
  | `--shadow` | `rgba(0,0,0,.55)` | `rgba(15,23,38,.12)` |

- Fontes: `--display` e `--num` = Sora (600, 700); `--body` e `--mono` = Inter (400, 500, 600, 700) com algarismos tabulares; `--code` = JetBrains Mono 400 (só senha, código e endereço).
- Celular: largura menor que 900 px. PC: 900 px ou mais.
- Fotos: só `https://*.fbcdn.net/...` e `https://*.olx.com.br/...`, até 1200 caracteres.
- Pausar aceita só 15, 60, 180, 480 e 44640 minutos.
- Proteção: núcleo 85 °C ou memória 100 °C, 2 leituras seguidas, pausa 15 min; esquentou de novo em até 2 h depois de voltar → 44640 min.
- Leitura do app a cada 60 s. Aviso de parada: 3 leituras seguidas sem minerar e sem pausa. Aviso de app fechado: 5 min sem resposta depois de ter respondido.
- `min-kx-app` (sincroniza, só o PC grava): quando muda o estado, há aviso, depois de pausar/voltar, a pedido do celular e, fora isso, a cada 30 min. `min-kxa-hist` (só no PC): 36 h de leituras.
- Celular: pede retrato sozinho no máximo 1 vez a cada 10 min (retrato com mais de 10 min); Atualizar no máximo 1 vez a cada 2 min.
- Versão 1.6.0 no PC e no app do celular.

## Review Focus

1. **Pausado com hashrate velho na leitura**: o app da Kryptex pode mostrar hashrate por alguns segundos depois de pausar. Esperado: estado "Pausada", sem aviso de parada. Teste na Tarefa 5 (`pausado_nao_avisa`).
2. **Saque no meio do dia** (o saldo cai): o ganho de hoje nunca fica negativo e conta o que entrou depois do saque. Teste na Tarefa 5 (`hoje_com_saque`).
3. **PC dormiu horas**: a luz não conta o buraco (no máximo 5 min por leitura) e o buraco sozinho não gera aviso de parada. Teste na Tarefa 5 (`buraco_nao_avisa`).
4. **Celular com retrato velho** (de ontem): mostra "última leitura há X h" e não diz "Minerando" como se fosse agora. Teste na Tarefa 6 (`retrato_velho`).
5. **Foto que não carrega** (expirou, ou o painel online bloqueia): fica o desenho da placa, sem ícone de imagem quebrada e sem erro no console. Teste na Tarefa 7 (`foto_quebrada`).

## Arquivos

| Arquivo | O que muda |
|---|---|
| `mineracao.html` | cores, fontes, tema; menu e barra de baixo; Resumo; leitura do app da Kryptex; ofertas |
| `desktop/kryptex-app.js` (novo) | as 5 leituras e as 2 ações no app da Kryptex, filtrando os campos |
| `desktop/scripts/kryptex-falso.js` (novo) | app da Kryptex de mentira para os testes |
| `desktop/scripts/teste-kryptex-app.js` (novo) | teste do módulo contra o app de mentira |
| `desktop/main.js` | canal `kryptex-app`; `APP_PEDIDOS`; foto nas buscas; cores da janela e da página do celular |
| `desktop/preload.js` | `window.desktop.kryptexApp` |
| `desktop/sincronia.js` | `min-kx-app` em `SINCRONIZADAS` |
| `desktop/scripts/gerar-index.py`, `celular/scripts/montar-www.py` | fontes novas; `img-src` das fotos; cor do tema |
| `celular/src/ponte-app.js` | botão voltar fecha a folha Mais; prazo dos pedidos novos |
| `celular/android/app/src/main/res/values*/colors.xml` | fundo escuro |
| `desktop/scripts/teste.js` | app da Kryptex no teste de ponta a ponta; foto nas páginas de mentira; painel da conta em Premissas |
| `testes/apoio.py`, `testes/visual.py`, `testes/kryptex_app.py` (novos) | testes de navegador com dados inventados |
| `notas/v1.6.0.md`, `CLAUDE.md`, `package.json` e `package-lock.json` (desktop e celular) | versão e documentação |

---

### Task 1: Paleta nova, tema escuro e claro, fontes Sora e Inter

**Arquivos:**
- Modificar: `mineracao.html:1-4` (links das fontes e script do tema), `:135-152` (variáveis), `:36` (`#5cc98a` → `var(--good)`), `:117` (`body::before`), regras de números grandes (`.kpi b`, `.g-linha b`, `.tile b`) para `var(--num)`
- Modificar: `desktop/scripts/gerar-index.py:22-35`, `celular/scripts/montar-www.py:33-45` e `:57-60`
- Modificar: `desktop/package.json`, `desktop/package-lock.json`, `celular/package.json`, `celular/package-lock.json`
- Modificar: `desktop/main.js:64`, `:459`, `:521-524`, `:532`; `celular/android/app/src/main/res/values/colors.xml` e `values-night/colors.xml`
- Criar: `testes/apoio.py`, `testes/visual.py`

**Interfaces:**
- Produz: `temaAtual(): "escuro"|"claro"`; `aplicarTema(t: "escuro"|"claro"): void` (põe `data-tema` no `<html>`, grava `min-tema` com try/catch, marca `aria-pressed` em todo `[data-tema-op]`); qualquer botão `[data-tema-op="escuro"|"claro"]` troca o tema (um ouvinte no `document`).
- Produz: `<script id="tema-inicial">` logo depois da linha 2 (o `id` impede que os scripts de build, que procuram o primeiro `<script>` sem atributo, ponham as pontes antes dele).
- Produz (testes): `testes/apoio.py` com:
  - `abrir(p, largura=1366, altura=900, dados=None, celular=False, pc=False, sem_storage=False, hash="resumo") -> Page`: serve `mineracao.html` do repositório num servidor local (com doctype e viewport, como as suítes antigas), fixa o relógio em 25/10/2026 14:00 e junta os erros da página e do console. `celular=True` põe um `window.desktop` de celular de mentira (`remoto:true`, `sync.aoReceber/aoEstado/mudou/info/atualizar`, `pedirAoPc` que guarda `[nome, args]` em `window.__pedidos` e devolve `{ok:true}`). `pc=True` põe um `window.desktop` de PC de mentira (`versao`, `notificar`, `celular.enviar`, `kryptex.ler/entrar`, `kryptexApp`, os demais como funções vazias). `sem_storage=True` faz `localStorage` dar erro.
  - `DADOS` (dados inventados): `min-cfg`, 1 placa RX 9070 XT comprada em 11/10/2026 por R$ 5.000, 14 dias de Diário em outubro (11 a 24/10), 12 ofertas em `min-ofertas` (8 com `foto`, 4 sem; 6 que compensam, 3 apertadas, 3 que não compensam).
  - `DADOS_ESPERADO`: `recebido_mes`, `dias_grafico_diario`, `ofertas_filtradas` (as que aparecem com "Só os que compensam"), `ofertas_sem_foto_visiveis`.
  - `checa(nome, cond, extra="")`, `erros(page) -> list`, `contrastes(page, tema) -> {par: razão}` (calcula pelas cores das variáveis no tema pedido) e `fim()` (imprime o resumo e sai com 1 se houve falha).

- [ ] **Passo 1: Escrever o teste `tema` em `testes/visual.py`**

```python
pg = abrir(p)
checa("padrão escuro", pg.evaluate("document.documentElement.dataset.tema") == "escuro")
checa("fundo escuro", pg.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(12, 16, 22)")
pg.click('[data-tema-op="claro"]')
checa("claro", pg.evaluate("[document.documentElement.dataset.tema, getComputedStyle(document.body).backgroundColor, localStorage.getItem('min-tema')]") == ["claro", "rgb(243, 245, 248)", "claro"])
pg.reload(); checa("continua claro", pg.evaluate("document.documentElement.dataset.tema") == "claro")
checa("fontes", "Sora" in pg.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily") and "Inter" in pg.evaluate("getComputedStyle(document.body).fontFamily"))
# sem localStorage (navegação privada): escuro, sem erro
pg2 = abrir(p, sem_storage=True); checa("sem storage", pg2.evaluate("document.documentElement.dataset.tema") == "escuro" and not erros(pg2))
# contraste >= 4.5 nos dois temas: fg/bg, muted/surface, accent/bg, onaccent/accent, good/warn/bad sobre surface
for tema in ("escuro", "claro"):
    for par, razao in contrastes(pg, tema).items(): checa(f"contraste {tema} {par}", razao >= 4.5, round(razao, 2))
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `python3 testes/visual.py`
Expected: FAIL em "padrão escuro" (não existe `data-tema`).

- [ ] **Passo 3: Implementar**

Variáveis da tabela de Global Constraints; tirar o bloco `prefers-color-scheme` e o `[data-theme]`; `color-scheme: dark` no `:root` e `light` no claro. Fontes: link do Google com `Inter:wght@400;500;600;700`, `Sora:wght@600;700` e `JetBrains+Mono:wght@400` (mesmo formato de dois links, que os scripts de build trocam); `FONTES` dos dois scripts com `("Sora","sora",[600,700])`, `("Inter","inter",[400,500,600,700])`, `("JetBrains Mono","jetbrains-mono",[400])`; `npm install -D @fontsource/sora@^5 @fontsource/inter@^5` em `desktop/` e `celular/` (tirar `bricolage-grotesque` e `public-sans`). `body{font-variant-numeric:tabular-nums}`. Cores fixas da janela e da página do celular para `#0C1016`; `theme-color` do app: uma meta só, `#0C1016`.

- [ ] **Passo 4: Rodar e ver passar; montar as duas páginas**

Run: `python3 testes/visual.py && python3 desktop/scripts/gerar-index.py mineracao.html && python3 celular/scripts/montar-www.py --saida /tmp/www-teste && grep -c "font-family:\"Sora\"" desktop/app/index.html`
Expected: tudo OK; `2` (Sora 600 e 700).

- [ ] **Passo 5: Commit** (`git add` dos arquivos acima; mensagem "Paleta nova, tema escuro e claro, fontes Sora e Inter")

---

### Task 2: Menu em grupos no PC, barra de baixo e "Mais" no celular

**Arquivos:**
- Modificar: `mineracao.html:714-741` (menu), `:6-50` e `:117-133` (CSS do menu e do celular), `:5325-5334` (`VIEWS`, `irPara`), `renderGanhos`/`tickGanhos`/`renderCenario` (5295-5324: não mexem em elemento que não existe mais)
- Modificar: `celular/src/ponte-app.js:617-623` (voltar fecha a folha antes de tudo)
- Testar: `testes/visual.py`

**Interfaces:**
- Consome: `aplicarTema`, `[data-tema-op]` (Tarefa 1).
- Produz: `VIEWS = ["resumo","diario","minhas","ofertas","anuncio","placas","setup","premissas"]`; menu com `p.menu-t` "Acompanhar", "Comprar", "Ajustes" nessa ordem; `nav.abas` com `button.aba[data-view]` para resumo, diario, minhas (rótulo "Placas"), ofertas (`#aba-ofertas`, escondido junto com `#nav-ofertas`) e `button#aba-mais[aria-expanded][aria-controls="mais"]`; `#mais` (`role="dialog"`, `aria-modal="true"`) com anuncio, placas, setup, premissas e os botões de tema; `abrirMais()`, `fecharMais(): boolean` (true se estava aberta; também em `window.fecharMais`); `irPara` marca `aria-current="page"` nos `.aba` e no `#aba-mais` quando a tela está na folha.
- Produz: rodapé do menu com `#vivo` (o estado: por enquanto "Seu setup rende R$ X/dia" a partir de `renderGanhos`; a Tarefa 5 troca pelo ao vivo), `.tema-sel` (dois `[data-tema-op]`), `#sync` e `.credito`. Saem `.ganhos` (`#g-dia`, `#g-mes`, `#g-sub`, `#g-hoje`, `.g-anotar`) e `#cenario-mini`. No celular, o topo mostra a marca e `#g-chip` (estado curto).
- Avisos fixos de baixo (`.remoto-aviso`, `.aviso-atu`) sobem para cima da barra no celular: `bottom: calc(72px + env(safe-area-inset-bottom,0px) + 12px)`.

- [ ] **Passo 1: Escrever os testes `menu_pc` e `barra_celular`**

```python
pg = abrir(p)  # 1366
checa("grupos", pg.eval_on_selector_all(".menu-t", "e=>e.map(x=>x.textContent)") == ["Acompanhar", "Comprar", "Ajustes"])
checa("ordem", pg.eval_on_selector_all(".menu .item[data-view]", "e=>e.map(x=>x.dataset.view)") == ["resumo","diario","minhas","ofertas","anuncio","placas","setup","premissas"])
checa("sem barra no PC", pg.is_hidden(".abas"))
pg = abrir(p, largura=390, altura=844)
checa("barra", pg.eval_on_selector_all(".abas .aba:not([hidden])", "e=>e.map(x=>x.textContent.trim())") == ["Resumo", "Diário", "Placas", "Mais"])  # web: sem Ofertas
pg.click("#aba-mais"); checa("folha aberta", pg.is_visible("#mais") and pg.get_attribute("#aba-mais", "aria-expanded") == "true")
pg.click('#mais [data-view="premissas"]')
checa("foi para Premissas", pg.is_visible("#v-premissas") and pg.is_hidden("#mais") and pg.get_attribute("#aba-mais", "aria-current") == "page")
pg.click("#aba-mais"); pg.keyboard.press("Escape"); checa("Esc fecha", pg.is_hidden("#mais"))
checa("sem rolagem lateral", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
pg = abrir(p, largura=390, altura=844, celular=True)
checa("Ofertas na barra do celular", pg.is_visible("#aba-ofertas"))
```

- [ ] **Passo 2: Rodar e ver falhar** — Run: `python3 testes/visual.py` · Expected: FAIL em "grupos".
- [ ] **Passo 3: Implementar** (ícones dos itens como hoje; na barra de baixo, os mesmos SVG em 22 px com o rótulo embaixo, 44 px de altura no mínimo; folha `#mais` presa embaixo, acima da barra, com fundo `--surface` e uma camada atrás que fecha ao tocar).
- [ ] **Passo 4: Rodar e ver passar** — Run: `python3 testes/visual.py` · Expected: tudo OK.
- [ ] **Passo 5: Commit** ("Menu em grupos no PC e barra de baixo no celular")

---

### Task 3: Resumo novo (o mês, ganho por dia, retorno, ofertas, avisos) e o que muda de lugar

**Arquivos:**
- Modificar: `mineracao.html:744-769` (Resumo), `:5226-5293` (`renderResumo`; sair `renderResumoSetup` e `renderResumoDiario`), `:2689-2737` (`renderGraf`), o topo de `#v-placas` (recebe "Melhores compras hoje", `#r-compras` e `#r-compras-nota`), o fim de `#v-anuncio` (recebe "Últimos analisados", `#r-anuncios`), o topo de `#v-premissas` (recebe "Cenário das contas", `#r-cenario`, e o grupo "Kryptex" com `#kx-p`)
- Testar: `testes/visual.py`

**Interfaces:**
- Produz: `resumoMes(hoje = hojeISO()) -> {recebido, luz, lucro, dias, previsto, recup, custo}` — `recebido`, `luz` e `dias` vêm de `resumoDias(diario do mês corrente .map(linhaDia))`; `lucro = recebido - luz`; `previsto` = o "Lucro líquido/mês" de hoje (setup se houver, senão placas); `recup` e `custo` como no KPI "Recuperado" de hoje.
- Produz: `renderGraf(linhas, box = $("d-graf"), op = {})`: com `op.dias` e `op.fim` (ISO), o eixo são os `op.dias` dias até `op.fim`, com os dias sem anotação sem barra e com a linha do estimado; sem `op`, o Diário fica igual. A largura lembrada vai em `box.dataset.larg`.
- Produz: `renderAgora()` em `#agora` (aqui só os estados sem leitura ao vivo: estimativa do setup com o "hoje até agora" que corre a cada segundo em `#ag-hoje`, e a frase de cada lugar — PC: "Abra o app da Kryptex neste PC para ver a mineração ao vivo."; celular: "O PC ainda não mandou a leitura do app da Kryptex."; online: "No aplicativo do PC, este quadro mostra a mineração ao vivo."; sem placas: botão "Cadastrar suas placas").
- Produz: `htmlOfertaMini({x, c, r, v})` (foto, preço, modelo e "se paga em X meses") e `renderOfertasResumo()` em `#r-ofertas` (as 3 primeiras na ordem de "se paga mais rápido", sem descartadas; painel escondido quando `!OF_PODE()`; sem busca, um botão "Buscar ofertas").
- Produz: `renderAvisos()` em `#r-avisos` (de `kx.alertas`, os 6 mais novos dos últimos 7 dias; ícone e cor pelo tipo: parou/fechado/quente = `--bad`, lenta/falha/login = `--warn`, voltou = `--good`; hora "hoje 14:32", "ontem 09:10" ou a data; sem nenhum: "Nenhum aviso nos últimos 7 dias.").
- Produz: `#kx-aviso-sug` no Resumo ("2 dias da Kryptex esperando você anotar" + botão para o Diário), visível quando `sugestoesKx().length > 0`.
- Ordem no Resumo: cabeçalho, `#novid`, `#kx-aviso-sug`, `#agora`, `#r-mes` (4 cartões: Lucro do mês, Recebido, Previsto, Recuperado), depois em 2 colunas no PC: [`#r-graf-p` Ganho por dia | `#r-ret-p` Retorno das placas, com `#r-rig` restilizado] e [`#r-of-p` Ofertas perto de você | `#r-avisos-p` Avisos recentes]; no celular, uma coluna nessa ordem.

- [ ] **Passo 1: Escrever o teste `resumo`**

```python
pg = abrir(p, dados=DADOS)
ids = pg.eval_on_selector_all("#v-resumo [id]", "e=>e.map(x=>x.id)")
checa("ordem", [i for i in ids if i in ("agora","r-mes","r-graf-p","r-ret-p","r-avisos-p")] == ["agora","r-mes","r-graf-p","r-ret-p","r-avisos-p"], ids)
m = pg.evaluate("resumoMes()")
checa("o mês", abs(m["recebido"] - DADOS_ESPERADO["recebido_mes"]) < 0.01 and m["dias"] == 14, m)
checa("4 cartões do mês", pg.eval_on_selector_all("#r-mes .kpi .lbl", "e=>e.map(x=>x.textContent)") == ["Lucro do mês", "Recebido", "Previsto", "Recuperado"])
checa("14 dias no gráfico", pg.eval_on_selector_all("#r-graf .bar-hit", "e=>e.length") == 14)
checa("Diário igual", pg.evaluate("irPara('diario'), document.querySelectorAll('#d-graf .bar-hit').length") == DADOS_ESPERADO["dias_grafico_diario"])
checa("compras em Todas as placas", pg.evaluate("!!document.querySelector('#v-placas #r-compras')"))
checa("conta da Kryptex em Premissas", pg.evaluate("!!document.querySelector('#v-premissas #kx-p')"))
checa("agora sem app: frase do online", "No aplicativo do PC" in pg.inner_text("#agora"))
pgc = abrir(p, largura=390, altura=844, dados=DADOS, celular=True)
checa("3 ofertas no Resumo do celular", pgc.eval_on_selector_all("#r-ofertas .of-mini", "e=>e.length") == 3)
checa("avisos", pgc.evaluate("kx.alertas=[{t:Date.now()-60e3,tipo:'parou',texto:'RX 9070 XT parou de minerar'}], renderAvisos(), document.querySelector('#r-avisos').innerText").startswith("RX 9070 XT parou"))
checa("sem rolagem lateral 390", pgc.evaluate("document.documentElement.scrollWidth <= innerWidth"))
```

- [ ] **Passo 2: Rodar e ver falhar** — Expected: FAIL em "ordem".
- [ ] **Passo 3: Implementar** (CSS dos blocos novos com as variáveis; os textos e cálculos que vão para outras telas não mudam).
- [ ] **Passo 4: Rodar `python3 testes/visual.py`** e as suítes antigas copiadas para o mesmo arquivo de página (`teste_relatorio.py`, `teste_kryptex.py` da pasta de rascunho, depois de copiar `mineracao.html` para `/home/claude/mineracao.html`) · Expected: tudo OK (onde a suíte antiga procura `#kx-p` no Resumo, ela passa a chamar `irPara("premissas")`).
- [ ] **Passo 5: Commit** ("Resumo novo: o mês, ganho por dia, retorno, ofertas e avisos")

---

### Task 4: Módulo do app da Kryptex no aplicativo (e o app de mentira)

**Arquivos:**
- Criar: `desktop/kryptex-app.js`, `desktop/scripts/kryptex-falso.js`, `desktop/scripts/teste-kryptex-app.js`
- Modificar: `desktop/main.js` (perto de `:1214-1220`: `require("./kryptex-app.js")` e o canal), `desktop/preload.js`

**Interfaces:**
- Produz `desktop/kryptex-app.js` (só Node `http`; endereço `process.env.PAINEL_KRYPTEX_LOCAL || "http://127.0.0.1:8107"`, lido a cada chamada; 4 s por pedido; resposta até 2 MB):
  - `ler(): Promise<Leitura>`; `pausar(minutos: 15|60|180|480|44640): Promise<Leitura>` (`PUT /pause {"pause_for": minutos*60000}`, depois lê); `voltar(): Promise<Leitura>` (`PUT /pause {"pause": false}`, depois lê); outro valor de minutos → `Error("tempo de pausa não permitido")` sem pedido nenhum.
  - `Leitura` = `{ok:true, quando, pausado, pausaAte, moeda, computador, cotacoes:{brl, btc}, saldoBtc, placas:[Placa], desconhecidos:[string]}` ou `{ok:false, erro:"fechado"|"tempo"|"formato", msg}`.
  - `Placa` = `{id, tipo:"gpu"|"cpu", nome, desativada, minerando, moeda, algoritmo, minerador, hash, rendimentoUsd, temp, tempMem, tempHot, watts, ventoinha, rpm, erros1h}`.
  - Campos da leitura: `temp` ← `core_temperature`|`temperature`|`gpu_temperature`|`temperature_gpu`; `tempMem` ← `memory_temperature`|`temperature_memory`|`mem_temperature`|`vram_temperature`; `tempHot` ← `hotspot_temperature`|`junction_temperature`|`temperature_hotspot`; `watts` ← `power_usage`|`power_draw`|`power`|`watts`|`board_power`|`power_consumption`; `ventoinha` ← `fan_speed_percent`, ou `fan_speed` quando ≤ 100; `rpm` ← `fan_speed_rpm`, ou `fan_speed` quando > 100. Zero, negativo ou não número → `null`. Os outros nomes numéricos de `reading` vão para `desconhecidos` (só o nome).
  - Minerador ativo: entre todas as `algorithm_combinations[].miners[]`, o de maior `Σ coin_algorithms[].(local_hashrate||hashrate)`, valendo só se esse total for > 0 ou `stats.process_count > 0`. `hash` = esse total; `rendimentoUsd` = `stats.profitability` dele (ou a soma dos `coin_algorithms[].profitability`); sem minerador ativo, `rendimentoUsd` = o maior `profitability` entre todos (o esperado) e `hash` = 0. `minerando = ativo && !pausado && !desativada`.
  - `pausaAte`: de `/pause`, o primeiro de `pause_until`|`paused_until`|`until`|`resume_at` (número em s ou ms, ou data ISO) → ms; senão `null`.
  - Nunca devolve nada de `/user`, e-mail, token ou nome de usuário (não pede `/user`).
- Produz no `main.js`: `ipcMain.handle("kryptex-app", doPainel((op, minutos) => ...))` com `op` ∈ `ler|pausar|voltar`.
- Produz no `preload.js`: `kryptexApp: { ler(), pausar(minutos), voltar() }`.
- Produz `desktop/scripts/kryptex-falso.js`: `module.exports = () => ({ estado, pedidos, tratar(req, res, caminho) })`, com `estado = {modo:"minerando"|"pausado"|"quente"|"parado"|"fechado", saldo, temp, tempMem, watts, pausaAte}` e `pedidos` = lista de `{metodo, caminho, corpo}`; em `"fechado"` não responde (o teste usa o limite de 4 s); `PUT /pause` muda o `modo`.

- [ ] **Passo 1: Escrever `desktop/scripts/teste-kryptex-app.js`** (sobe o falso numa porta livre, `process.env.PAINEL_KRYPTEX_LOCAL = base`, e confere com `assert`):

```js
const l = await K.ler();
assert(l.ok && l.placas.length === 2 && l.placas[0].tipo === "gpu" && l.placas[0].minerando);
assert.equal(l.placas[0].temp, 63); assert.equal(l.placas[0].tempMem, 78); assert.equal(l.placas[0].watts, 286);
assert.equal(l.placas[0].moeda, "PRL"); assert.equal(l.placas[0].minerador, "srbminer");
assert(!JSON.stringify(l).includes("alex.teste@example.com"));          // o falso põe e-mail em /user e em campos extras
assert(l.desconhecidos.includes("campo_novo_qualquer"));
await assert.rejects(K.pausar(7), /não permitido/); assert.equal(falso.pedidos.filter(p => p.metodo === "PUT").length, 0);
const ultimoPut = () => JSON.parse(falso.pedidos.filter(p => p.metodo === "PUT").at(-1).corpo);
const p = await K.pausar(60); assert(p.pausado); assert.deepEqual(ultimoPut(), { pause_for: 3600000 });
const v = await K.voltar(); assert(!v.pausado); assert.deepEqual(ultimoPut(), { pause: false });
assert(falso.pedidos.every(p => p.metodo === "GET" || p.caminho === "/pause"));   // nenhuma outra ação
falso.estado.modo = "pausado"; const lp = await K.ler(); assert(lp.pausado && !lp.placas[0].minerando);   // hashrate velho, mas pausado
falso.estado.modo = "fechado"; const f = await K.ler(); assert(!f.ok && f.erro === "tempo");
process.env.PAINEL_KRYPTEX_LOCAL = "http://127.0.0.1:1"; const fe = await K.ler(); assert(!fe.ok && fe.erro === "fechado");
```

- [ ] **Passo 2: Rodar e ver falhar** — Run: `node desktop/scripts/teste-kryptex-app.js` · Expected: FAIL (`Cannot find module '../kryptex-app.js'`).
- [ ] **Passo 3: Implementar** `kryptex-app.js`, o canal e a ponte. A resposta de `/devices` do falso segue o formato real (ver a especificação, seção 3; os campos de temperatura de memória e watts do falso usam `memory_temperature` e `power_usage`).
- [ ] **Passo 4: Rodar e ver passar** — Run: `node desktop/scripts/teste-kryptex-app.js && node desktop/scripts/teste-sincronia.js` · Expected: "ok" nos dois.
- [ ] **Passo 5: Commit** ("Leitura do app da Kryptex no aplicativo, com app de mentira para os testes")

---

### Task 5: Painel do PC: ao vivo, ganho e luz de hoje, avisos, proteção e Premissas › App da Kryptex

**Arquivos:**
- Modificar: `mineracao.html` (bloco novo logo depois do bloco da conta da Kryptex, `:4813`; `renderAgora`, `renderVivo`; `SINCRONIZADAS` em `:1406`; `recarregarDados` em `:4846`; Premissas: painel `#kxa-p` dentro do grupo "Kryptex", ao lado de `#kx-p`)
- Modificar: `desktop/sincronia.js` (`SINCRONIZADAS` igual)
- Criar: `testes/kryptex_app.py`

**Interfaces:**
- Consome: `window.desktop.kryptexApp.*` e `Leitura` (Tarefa 4); `avisoKx(tipo, titulo, corpo)`, `salvarKx(antes)`, `impressaoKx()`, `registrarSaldo(s)`, `calcularDiasKx()`, `tarifaEf()` (já existem); `renderAgora()` (Tarefa 3).
- Produz:
  - `kxaCfg() -> {ligado, protecao, limTemp, limMem}` de `cfg.kxa`, padrão `{ligado:true, protecao:true, limTemp:85, limMem:100}`; `mudarKxaCfg(o)`.
  - `var kxa` = `{leitura, quando, ultimaOk, jaRespondeu, estado:"minerando"|"pausada"|"parada"|"fechado"|"", minerandoDesde, quentes, ultimaProtecao, protecao:{ate, motivo}|null, semMinerar:{[id]:n}, avisouParou:{[id]:bool}, avisouFechado, ultimoSaldo, gravado}`; `var kxaHist` = `{amostras:[[t, saldoBtc, watts, minerando, hash, temp, tempMem]]}` em `min-kxa-hist` (36 h, até 2200).
  - `async lerKryptexApp(motivo?: "manual"|"celular") -> void` (a cada 60 s por `setInterval`, só com `DESKTOP && window.desktop.kryptexApp && kxaCfg().ligado`).
  - `hojeKxa(amostras, agora, tarifa, precoBrl) -> {ganho, luz, lucro, kwh, desde, linha:[[t, reais]]}` (algoritmo abaixo).
  - `deveProteger(est, leitura, cfg, agora) -> null | {minutos, motivo}` (algoritmo abaixo).
  - `estadoKxa(leitura) -> "minerando"|"pausada"|"parada"|"fechado"`.
  - `retratoKxa() -> {v:1, quando, estado, pausaAte, computador, placas:[{nome, tipo, minerando, moeda, minerador, hash, temp, tempMem, watts, ventoinha, rpm}], hoje:{ganho, luz, lucro, kwh, desde}, ritmo:{brutoDia, lucroDia}, saldoBtc, precoBtc, linha:[[t, reais]] (até 48 pontos), protecao}`; `gravarKxa(forcar?: boolean)` grava `min-kx-app` pelas regras de Global Constraints.
  - `async pausarKryptex(minutos)`, `async voltarKryptex()` (chamam a ponte, guardam a leitura que volta, gravam o retrato; erro ou `{ok:false}` → mensagem em `#ag-status`, `role="status"`, e o estado fica o da próxima leitura).
  - Depois de cada leitura: `renderAgora()`, `renderVivo()` e, se houve aviso, `renderAvisos()`.
  - `renderAgora()` ao vivo: selo (Minerando / Pausada até HH:MM / Parada / App da Kryptex fechado), "Moeda com minerador · há X h Y min", "Hoje até agora" (e "desde HH:MM" quando parcial), "lucro de R$ X depois da luz", a linha do dia (SVG, `role="img"` com o resumo), 4 números (hashrate agora e média de 24 h; temperatura do núcleo e da memória; consumo em W e luz de hoje; ventoinha em % e rpm), `details.pausar` com 1 hora, 3 horas, 8 horas, Até eu voltar (`data-pausa="60|180|480|44640"`) ou "Voltar a minerar" (`data-voltar`), e a linha da proteção ("Pausa sozinha com a placa a 85 °C ou a memória a 100 °C" ou "Proteção de temperatura desligada").
  - `renderVivo()`: `#vivo` e `#g-chip` com o estado e o ganho de hoje quando há leitura (ao vivo ou retrato).
  - Premissas › `#kxa-p`: interruptor "Ler o app da Kryptex deste PC", interruptor da proteção, os dois limites (°C), "lido há X" e "Copiar o que o painel leu" (a leitura sem `computador`, com os `desconhecidos`).

`hojeKxa`: `ini` = meia-noite local de `agora`. Base = a última amostra com `ini-30min ≤ t < ini`; sem ela, a primeira com `t ≥ ini`. `desde` = `base.t` se `base.t > ini+30min`, senão `null`. Ganho em BTC = soma de `max(0, saldo[i] - saldo[i-1])` das amostras com saldo, da base em diante (um saque não desconta). `kwh` = soma, nas amostras com `t ≥ ini`, de `watts × min(próxima.t (ou agora) - t, 5 min)`; amostra sem `watts` e minerando usa `totaisSetup({}).tomada`. `luz = kwh × tarifa`, `ganho = ganhoBtc × precoBrl`, `lucro = ganho - luz`. `linha` = o ganho acumulado em reais em cada amostra.

`deveProteger`: sem `cfg.protecao`, leitura com falha ou pausada → `est.quentes = 0`, `null`. Quente = alguma GPU minerando com `temp ≥ limTemp` ou `tempMem ≥ limMem`. `est.quentes` soma 1 se quente, senão zera; menos de 2 → `null`. Com 2: zera `quentes`; `longa = est.ultimaProtecao && agora - est.ultimaProtecao < 2 h 15 min`; `est.ultimaProtecao = agora`; devolve `{minutos: longa ? 44640 : 15, motivo: "<nome> a <temp> °C (limite <limTemp> °C)"}` (ou o da memória).

Avisos (por `avisoKx`): `parou` quando uma placa que minerava fica 3 leituras seguidas sem minerar, sem pausa (o contador zera se a leitura anterior foi há mais de 10 min); `voltou` depois de um `parou`; `fechado` quando `jaRespondeu` e `agora - ultimaOk ≥ 5 min` (uma vez, até responder de novo); `quente` quando a proteção pausa ("Pausei a mineração: …", "Volta sozinha às HH:MM" ou "Fica pausada até você voltar pelo painel"). Saldo para o Diário: com `saldoBtc` e `precoBrl`, no máximo a cada 15 min, `registrarSaldo({btc, fiat: btc*precoBrl, moeda:"BRL", preco: precoBrl})`, `calcularDiasKx()` e `salvarKx(antes)`.

- [ ] **Passo 1: Escrever `testes/kryptex_app.py`** (página `abrir(p, pc=True)`, cujo `kryptexApp` devolve as leituras de `window.__leituras` e guarda `pausar`/`voltar` em `window.__acoes`). Leituras de exemplo do próprio teste: `MIN` (RX 9070 XT minerando Pearl com SRBMiner, 63 °C, memória 78 °C, 286 W, ventoinha 54%), `PARADO` (sem minerar, sem pausa), `PAUSADO_COM_HASH` (pausado, ainda com hashrate), `QUENTE` (86 °C), `FALHA` (`{ok:false, erro:"tempo"}`). `simularLeituras(lista)` recebe itens `[minutos desde o início, leitura]` (ou só a leitura, um minuto depois da anterior), troca `Date.now` pelo relógio do teste, chama `lerKryptexApp()` uma vez por item e devolve `{estado, alertas:[tipos], acoes:[["pausar", minutos]]}`; `contarGravacoes(lista)` faz o mesmo e devolve quantas vezes `min-kx-app` foi gravado.

```python
# hoje_com_saque: saldo 0,00010 → 0,00012 → (saque) 0,00002 → 0,00003
h = pg.evaluate("hojeKxa(AMOSTRAS_SAQUE, AGORA, 1.0, 400000)")
checa("hoje_com_saque", abs(h["ganho"] - 0.00003 * 400000) < 1e-6 and h["ganho"] > 0, h)
# buraco_nao_avisa: a leitura anterior foi há 6 h (PC dormiu) → o contador de parada recomeça; luz conta no máximo 5 min por leitura
checa("buraco_nao_avisa", pg.evaluate("simularLeituras([[0, MIN], [360, PARADO], [361, PARADO]]).alertas") == [])
checa("luz do buraco", abs(pg.evaluate("hojeKxa([[AGORA-6*3600e3, 0.0001, 286, 1, 1, 63, 78], [AGORA, 0.0001, 286, 1, 1, 63, 78]], AGORA, 1.0, 400000).kwh") - 0.286 * 5/60) < 1e-6)
# pausado_nao_avisa: pausado com hashrate velho
checa("pausado_nao_avisa", pg.evaluate("simularLeituras([MIN, PAUSADO_COM_HASH, PAUSADO_COM_HASH, PAUSADO_COM_HASH])") == {"estado": "pausada", "alertas": [], "acoes": []})
# parou e voltou
checa("parou_voltou", pg.evaluate("simularLeituras([MIN, PARADO, PARADO, PARADO, MIN]).alertas") == ["parou", "voltou"])
# proteção: 2 leituras a 86 °C → pausar 15; esquenta de novo 1 h depois de voltar → 44640
checa("protecao_15", pg.evaluate("simularLeituras([QUENTE, QUENTE]).acoes") == [["pausar", 15]])
checa("protecao_longa", pg.evaluate("simularLeituras([[0, QUENTE], [1, QUENTE], [16, MIN], [76, QUENTE], [77, QUENTE]]).acoes") == [["pausar", 15], ["pausar", 44640]])
checa("protecao_desligada", pg.evaluate("mudarKxaCfg({protecao:false}), simularLeituras([QUENTE, QUENTE]).acoes") == [])
# fechado: respondia, 5 min sem resposta → 1 aviso
checa("fechado", pg.evaluate("simularLeituras([[0, MIN], [1, FALHA], [3, FALHA], [6, FALHA], [7, FALHA]]).alertas") == ["fechado"])
# retrato: gravado ao mudar de estado e a cada 30 min, não a cada leitura (60 leituras, uma por minuto)
checa("retrato", pg.evaluate("contarGravacoes(Array(60).fill(MIN))") == 2)
# tela: Agora ao vivo e pausar pelo botão
pg.click('details.pausar summary'); pg.click('[data-pausa="60"]')
checa("pausar pelo botão", pg.evaluate("window.__acoes") == [["pausar", 60]])
checa("tela ao vivo", all(s in pg.inner_text("#agora") for s in ["Minerando", "Pearl", "286 W", "63 °C"]))
checa("sem erros no console", not erros)
```

(`simularLeituras` e `contarGravacoes` são funções do próprio teste, injetadas por `page.evaluate`, que trocam `Date.now` pelo relógio do teste e chamam `lerKryptexApp()` uma vez por leitura.)

- [ ] **Passo 2: Rodar e ver falhar** — Run: `python3 testes/kryptex_app.py` · Expected: FAIL (`hojeKxa is not defined`).
- [ ] **Passo 3: Implementar.**
- [ ] **Passo 4: Rodar e ver passar** — Run: `python3 testes/kryptex_app.py && python3 testes/visual.py && node desktop/scripts/teste-sincronia.js` · Expected: tudo OK.
- [ ] **Passo 5: Commit** ("Painel do PC lê o app da Kryptex: ao vivo, ganho de hoje, avisos e proteção de temperatura")

---

### Task 6: Celular: retrato, Atualizar, pausar e voltar pelo PC

**Arquivos:**
- Modificar: `mineracao.html` (`executarPedidoRemoto` em `:4883`: os três pedidos antes do teste de `ocupado()`; `renderAgora` no celular; botões)
- Modificar: `desktop/main.js:658` (`APP_PEDIDOS` com `kryptex-agora`, `kryptex-pausar`, `kryptex-voltar`), `celular/src/ponte-app.js:316` (`LIMITE` desses três: 60 s)
- Testar: `testes/kryptex_app.py`

**Interfaces:**
- Consome: `retratoKxa`, `gravarKxa`, `pausarKryptex`, `voltarKryptex`, `lerKryptexApp` (Tarefa 5); `pedirAoPc(nome, args)`.
- Produz: no PC, `executarPedidoRemoto({nome:"kryptex-agora"})` lê agora e grava o retrato (forçado); `{nome:"kryptex-pausar", args:{minutos}}` só com 60, 180, 480 ou 44640; `{nome:"kryptex-voltar"}`. Todos devolvem `{ok, texto}`.
- Produz: no celular, `kxaSnap` (de `min-kx-app`, recarregado em `recarregarDados`); `pedirRetrato(motivo: "auto"|"botao")` com as esperas de Global Constraints; Agora com "lido há X min" e o botão Atualizar; com retrato de mais de 15 min, o selo vira "Última leitura há X" em `--muted` e os números ficam com a hora da leitura.

- [ ] **Passo 1: Escrever os testes** (em `testes/kryptex_app.py`, página de celular com `pedirAoPc` de mentira):

```python
pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO_DE_ONTEM)); recarregarDados(['min-kx-app'])")
t = pgc.inner_text("#agora")
checa("retrato_velho", "Última leitura há" in t and "Minerando" not in t, t[:200])
checa("pediu sozinho uma vez", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 1)
pgc.evaluate("irPara('diario'); irPara('resumo')")
checa("não repete antes de 10 min", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 1)
pgc.click('details.pausar summary'); pgc.click('[data-pausa="180"]')
checa("pausar pelo PC", pgc.evaluate("window.__pedidos.at(-1)") == ["kryptex-pausar", {"minutos": 180}])
# no PC: pedido inválido e pedido no meio de uma busca
checa("minutos inválidos", pg.evaluate("executarPedidoRemoto({nome:'kryptex-pausar', args:{minutos:7}})")["ok"] is False)
checa("atende mesmo ocupado", pg.evaluate("ofEst.rodando = true, executarPedidoRemoto({nome:'kryptex-voltar'})")["ok"] is True)
```

- [ ] **Passo 2: Rodar e ver falhar.**
- [ ] **Passo 3: Implementar.**
- [ ] **Passo 4: Rodar e ver passar** — Run: `python3 testes/kryptex_app.py && node desktop/scripts/teste-sincronia.js` · Expected: OK.
- [ ] **Passo 5: Commit** ("Celular: mineração ao vivo pelo retrato do PC, atualizar, pausar e voltar")

---

### Task 7: Ofertas com foto, cartões novos, fichas e gráfico de preço × tempo para se pagar

**Arquivos:**
- Modificar: `desktop/main.js:1064-1103` (`paginaBuscaFb` devolve `foto` de `a.querySelector("img")`; `paginaBuscaOlx` devolve `foto` de `img.currentSrc || img.src || img.dataset.src` do card)
- Modificar: `mineracao.html:3809-3825` (`anuncioFb`/`anuncioOlx` guardam `foto: fotoValida(it.foto)`), `:4068-4093` (`htmlOferta`), `:4117-4147` (`renderOfertas`), `:771-836` (filtros como fichas, gráfico `#of-graf`, explicação longa num "Saiba mais"), CSS das ofertas (`:573-638`)
- Modificar: `desktop/scripts/gerar-index.py` e `celular/scripts/montar-www.py` (`img-src 'self' data: https://*.fbcdn.net https://*.olx.com.br` e, no app, `blob:`)
- Modificar: `desktop/scripts/teste.js:66-87` (cards de mentira com `<img src="https://scontent.teste.fbcdn.net/...">` e `<img src="https://img.olx.com.br/thumbs/...">`)
- Testar: `testes/visual.py`

**Interfaces:**
- Produz: `fotoValida(u) -> string` (o endereço, ou `""` se não for https, de host fora de `*.fbcdn.net`/`*.olx.com.br`, ou com mais de 1200 caracteres).
- Produz: `htmlOferta` novo: dentro de `article.of[data-k]`, `.of-img` (a foto `img.of-foto[loading=lazy][referrerpolicy=no-referrer][alt=""]` sobre o desenho da placa; o site em `.of-site`; o botão Salvar `[data-of="salvar"]` por cima), depois modelo e selo, `a.of-tit`, cidade e distância, `.of-preco` (com `s` do preço antigo), lucro por mês e quanto está abaixo do típico (`precoTipico(c)`), `.of-ret` com `.pill` e a barra do tempo para se pagar contra `cfg.meses` (a marca do prazo em `cfg.meses / (cfg.meses*1.5)`), e `.of-acoes` (Falar com o vendedor, Analisar, e um `details` Mais com Ver detalhes e Descartar). Os `data-of` de hoje continuam.
- Produz: um ouvinte `error` no `document` (fase de captura) que esconde `img.of-foto` que falhar.
- Produz: `renderGrafOfertas(linhas)` em `#of-graf`: SVG com um ponto por anúncio da lista filtrada (x = preço, y = meses; círculo cheio `--good` para "compensa", anel `--warn` para "apertado", X `--bad` para "não compensa"), faixa `--good-soft` até `cfg.meses`, nome nos 3 primeiros, dica ao passar o mouse ou focar (`.pt-hit` com `tabindex=0`), clique leva ao cartão (`.of.destaque` por 2 s) e `aria-label` com o resumo.
- Produz: filtros de hoje (`#of-so-compensa`, `#of-sem-troca`, `#of-salvos`, `#of-desc`, `#of-modelo`, `#of-ordem`) com a mesma lógica, desenhados como fichas numa linha que rola de lado no celular.

- [ ] **Passo 1: Escrever os testes `ofertas` e `foto_quebrada`**

```python
pgc = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="ofertas")
checa("cartões", pgc.eval_on_selector_all("#of-lista .of", "e=>e.length") == DADOS_ESPERADO["ofertas_filtradas"])
checa("foto válida", pgc.evaluate("[fotoValida('https://scontent-gru2-1.xx.fbcdn.net/v/t45/a.jpg'), fotoValida('http://x.fbcdn.net/a.jpg'), fotoValida('https://evil.com/a.jpg'), fotoValida('https://img.olx.com.br/thumbs/a.jpg')]") == ["https://scontent-gru2-1.xx.fbcdn.net/v/t45/a.jpg", "", "", "https://img.olx.com.br/thumbs/a.jpg"])
checa("sem foto: desenho", pgc.evaluate("[...document.querySelectorAll('#of-lista .of')].filter(a=>!a.querySelector('img.of-foto')).length") == DADOS_ESPERADO["ofertas_sem_foto_visiveis"])
pgc.wait_for_timeout(800)   # as fotos de teste apontam para hosts que não respondem
checa("foto_quebrada", pgc.evaluate("[...document.querySelectorAll('img.of-foto')].every(i=>i.hidden)") and not erros(pgc))
checa("gráfico", pgc.eval_on_selector_all("#of-graf .pt-hit", "e=>e.length") == DADOS_ESPERADO["ofertas_filtradas"])
pgc.focus("#of-graf .pt-hit"); checa("dica", pgc.is_visible("#of-graf .tip"))
pgc.click("#of-graf .pt-hit"); checa("leva ao cartão", pgc.evaluate("!!document.querySelector('.of.destaque')"))
pgc.evaluate("document.getElementById('of-so-compensa').click()"); checa("filtro muda o gráfico", pgc.eval_on_selector_all("#of-graf .pt-hit", "e=>e.length") == 12)
checa("seletores antigos", pgc.evaluate("!!document.querySelector('#of-lista .of .of-tit') && !!document.querySelector('.of-ret .pill')"))
checa("sem rolagem lateral", pgc.evaluate("document.documentElement.scrollWidth <= innerWidth"))
```

- [ ] **Passo 2: Rodar e ver falhar.**
- [ ] **Passo 3: Implementar.**
- [ ] **Passo 4: Rodar e ver passar** — Run: `python3 testes/visual.py && python3 desktop/scripts/gerar-index.py mineracao.html && grep -o "img-src[^;]*" desktop/app/index.html` · Expected: OK; `img-src 'self' data: https://*.fbcdn.net https://*.olx.com.br`.
- [ ] **Passo 5: Commit** ("Ofertas com foto, cartões novos e gráfico de preço × tempo para se pagar")

---

### Task 8: As outras telas no visual novo

**Arquivos:**
- Modificar: CSS de `mineracao.html` (painéis com canto de 16 px, cabeçalhos, botões `.pri` com `--accent`/`--onaccent`, campos, tabelas, selos `.pill`/`.estado`/`.of-tags li` com ícone além da cor), os textos longos de cabeçalho (`.vh .sub` de no máximo uma frase) e os blocos `.note` e explicações longas de Ofertas, Todas as placas e Premissas dentro de `details.saiba` ("Saiba mais")
- Testar: `testes/visual.py`

**Interfaces:**
- Consome: as variáveis e fontes da Tarefa 1.
- Produz: `details.saiba > summary` ("Saiba mais") para as explicações; `.pill` com um ícone (`::before`) por classe (`g` ✓, `w` !, `b` ×).

- [ ] **Passo 1: Escrever o teste `telas`**: para cada tela em `VIEWS`, nos dois temas, em 1366 e em 390 px: nenhuma rolagem lateral; nenhum `.sub` de cabeçalho com mais de 160 caracteres; contraste ≥ 4.5 do texto de `.sub`, `.lbl`, `.hint` e `.pill` com o fundo do painel; nenhuma cor fixa fora das variáveis no CSS (`re.findall(r"#[0-9a-fA-F]{3,6}\b", css_sem_root)` vazio, fora o QR code em `.appcel-codigo`).
- [ ] **Passo 2: Rodar e ver falhar.**
- [ ] **Passo 3: Implementar** (conteúdo e cálculos não mudam; só aparência e o lugar dos textos longos).
- [ ] **Passo 4: Rodar e ver passar**, e tirar fotos das 8 telas nos dois temas (`testes/visual.py --fotos <pasta>`) para olhar.
- [ ] **Passo 5: Commit** ("Todas as telas no visual novo")

---

### Task 9: Teste de ponta a ponta, novidades, versão 1.6.0 e documentação

**Arquivos:**
- Modificar: `desktop/scripts/teste.js` (app da Kryptex de mentira: `require("./kryptex-falso.js")` no mesmo servidor, em `/kxapp`, e `process.env.PAINEL_KRYPTEX_LOCAL = base + "/kxapp"`; passos novos em `r.kxApp`; `irPara("premissas")` onde hoje abre o Resumo para a conta da Kryptex; fotos das ofertas)
- Modificar: `mineracao.html` (`NOVIDADES` 1.6.0 no começo), `notas/v1.6.0.md`, `CLAUDE.md` (arquivo `kryptex-app.js`, `min-kx-app`, `min-kxa-hist`, `min-tema`, pedidos novos, testes novos), `desktop/package.json` e lock (1.6.0), `celular/package.json` e lock (1.6.0)

**Interfaces:**
- Consome: tudo das Tarefas 1 a 8.

- [ ] **Passo 1: Escrever os passos novos do `teste.js`**: com o app de mentira minerando, `r.kxApp.leu` (estado "minerando", 286 W, 63 °C em `#agora`); clique em Pausar 1 hora → o falso recebeu `{"pause_for":3600000}` e `#agora` diz "Pausada até"; Voltar → `{"pause":false}`; modo "quente" por 2 leituras → `{"pause_for":900000}` e uma notificação "Pausei a mineração"; modo "parado" por 3 leituras → notificação "parou de minerar"; modo "fechado" por 5 min de relógio → notificação "O app da Kryptex não está respondendo"; pedido do celular `kryptex-pausar` pelo app (a sincronia de mentira) → o falso recebeu `{"pause_for":10800000}`; `min-kx-app` chegou ao celular; as ofertas de mentira têm `foto`.
- [ ] **Passo 2: Rodar o teste de ponta a ponta** — Run (em `desktop/`): `PAINEL_TESTE=1 PAINEL_DADOS=<pasta vazia> PAINEL_SAIDA=<pasta> PAINEL_FIXOS=<rascunho>/dados PAINEL_DESCANSO=20000 PAINEL_SINAL_MS=2000 PAINEL_PORTA=27777 PAINEL_CAMERA=<pasta>/camera.y4m XDG_CACHE_HOME=<pasta> xvfb-run -a ./node_modules/.bin/electron . --no-sandbox` · Expected: `teste-desktop.json` com `r.kxApp` todo certo e o resto igual ao da 1.5.0 (comparar com a rodada t155; mudam só valores que já variavam: `mandar`, `recusadasNoPc`).
- [ ] **Passo 3: Versão, novidades, notas e CLAUDE.md**; montar o instalador (`node desktop/scripts/build-win.js`) e o app (`montar-www.py`, `npx cap sync android`, `./gradlew assembleRelease` com a chave de teste) para conferir que montam.
- [ ] **Passo 4: Rodar tudo de novo** — `python3 testes/visual.py && python3 testes/kryptex_app.py && node desktop/scripts/teste-kryptex-app.js && node desktop/scripts/teste-sincronia.js` e as suítes antigas · Expected: OK.
- [ ] **Passo 5: Commit** ("Versão 1.6.0: novo visual e o app da Kryptex") e push da branch `visual-1.6.0` (não do `main`).

---

### Task 10: Revisão e publicação (com o OK do Alex)

- [ ] **Passo 1:** revisão da branch inteira por um revisor que não escreveu o código; corrigir o que ele achar.
- [ ] **Passo 2:** mandar ao Alex as fotos das telas e perguntar se pode publicar. Sem OK, parar aqui.
- [ ] **Passo 3:** com o OK: merge no `main` e push; acompanhar `repos/AlexsAzevedo/painel-mineracao/commits/<sha>/check-runs`; conferir a release com `scripts/conferir-versao.sh 1.6.0` (sha512, instalador sem dados pessoais, APK assinado com a mesma chave, rótulo "app 1.6.0").
- [ ] **Passo 4:** publicar de novo o painel online no artifact `https://claude.ai/artifact/Nu8cNXUvFJKtnFFPBWFY9A` (com `url`).
- [ ] **Passo 5:** segunda, com a placa minerando: ler `localhost:8107/devices` (só GET) para acertar os nomes de temperatura de memória e consumo em `kryptex-app.js`, e ver se a porta 8107 responde de outro aparelho da rede (se responder, avisar o Alex).
