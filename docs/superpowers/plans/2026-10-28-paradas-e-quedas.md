# Paradas e quedas de energia (1.10.0) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o painel do PC anota cada parada da mineração (queda de energia, PC desligado, suspensão, app fechado, placa parada, pausas) com o motivo, desconta as paradas das horas do dia no Diário e mostra no Diário, numa lista, no Resumo e no celular quanto deixou de ganhar.

**Architecture:**
- **No programa do PC,** um módulo pequeno (`desktop/energia.js`) anota num arquivo quando o Windows ligou, desligou normalmente, suspendeu e acordou. A página pergunta essas marcas por `window.desktop.energia()`.
- **Na página,** cada leitura de minuto do app da Kryptex guarda o estado. Uma função pura (`paradasDasAmostras`) calcula as paradas a partir das leituras e das marcas, e `atualizarParadas` junta o resultado com as paradas guardadas na chave nova `min-paradas`, que o PC grava e o celular recebe.
- **As contas** (horas do dia, ritmo da conta, quanto deixou de ganhar) e as telas leem `min-paradas`.

**Tech Stack:** HTML/JS de uma página só (`mineracao.html`), Electron 44 (`desktop/`), Playwright em Python (`testes/`), Node (`desktop/scripts/`).

**Spec:** `docs/superpowers/specs/2026-10-28-paradas-e-quedas-design.md`

## Global Constraints

- **O que olha:** só este PC (onde o painel lê o app da Kryptex). O valor recebido de cada dia e o relatório do ano não mudam.
- **Rótulos dos motivos** (exatos): `energia` "Falta de energia?", `desligado` "PC desligado", `suspensao` "PC em suspensão", `fechado` "App da Kryptex fechado", `parada` "Placa parada", `pausa` "Pausada por você", `protecao` "Pausada pela proteção de temperatura", `semleitura` "Sem leitura (PC desligado ou sem energia)", `semminerar` "Sem minerar (motivo não registrado)".
- **Frases dos motivos** (exatas):
  - `energia` "o PC apagou de repente (falta de energia?) e ligou às {hh:mm}";
  - `desligado` "o PC foi desligado e ligou às {hh:mm}";
  - `suspensao` "o PC ficou em suspensão";
  - `fechado` "o app da Kryptex ficou fechado";
  - `parada` "a placa ficou parada";
  - `pausa` "a mineração ficou pausada por você";
  - `protecao` "a mineração ficou pausada pela proteção de temperatura";
  - `semleitura` "o PC ficou sem leitura (desligado ou sem energia)";
  - `semminerar` "a placa ficou sem minerar".

  Sem a hora em que ligou, `energia` e `desligado` terminam antes de " e ligou às".
- **Formatos:**
  - Durações pelo `duracao(ms)` do painel: "45 min", "6 h", "6 h 10 min".
  - Valores: "uns " + `brl(v)`.
  - Horários: `horaMin(t)`, com "~" na frente quando a parada é aproximada (`aprox`).
- **Limites:**
  - **Buraco:** mais de `KXA_BURACO` (10 min) entre duas leituras, ou uma marca `ligou` entre elas.
  - **Paradas curtas:** menos de 10 min (`PARADA_MIN`) não entram, menos `energia`.
  - **PC religou e a placa não voltou:** o aviso sai 15 min depois de ligar.
  - **Saldos antigos:** buracos de mais de 45 min viram parada só quando o saldo cresceu menos que a metade do ritmo × o buraco.
- **Guardar:** `min-paradas` = `{v: 1, retro: boolean, lista: [{ini, fim, ligou, motivo, aprox, ritmo, avisoLigou}]}`.
  - Guarda 365 dias (pelo `fim`, ou agora sem fim) e no máximo 1000 paradas.
  - Só o PC grava, e só quando a lista muda.
  - `min-paradas` fica igual na `SINCRONIZADAS` de `mineracao.html` e de `desktop/sincronia.js`.
- **Avisos:**
  - Um por parada, quando ela acaba (nesta leitura: `agora − fim ≤ 3 min`).
  - Nenhum para `pausa`, para as paradas antigas nem para as curtas. As curtas continuam com o "voltou" de hoje.
- **Versões:** a do programa do PC vai para 1.10.0. O app do celular continua na 1.8.0 (nada em `celular/android` muda; `conferir-nativo.py` passa).
- **Tela:** celular a 390 px, sem rolagem para o lado, botões de 44 px; claro e escuro; sem NaN, Infinity ou undefined.
- **Publicar:** a release (push no `main`) e o painel online (artifact Nu8cNXUvFJKtnFFPBWFY9A) só depois do OK do Alex.

## Review Focus

1. **Página recarregada no meio de uma parada,** como na atualização do painel ou no painel reaberto. A parada continua com o mesmo início, e o aviso de fim não se repete. Teste na Tarefa 6.
2. **Duas quedas de energia nas mesmas 36 horas.** Cada buraco usa a marca `ligou` que caiu dentro dele. Teste na Tarefa 2.
3. **Parada mais longa que as 36 horas de leituras,** como a placa parada por 2 dias. O início e o motivo guardados ficam. Teste na Tarefa 2.
4. **Página sem o PC** (painel online, ou celular sem paradas). Sem erro; o painel online não mostra a lista e o celular mostra "Nenhuma parada neste período". Teste na Tarefa 5.
5. **Leituras repetidas no mesmo minuto** ("Ler agora", o Atualizar do celular). Nenhuma parada de duração zero, e nada quebra. Teste na Tarefa 2.

## Mapa dos arquivos

- **Criar:**
  - `desktop/energia.js`: as marcas de energia do PC;
  - `desktop/scripts/teste-energia.js`;
  - `testes/paradas.py`: todos os testes da página desta versão;
  - `notas/v1.10.0.md`.
- **Mudar:**
  - `desktop/main.js` e `desktop/preload.js`: a ponte, as marcas e o "O PC voltou";
  - `desktop/sincronia.js`: a `SINCRONIZADAS`;
  - `mineracao.html`: as leituras, as paradas, as contas, o Diário, o Resumo, os avisos e as `NOVIDADES`;
  - `desktop/package.json` e `desktop/package-lock.json`: a versão;
  - `CLAUDE.md`.

---

### Task 1: O programa do PC anota a energia

**Files:**
- Create: `desktop/energia.js`, `desktop/scripts/teste-energia.js`
- Modify: `desktop/main.js` (a criação no `app.whenReady`, `session-end`, `powerMonitor`, o IPC `energia`, `segundo-plano`, `verificarVolta`); `desktop/preload.js`

**Interfaces:**
- Produces:
  - `require("./energia.js").criar({arquivo, agora = () => Date.now(), uptime = () => os.uptime()})` devolve `{registrarLigou(): number, marcar(tipo): void, estado(): {desde: number, marcas: Array<{t: number, tipo: "ligou"|"desligou"|"suspendeu"|"acordou"}>}}`.
  - Na página: `window.desktop.energia()` (Promise do `estado()`) e `window.desktop.segundoPlano({bandeja, iniciar, kxa})`.
- O arquivo `energia.json` (pasta de dados) é `{v: 1, desde, marcas}`. `desde` é a criação do arquivo: o momento em que o painel começou a anotar.
- A spec cita uma marca para o "Sair" do painel. Ela **não** é gravada: sem o PC religar e sem suspensão, um buraco nunca vira parada, então a marca não mudaria nada.

- [ ] **Step 1: Escrever o teste** `desktop/scripts/teste-energia.js`, no estilo de `teste-sensores-amd.js` (assert, pasta temporária, imprime "ok" e sai com 1 na falha). Os testes, com o relógio de mentira `let t = 1.8e12; agora = () => t; let up = 3600; uptime = () => up`:
  - **Ligou:** `E.registrarLigou() === t - 3600e3`. Depois de `t += 60e3; up += 60`, `registrarLigou()` de novo continua com uma marca `ligou` só: mesma ligação (diferença até 120 s não repete).
  - **Marca no disco na hora:** `E.marcar("desligou")` aparece em `JSON.parse(fs.readFileSync(arquivo)).marcas` logo depois da chamada.
  - **Outra instância no mesmo arquivo:** `desde` e as marcas continuam.
  - **Ligou de novo:** `t += 7200e3; up = 120` → `registrarLigou()` grava uma segunda `ligou`, com `t: t - 120e3`.
  - **30 dias:** `t += 31*864e5` → `estado().marcas` não tem marca com mais de 30 dias.
  - **Máximo de 300:** 400 marcas → `estado().marcas.length <= 300`, ficando as mais novas.
  - **Tipo inválido:** `marcar("x")` não grava nada.
  - **Arquivo estragado:** com "{" no arquivo → `estado()` = `{desde: agora(), marcas: []}`.
  - **Sem conseguir gravar:** `arquivo` apontando para uma pasta → `marcar("desligou")` não lança.
  - **Fiação** (o texto dos arquivos):
    - `main.js` tem `ipcMain.handle("energia"`, `energia.registrarLigou()`, `energia.marcar("desligou")` no handler de `session-end`, `powerMonitor.on("suspend"` com `energia.marcar("suspendeu")`, `powerMonitor.on("resume"` com `energia.marcar("acordou")`, `segundoPlano.kxa = !!op.kxa` e `if (segundoPlano.kxa) return false` em `verificarVolta`;
    - `preload.js` tem `energia: () => ipcRenderer.invoke("energia")` e `kxa: !!op.kxa`.
- [ ] **Step 2: Rodar e ver falhar:** `node desktop/scripts/teste-energia.js` → `FALHOU: Error: Cannot find module '../energia.js'`.
- [ ] **Step 3: Implementar.**
  - **`energia.js`:**
    - Mantém o estado na memória e grava com `fs.writeFileSync`, porque o `session-end` dá pouco tempo; uma falha de escrita é engolida.
    - Corta as marcas por 30 dias e pelas 300 mais novas.
  - **`main.js`:**
    - Cria `energia` com `path.join(app.getPath("userData"), "energia.json")` dentro do `app.whenReady()`, antes de criar a janela, e chama `registrarLigou()`.
    - `powerMonitor` vem do `require("electron")`. Os handlers ficam depois do ready.
    - No `principal.on("session-end")`, `energia.marcar("desligou")` vem antes de `gravarPendentes()`.
    - O IPC `energia` usa a mesma guarda `deUmaJanelaNossa`.
    - O `segundo-plano` guarda `segundoPlano.kxa = !!op.kxa` (`gravarSegundoPlano()`).
    - O `verificarVolta()` volta `false` sem mandar quando `segundoPlano.kxa`; o painel manda o aviso completo.
    - Confira que `lerSegundoPlano()` roda antes de `iniciarCelular()`.
- [ ] **Step 4: Rodar e ver passar:** `node desktop/scripts/teste-energia.js` → `ok`; `node desktop/scripts/teste-sincronia.js` → `36/36 ok`.
- [ ] **Step 5: Commit:** `git add desktop/energia.js desktop/scripts/teste-energia.js desktop/main.js desktop/preload.js && git commit -m "Paradas: o programa do PC anota quando o Windows liga, desliga e suspende"`

### Task 2: As leituras com estado e as paradas

**Files:**
- Modify: `mineracao.html`
  - perto do bloco "app da Kryptex deste PC": `processarLeituraKxa`, `lerKryptexApp`, `hojeKxa`;
  - a `SINCRONIZADAS` e `recarregarDados`.
- Modify: `desktop/sincronia.js` (a `SINCRONIZADAS`)
- Create: `testes/paradas.py` (a função `deteccao(p)` e o fixture `FIX`)

**Interfaces:**
- Consumes: `window.desktop.energia()` (Tarefa 1).
- Produces:
  - **A leitura de minuto:** `[t, saldoBtc, watts, minerando, hash, temp, tempMem, tempHot, estado]`, com `estado` em `"m"|"u"|"t"|"p"|"f"`.
    - `"t"`: `l.pausado && kxa.protecao && (kxa.protecao.ate===0 || agora <= kxa.protecao.ate + 2*60e3)`.
    - `"u"`: pausado sem isso.
    - `"m"`: alguma placa minerando.
    - `"p"`: app aberto sem minerar.
    - `"f"`: o app não respondeu. A leitura fica `[agora, null, 0, 0, 0, null, null, null, "f"]` e entra também antes de `kxa.jaRespondeu`.
  - **As funções novas:**
    - `estadoAmostra(a) -> "m"|"u"|"t"|"p"|"f"|"?"`: `a[8]`, ou `a[3] ? "m" : "?"` nas leituras antigas.
    - `const PARADA_MIN = 10*60e3;`
    - `paradasDasAmostras(amostras, energia, agora) -> Array<{ini, fim, ligou, motivo, aprox: false}>`: pura, devolve **todos** os intervalos (sem o mínimo de 10 min).
    - `var paradas` (de `carregarParadas()`), `var energiaCache = null`, `async function lerEnergia()`.
    - `atualizarParadas(agora) -> {acabaram: Parada[], ligouSemMinerar: Parada|null}`.
  - `min-paradas` nas duas `SINCRONIZADAS`; `recarregarDados` faz `paradas = carregarParadas()`.

**O algoritmo de `paradasDasAmostras`** (leituras em ordem de `t`, uma leitura por vez; `atual` é a parada aberta):
- **Buraco entre a leitura anterior `a` e a atual `b`:** `b.t − a.t > KXA_BURACO`, ou uma marca `ligou` em `(a.t, b.t]`. O motivo:
  - sem `energia`, ou `a.t < energia.desde`: `semleitura`;
  - uma marca `ligou` em `(a.t, b.t]`: `desligado` se houver `desligou` em `[a.t, essa ligou]`, senão `energia` (e `ligou` = a hora dela);
  - senão, uma marca `suspendeu` em `[a.t, b.t]`: `suspensao`;
  - senão, `null` (painel fechado).
- **Buraco com motivo:**
  - com `atual`, ele passa a ter esse motivo, se o motivo do buraco for forte (`energia`, `desligado`, `suspensao`) e o de `atual` não for; e pega `ligou`, se ainda não tiver;
  - sem `atual`, cria `{ini: a.t, motivo, ligou}`.
- **Buraco sem motivo:** fecha `atual` em `a.t`.
- **Depois, a leitura `b`:**
  - `"m"` fecha `atual` em `b.t`;
  - outro estado sem `atual` abre `{ini: anterior minerando sem buraco ? a.t : b.t, motivo}`, pelo estado: `u`→`pausa`, `t`→`protecao`, `p`→`parada`, `f`→`fechado`, `?`→`semminerar`.
- **No fim:** `atual` sobra com `fim: null`.
- **Leituras com o mesmo `t`:** vale a última; uma leitura "fechado" e outra "minerando" no mesmo minuto contam como "minerando". Nenhum intervalo com `fim <= ini`.

**`atualizarParadas(agora)`** (só no PC):
1. `janelaIni` = o `t` da primeira leitura de `kxaHist.amostras`. `novas` = `paradasDasAmostras(kxaHist.amostras, energiaCache, agora)`.
2. **Continuação:** uma guardada que começou antes de `janelaIni` e não acabou, ou acabou em `>= janelaIni`, é a mesma parada que a primeira de `novas`, se esta começa em `janelaIni`. Fica o `ini`, o `aprox` e o motivo da guardada (o forte das duas, se uma for forte), com o `fim` e o `ligou` de `novas`. Uma guardada sem fim e sem continuação acaba em `janelaIni`.
3. **Juntar:**
   - `lista` = as guardadas com `ini < janelaIni` mais `novas`;
   - as que vieram da guarda mantêm `ritmo` e `avisoLigou`, casando pelo `ini`;
   - ficam de fora as que têm menos de `PARADA_MIN` (ou, sem fim, `agora − ini < PARADA_MIN`), menos `energia`;
   - a lista fica em ordem de `ini`, cortada por 365 dias e 1000 paradas.
4. **O que avisar:**
   - `acabaram` = as que têm `fim` agora, mas estavam sem fim (ou não existiam) na guarda, com `agora − fim <= 3*60e3`;
   - `ligouSemMinerar` = a sem fim com `ligou`, `agora − ligou >= 15*60e3` e sem `avisoLigou`.
5. **Grava** `lsSet("min-paradas", paradas)` só se a lista mudou (comparando o JSON).

**Na leitura:**
- `lerKryptexApp` faz `energiaCache = await lerEnergia()` antes de `processarLeituraKxa` (quando `PODE_KXA()`).
- `processarLeituraKxa` grava a leitura (as duas, ok e falha) e chama `atualizarParadas(agora)` logo em seguida.
- `hojeKxa` pega a primeira leitura do dia **com saldo** (`a[1]!=null`) como base.

- [ ] **Step 1: Escrever o teste** `testes/paradas.py`.
  - Cabeçalho e uso como `testes/kryptex_app.py`.
  - **`FIX`:**
    - define `window.__energia` e `window.desktop.energia = async () => JSON.parse(JSON.stringify(window.__energia))`;
    - as leituras `MIN`, `PARADO`, `PAUSADO` (`LEIT({pausado:true}, {minerando:false, watts:20})`), `QUENTE` (`temp: 86`) e `FECHADO = {ok:false, erro:"fechado", msg:""}`, com a mesma fábrica `LEIT` de `kryptex_app.py`;
    - `simularParadas(lista, marcas = [], op = {})`, igual a `simularLeituras`, mas:
      - zera `paradas = {v:1, retro:true, lista:[]}` (menos com `op.manter`);
      - aceita `op.t0`;
      - põe `window.__energia = {desde: t0 − 864e5, marcas: marcas.map(([m, tipo]) => ({t: t0 + m*60e3, tipo}))}`;
      - devolve `{paradas: [{ini, fim, ligou, motivo}] em minutos desde t0, alertas: [tipos], textos: [textos], celular: window.__celular, t0}`.
  - **`deteccao(p)`**, com `abrir(p, dados=DADOS, pc=True)` e as asserções sobre `r["paradas"]` (minutos):
    - **Queda de energia:** `[[0,MIN],[1,MIN],[2,MIN],[380,FECHADO],[381,FECHADO],[384,PARADO],[386,MIN]]` com `[[374,"ligou"]]` → `[{ini:2, fim:386, ligou:374, motivo:"energia"}]`.
    - **Queda curta (o PC religou em 4 min):** `[[0,MIN],[1,MIN],[6,FECHADO],[7,MIN]]` com `[[4,"ligou"]]` → `[{ini:1, fim:7, ligou:4, motivo:"energia"}]`.
    - **Desligado:** `[[0,MIN],[1,MIN],[2,MIN],[64,MIN]]` com `[[3,"desligou"],[60,"ligou"]]` → `[{ini:2, fim:64, ligou:60, motivo:"desligado"}]`.
    - **Suspensão:** `[[0,MIN],[4,MIN],[91,MIN]]` com `[[5,"suspendeu"],[90,"acordou"]]` → `[{ini:4, fim:91, ligou:None, motivo:"suspensao"}]`.
    - **Painel fechado com o PC ligado:** `[[0,MIN],[1,MIN],[120,MIN]]` sem marcas → `[]`.
    - **App fechado:** `[MIN] + [FECHADO]*12 + [MIN]` → `[{ini:0, fim:13, motivo:"fechado"}]`.
    - **Placa parada:** `[MIN] + [PARADO]*12 + [MIN]` → `[{ini:0, fim:13, motivo:"parada"}]`.
    - **Curta:** `[MIN] + [PARADO]*5 + [MIN]` → `[]`.
    - **Pausa:** `[MIN] + [PAUSADO]*15 + [MIN]` → motivo `"pausa"`.
    - **Proteção:** `[[0,QUENTE],[1,QUENTE]] + [[m,PAUSADO] for m in 2..17] + [[18,MIN]]` → `[{ini:1, fim:18, motivo:"protecao"}]`.
    - **A queda vale mais que a pausa:** `[[0,MIN],[1,PAUSADO],[2,PAUSADO],[3,PAUSADO],[200,MIN]]` com `[[150,"ligou"]]` → `[{ini:0, fim:200, ligou:150, motivo:"energia"}]`.
    - **Sem fim:** `[MIN] + [PARADO]*12` → `[{ini:0, fim:None, motivo:"parada"}]`; com `[PARADO]*5` → `[]`.
    - **Review Focus 2:** `[[0,MIN],[1,MIN],[120,MIN],[121,MIN],[300,MIN],[450,MIN]]` com `[[110,"ligou"],[440,"ligou"]]` → `[{ini:1, fim:120, ligou:110, motivo:"energia"}, {ini:300, fim:450, ligou:440, motivo:"energia"}]`.
    - **Review Focus 5:** `[[0,MIN],[0,MIN],[1,PARADO],[1,PARADO]] + [[m,PARADO] for m in 2..12] + [[13,MIN]]` → `[{ini:0, fim:13, motivo:"parada"}]`, sem erros.
    - **Review Focus 3:** monta no JS `kxaHist.amostras` com leituras "parado" (`[t, 0.0001, 18, 0, 0, 63, 78, null, "p"]`) de minuto em minuto de −2100 a 0 e guarda `paradas.lista = [{ini: t0 − 40h, fim: null, ligou: null, motivo: "parada", aprox: false, ritmo: null}]`. Uma leitura `[1, MIN]` com `op.manter` → uma parada só, `{ini: −2400, fim: 1, motivo: "parada"}`.
    - **O estado nas leituras:** depois de `[MIN, PAUSADO, PARADO, FECHADO]`, `kxaHist.amostras.map(a => a[8])` = `["m","u","p","f"]`.
    - **Grava pouco:** espiando o `Storage.prototype.setItem` de `min-paradas`, `[MIN] + [PARADO]*15 + [MIN]` grava 2 vezes (quando chega a 10 min e quando acaba).
    - **As duas listas:** `re.findall` das duas `SINCRONIZADAS` (`mineracao.html` e `desktop/sincronia.js`) dá a mesma lista, com `"min-paradas"`.
    - **Celular:** `abrir(p, dados={**DADOS, "min-paradas": {"v":1, "retro":True, "lista":[uma parada]}}, celular=True)` → `paradas.lista.length === 1`. Depois de trocar o localStorage e chamar `recarregarDados(["min-paradas"])`, a lista nova.
    - **Sem erros** nas páginas.
  - O fim do arquivo segue `kryptex_app.py`: `with sync_playwright() as p: deteccao(p)` e `fim()`.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/paradas.py` → as checagens de `deteccao` falham (`paradas is not defined`).
- [ ] **Step 3: Implementar** como acima.
- [ ] **Step 4: Rodar:** `python3 testes/paradas.py` → `"falhas": []`; `python3 testes/kryptex_app.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git add mineracao.html desktop/sincronia.js testes/paradas.py && git commit -m "Paradas: as leituras guardam o estado e o painel calcula as paradas"`

### Task 3: As contas (horas do dia, ritmo e quanto deixou de ganhar)

**Files:**
- Modify: `mineracao.html` (`calcularDiasKx` e as funções novas perto de `estDia`; `horasDoDiaKx` sai, porque fica sem uso)
- Test: `testes/paradas.py` (a função `contas(p)`)

**Interfaces:**
- Consumes: `paradas`, `atualizarParadas` (Tarefa 2).
- Produces:
  - `ritmoConta(dia: "aaaa-mm-dd") -> number|null` (R$/h): os `kx.dias` dos 7 dias antes de `dia`, com `!aproximado && !parcial && horas>0 && valor>0`; US$ × `cfg.dolar`. É Σvalor ÷ Σhoras.
  - `ritmoEstimado() -> number` = `totaisSetup({horas:24}).recUsd/365/24*cfg.dolar*fatorSim().f`.
  - `ritmoParada(p) -> number` = `p.ritmo ?? ritmoConta(isoLocal(new Date(p.ini))) ?? ritmoEstimado()`.
  - `horasParadasDia(dia, agora) -> number`: as horas das paradas dentro do dia; sem fim = até `agora`.
  - `horasMinerandoDia(dia, agora) -> number` (1 casa): do começo do dia até o fim dele (ou até `agora`, hoje), menos `horasParadasDia`. Num dia `parcial` de `kx.dias`, começa em `kxHist.saldos[0][0]`.
  - `perdaParada(p, dia?, agora?) -> number` (R$): as horas (só dentro do `dia`, se vier) × `ritmoParada(p)`.
  - `aplicarParadasNosDias(agora) -> boolean`: só no PC.
    - Muda as `horas` dos `kx.dias` (por `horasMinerandoDia`) e as dos dias do Diário com `fonte==="kryptex"` cujo dia está em `kx.dias`. Os do Diário mudam quando a diferença é de 0,05 h ou mais.
    - Grava `min-diario` uma vez e `min-kryptex` (`kx.gravado = 0`, `salvarKx()`).
    - Volta `true` se mudou.
  - `calcularDiasKx` usa `horas: horasMinerandoDia(iso, agora)`.
  - `atualizarParadas` preenche `ritmo` das que acabaram sem ele (`ritmoConta(...) ?? ritmoEstimado()`) e, com a lista mudada, chama `aplicarParadasNosDias(agora)`.

- [ ] **Step 1: Escrever** `contas(p)` com `abrir(p, dados=DADOS_CONTAS, pc=True)`. `DADOS_CONTAS` = `DADOS` mais:
  - **`min-kryptex`:** `dias` de 2026-10-14 a 2026-10-24, cada um `{btc: 0.0000618, valor: 24.72, moeda: "BRL", horas: 24, aproximado: false, parcial: ""}`, com duas exceções:
    - 2026-10-23 `aproximado: true, valor: 100`;
    - 2026-10-22 `moeda: "USD", valor: 24.72/5.04`.
  - **`min-paradas`:** `retro: true` e as paradas (horário de Brasília):
    - P1: 24/10 02:00–08:00, `energia`, `ligou` 07:50, `ritmo` 1.03;
    - P2: 22/10 22:00 – 23/10 01:00, `parada`, `ritmo` 1.03;
    - P4: 25/10 05:00–07:10, `energia`, `ligou` 07:00, `ritmo` 1.03;
    - P6: 25/10 13:40, sem fim, `parada`, `ritmo` null.
  - **`min-diario`:** 2026-10-24 `{fonte: "kryptex", horas: 24, valor: 18.54, moeda: "BRL"}` e 2026-10-23 `{horas: 24, valor: 24.72, moeda: "BRL"}` (digitado).

  **Asserções:**
  - `ritmoConta("2026-10-25")` ≈ 1.03 (1e-9): o 23 aproximado fica fora e o 22 em US$ vira R$. `ritmoConta("2026-10-14") === null`.
  - `ritmoEstimado()` ≈ `totaisSetup({horas:24}).recUsd/365/24*cfg.dolar*fatorSim().f` e `> 0`.
  - **Horas minerando:**
    - `horasMinerandoDia("2026-10-24", AGORA)` = 18;
    - `"2026-10-22"` = 22;
    - `"2026-10-23"` = 23;
    - `"2026-10-25"` = 11.5 (14 h − 2 h 10 min − 20 min, em 1 casa).
  - **Deixou de ganhar:**
    - `perdaParada(P1)` ≈ 6.18;
    - `perdaParada(P2, "2026-10-22")` ≈ 2.06;
    - `perdaParada(P6, undefined, AGORA)` ≈ (20/60)*1.03.
  - **O Diário depois de `aplicarParadasNosDias(AGORA)`** (é `true`):
    - o 24 (Kryptex) fica com `horas` 18;
    - o 23 (digitado) continua com 24;
    - `JSON.parse(localStorage["min-kryptex"]).dias["2026-10-24"].horas === 18`;
    - `linhaDia(o 24).eUsd` ≈ `estDia("2026-10-24", 18).usd` e é menor que `estDia("2026-10-24", 24).usd`.
  - **Ritmo de uma parada que acabou:** com `simularParadas([MIN] + [PARADO]*12 + [MIN])`, `paradas.lista[0].ritmo` ≈ `ritmoConta(isoLocal(new Date(paradas.lista[0].ini))) ?? ritmoEstimado()`.
  - **Sem erros.**
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/paradas.py` → as de `contas` falham (`ritmoConta is not defined`).
- [ ] **Step 3: Implementar** as funções acima.
- [ ] **Step 4: Rodar:** `python3 testes/paradas.py` e `python3 testes/kryptex_app.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Paradas: as horas do dia descontam as paradas e o painel calcula quanto deixou de ganhar"`

### Task 4: As paradas dos dias que já passaram

**Files:**
- Modify: `mineracao.html` (perto de `atualizarParadas`)
- Test: `testes/paradas.py` (a função `retro(p)`)

**Interfaces:**
- Consumes:
  - as leituras de 36 h já viram paradas pela Tarefa 2: buracos antes de `energia.desde` dão `semleitura`, leituras antigas sem minerar dão `semminerar`;
  - `ritmoConta` (Tarefa 3).
- Produces:
  - `paradasDosSaldos(saldos: Array<[t, btc, preco]>, ate: number, ritmoDe: (t) => number|null) -> Parada[]` (pura): buracos de mais de 45 min entre saldos seguidos com `t2 <= ate`. Cada um vira `{ini: t1, fim: t2, ligou: null, motivo: "semleitura", aprox: true}` quando `(b2 − b1)*preco < 0.5*ritmoDe(t1)*(t2−t1)/3600e3`. Sem ritmo, só quando `b2 − b1 <= 0`.
  - Na primeira chamada de `atualizarParadas` com `!paradas.retro`: junta `paradasDosSaldos(kxHist.saldos, janelaIni, t => ritmoConta(isoLocal(new Date(t))))` (com `ritmo` preenchido), marca `retro = true` e chama `aplicarParadasNosDias`.
  - Essas paradas não geram aviso, porque acabaram há mais de 3 min.

- [ ] **Step 1: Escrever** `retro(p)`, com os horários em minutos desde `t0 = AGORA`.
  - **`min-kxa-hist`:** `{v:2, amostras}` com leituras antigas, de 8 campos e sem estado, de minuto em minuto de −1200 a −1:
    - minerando (`a[3] = 1`), menos −299 a −271 (`a[3] = 0`);
    - sem leituras entre −900 e −720 (exclusivo).
  - **`min-kx-hist`:** `saldos` de 15 em 15 min, de −5760 a −1200, com o preço de 400000 R$/BTC.
    - O saldo cresce 1.03/400000 BTC por hora.
    - Sem saldos entre −3600 e −3360 (exclusivo), com o saldo de −3360 igual ao de −3600.
    - Sem saldos entre −2400 e −2160 (exclusivo), com o crescimento normal.
  - **`min-kryptex`:** os `dias` de 2026-10-14 a 2026-10-24, como em `contas`.
  - **`min-paradas`:** não existe.
  - **Energia:** `window.__energia = {desde: t0 − 60e3, marcas: []}`.
  - **Abrir:** `pc=True`; uma leitura `[0, MIN]` com `simularParadas(..., {manter: true, t0})`.

  **Asserções:**
  - As paradas em minutos são exatamente:
    - `{ini:−3600, fim:−3360, motivo:"semleitura"}`, com `aprox` verdadeiro;
    - `{ini:−900, fim:−720, motivo:"semleitura"}`;
    - `{ini:−300, fim:−270, motivo:"semminerar"}` (a última leitura minerando antes é a de −300, e a primeira depois, a de −270).
  - O buraco de −2400 a −2160 **não** vira parada.
  - `paradas.retro === true`, e uma segunda `atualizarParadas(t0)` não muda o tamanho da lista.
  - Sem `voltou` nem `parou` em `kx.alertas`; `window.__celular` vazio.
  - `kx.dias["2026-10-23"].horas` < 24: o buraco de −3600 cai no dia 23.
  - Sem erros.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/paradas.py` → as de `retro` falham (a parada dos saldos não aparece).
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar:** `python3 testes/paradas.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Paradas: as quedas dos dias que já passaram, pelas leituras e pelos saldos guardados"`

### Task 5: O Diário e a lista de paradas

**Files:**
- Modify: `mineracao.html`
  - o HTML da seção `#v-diario`: `#d-paradas` embaixo de `#d-margem`; `#paradas-p` entre `#d-tab` e `#rel-p`;
  - o CSS: `.d-parou`, `#d-paradas`, `.pd-lista`, `.pd-it` e as regras do celular;
  - `renderDiario`, `renderSugestoesKx`, `renderGraf` (a dica) e `renderParadas`.
- Test: `testes/paradas.py` (a função `diario_ui(p)`)

**Interfaces:**
- Consumes: `paradas`, `perdaParada`, `ritmoParada`, `horasParadasDia` (Tarefas 2 e 3), `duracao`, `horaMin`, `brl`, `plural`, `copiarTexto`.
- Produces:
  - **Textos:**
    - `ROTULO_PARADA` (os rótulos exatos);
    - `fraseParada(p) -> string` (as frases exatas);
    - `hhParada(t, aprox) -> string` (`"~"` + `horaMin(t)` quando aproximada);
    - `intervaloTxt(ini, fim, aprox) -> string`: "das {hh:mm} às {hh:mm}", ou, em dias diferentes, "das {hh:mm} de {dd/mm/aaaa} às {hh:mm} de {dd/mm/aaaa}".
  - **Por dia e por período:**
    - `paradasDoDia(dia, agora) -> Array<{p, ini, fim}>`: cortadas no dia. O começo cortado é "00:00" e o fim cortado é "24:00", sem "~".
    - `linhaParadasDia(dia, agora) -> string`: `""` ou "Fora do ar {duração}: {hh}–{hh} ({Rótulo}), … · deixou de ganhar uns {R$}".
    - `resumoParadasPeriodo(per, agora) -> {total, n, perda}`.
  - **A lista:**
    - `textoParadas(lista, agora) -> string`: uma linha por parada, "{dd/mm/aaaa do início}, {intervaloTxt(ini, fim, aprox)} ({duração}): {fraseParada(p)}". Sem fim, "{dd/mm/aaaa}, desde as {hh:mm} ({duração} até agora): {fraseParada(p)}". As linhas se juntam com "\n".
    - `renderParadas()`.
  - **O filtro "Só falta de energia"** mostra `energia` e `semleitura`. Esta foi pensada como uma regra: a queda de energia de antes desta versão aparece como `semleitura`.

- [ ] **Step 1: Escrever** `diario_ui(p)`. `DADOS_UI` = `DADOS_CONTAS` mais:
  - P3: 21/10 03:00–05:00, `semleitura`, `aprox` verdadeiro, `ritmo` 1.03;
  - P5: 20/10 10:00–10:30, `pausa`, `ritmo` 1.03;
  - P6 com `fim` 13:50 e `ritmo` 1.03;
  - no Diário, com `fonte: "kryptex"`: o 24 com `horas` 18 e valor 18.54, o 22 com 22 e 22.66, e o 21 com 22 e 22.66.

  As asserções (no PC, `hash="diario"`, `pc=True`):
  - **A linha do dia 24:** contém "Fora do ar 6 h: 02:00–08:00 (Falta de energia?) · deixou de ganhar uns R$ 6,18".
  - **A do dia 22:** contém "Fora do ar 2 h: 22:00–24:00 (Placa parada) · deixou de ganhar uns R$ 2,06".
  - **A do dia 21:** contém "Fora do ar 2 h: ~03:00–~05:00 (Sem leitura (PC desligado ou sem energia)) · deixou de ganhar uns R$ 2,06".
  - **`#d-paradas`** (período de 7 dias, de 19/10 a 25/10): "No período, a placa ficou 13 h 50 min parada (6 paradas) e deixou de ganhar uns R$ 14,25". São P1 6 h, P2 3 h, P3 2 h, P4 2 h 10 min, P5 30 min e P6 10 min: 13,8333 h × 1.03 = 14,248.
  - **A lista `#paradas-p`:** 6 itens, a mais nova primeiro. Com "Só falta de energia" marcado, ficam P4, P1 e P3.
  - **"Copiar a lista"** (com `window.desktop.copiar` trocado por um que guarda o texto) dá exatamente, com o período de 7 dias e o filtro desmarcado:
    ```
    25/10/2026, das 13:40 às 13:50 (10 min): a placa ficou parada
    25/10/2026, das 05:00 às 07:10 (2 h 10 min): o PC apagou de repente (falta de energia?) e ligou às 07:00
    24/10/2026, das 02:00 às 08:00 (6 h): o PC apagou de repente (falta de energia?) e ligou às 07:50
    22/10/2026, das 22:00 de 22/10/2026 às 01:00 de 23/10/2026 (3 h): a placa ficou parada
    21/10/2026, das ~03:00 às ~05:00 (2 h): o PC ficou sem leitura (desligado ou sem energia)
    20/10/2026, das 10:00 às 10:30 (30 min): a mineração ficou pausada por você
    ```
  - **Ganhos lidos da Kryptex:** tirando o 24 do Diário (`diario = diario.filter(e => e.data !== "2026-10-24"); renderSugestoesKx()`), com `kx.dias["2026-10-24"].horas` 18, o cartão mostra "· 18 h minerando · parou 6 h (Falta de energia?)".
  - **A dica do gráfico** no dia 24 (foco no `.bar-hit`) tem "parou 6 h".
  - **Review Focus 4:**
    - sem PC e sem celular (`abrir(p, dados=DADOS, hash="diario")`): `#paradas-p` escondido e sem erros;
    - no celular (`celular=True`, 390×844) com `min-paradas` vazio: "Nenhuma parada neste período";
    - com `DADOS_UI`, o celular mostra a mesma linha do dia 24, `document.documentElement.scrollWidth <= 390` e o botão "Copiar a lista" com 44 px ou mais.
  - **Claro e escuro:** sem "NaN", "Infinity" nem "undefined" no texto de `#v-diario`.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/paradas.py` → as de `diario_ui` falham.
- [ ] **Step 3: Implementar.**
  - `linhaParadasDia` entra num `<small class="d-parou">` na célula do dia, que vira a linha do cartão no celular.
  - `#d-paradas` usa `resumoParadasPeriodo(dPer)`.
  - **`#paradas-p`:**
    - o título "Paradas", o filtro (`<label class="check"><input type="checkbox" id="pd-energia"> Só falta de energia</label>`, só nesta visita) e "Copiar a lista";
    - fica escondido quando `!paradas.lista.length && !(PODE_KXA() || REMOTO)`.
  - No celular, os itens empilham e o botão tem 44 px.
- [ ] **Step 4: Rodar:** `python3 testes/paradas.py` e `python3 testes/visual.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Paradas: o Diário mostra as paradas de cada dia e a lista para copiar"`

### Task 6: Resumo, avisos e o celular

**Files:**
- Modify: `mineracao.html`
  - `htmlAgoraVivo` (a linha `.ag-parou`);
  - `processarLeituraKxa` (o "voltou" completo, o "PC voltou mas a placa ainda não está minerando" e o "voltou" de hoje só sem parada acabando);
  - `sincronizarSegundoPlano` (`kxa`).
- Test: `testes/paradas.py` (a função `resumo_avisos(p)`)

**Interfaces:**
- Consumes: `atualizarParadas(agora)` → `{acabaram, ligouSemMinerar}` (Tarefa 2), `fraseParada`, `intervaloTxt`, `perdaParada` (Tarefas 3 e 5), `avisoKx`.
- Produces:
  - **`linhaParadasHoje(agora) -> string`:**
    - com uma parada sem fim, "parada desde {hh:mm}";
    - com as paradas de hoje que acabaram, "parou {duração} hoje ({hh}–{hh}, {Rótulo}; …)";
    - as duas partes se juntam com " · ".
  - **O aviso de fim:** `avisoKx("voltou", "{nomePlaca(principalKxa(l)) || 'A placa'} voltou a minerar", "Ficou fora do ar {intervaloTxt} ({duração}): {fraseParada}. Deixou de ganhar uns {R$}.")` para cada uma de `acabaram` que não é `pausa`.
  - **O aviso do PC que voltou:** `avisoKx("parou", "O PC voltou, mas a placa ainda não está minerando", "Ligou às {hh:mm}; a placa está sem minerar desde {hh:mm}.")` para `ligouSemMinerar`. Depois, a parada fica com `avisoLigou = true` e é gravada.
  - O "voltou" de hoje (moeda e hashrate) sai só quando nenhuma parada acabou nesta leitura.
  - `window.desktop.segundoPlano({bandeja, iniciar, kxa: kxv})`.

- [ ] **Step 1: Escrever** `resumo_avisos(p)`, com `abrir(p, dados=DADOS_CONTAS, pc=True)` e os avisos do celular ligados (`celCfg = {...(celCfg||{}), ligado:true, topico:'t', maquinas:true}`).
  - **Queda de energia** (o mesmo cenário da Tarefa 2):
    - `kx.alertas` tem um único `voltou`, com o texto "RX 9070 XT voltou a minerar. Ficou fora do ar das 14:02 às 20:26 (6 h 24 min): o PC apagou de repente (falta de energia?) e ligou às 20:14. Deixou de ganhar uns R$ 6,59.";
    - `window.__celular` tem uma mensagem `{tipo:"voltou", titulo:"RX 9070 XT voltou a minerar", corpo:"Ficou fora do ar das 14:02 às 20:26 (6 h 24 min): o PC apagou de repente (falta de energia?) e ligou às 20:14. Deixou de ganhar uns R$ 6,59."}`.
  - **O PC voltou e a placa não:** `[[0,MIN],[1,MIN],[2,MIN]] + [[m,FECHADO] for m in 380..395]` com `[[374,"ligou"]]`.
    - `__celular` tem uma só `{tipo:"maquina", titulo:"O PC voltou, mas a placa ainda não está minerando", corpo:"Ligou às 20:14; a placa está sem minerar desde 14:02."}`.
    - Ela sai uma vez, mesmo com as leituras seguintes. Com `[396, MIN]` depois (`op.manter`), vem o `voltou`.
  - **A placa parada por 13 min:** `[MIN] + [PARADO]*12 + [MIN]` → alertas `["parou", "voltou"]`, e o texto do `voltou` termina em "a placa ficou parada. Deixou de ganhar uns R$ 0,22.".
  - **Parada curta:** `[MIN, PARADO, PARADO, PARADO, MIN]` → `["parou", "voltou"]`, com o "voltou" de hoje ("Pearl (PRL)" no texto).
  - **Pausa:** `[MIN] + [PAUSADO]*15 + [MIN]` → nenhum alerta e `__celular` vazio.
  - **Review Focus 1:** depois da queda acima, recarregar (`kxa = novoKxa(); energiaCache = null`, com `kxaHist` e `paradas` mantidos) e uma leitura `[387, MIN]` com `op.manter` e o mesmo `t0` → nenhum `voltou` novo e `__celular` vazio nessa rodada.
  - **`segundoPlano`:** troca `window.desktop.segundoPlano` por um que guarda o argumento e põe `apCfg ||= {ligado:false}`, `celCfg ||= {ligado:false}` e `acCfg ||= {ligado:false}`. Depois de uma leitura `MIN` e de `sincronizarSegundoPlano()`, o argumento tem `kxa === true`.
  - **Resumo no PC:** com `DADOS_UI` (Tarefa 5) e uma leitura `MIN` em `AGORA`, `#ag-corpo` contém "parou 2 h 20 min hoje (05:00–07:10, Falta de energia?; 13:40–13:50, Placa parada)".
  - **Resumo sem fim:** com a P6 sem fim, contém "parada desde 13:40".
  - **Resumo no celular** (`celular=True`, `min-kx-app` com um retrato e `min-paradas` de `DADOS_UI`): a mesma linha.
  - **Sem erros.**
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/paradas.py` → as de `resumo_avisos` falham.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar:** `python3 testes/paradas.py`, `python3 testes/kryptex_app.py`, `python3 testes/celular.py` e `python3 testes/mensagens_app.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Paradas: o Resumo mostra as paradas de hoje e o celular recebe o aviso quando a mineração volta"`

### Task 7: Versão 1.10.0, documentação, fotos e todos os testes

**Files:**
- Modify: `mineracao.html` (`NOVIDADES`), `desktop/package.json`, `desktop/package-lock.json` (o topo), `CLAUDE.md`, `testes/paradas.py` (`--fotos`)
- Create: `notas/v1.10.0.md`

- [ ] **Step 1: Novidades e notas.**
  - **`NOVIDADES`**, no começo:
    ```js
    {v:"1.10.0", itens:[
      "Paradas e quedas de energia: o painel anota quando a mineração para (falta de energia, PC desligado, app da Kryptex fechado, placa parada ou pausada), de que horas a que horas, e quanto deixou de ganhar.",
      "No Diário, cada dia mostra as paradas, as horas minerando descontam o tempo parado (o estimado e a margem real ficam justos) e a lista de paradas pode ser copiada para mandar à Celesc.",
      "Quando a mineração volta depois de uma parada, o celular recebe um aviso com o horário e quanto deixou de ganhar."]},
    ```
  - **`notas/v1.10.0.md`:** no formato de `notas/v1.9.0.md`, com 3 itens:
    - **Paradas e quedas de energia**;
    - **Diário mais justo**;
    - **Aviso quando volta**.

    Repita a linha "Esta versão não muda a parte do Android do app: com o app 1.8.0, o celular recebe o painel novo sozinho." e o "Como instalar" com 1.10.0.
- [ ] **Step 2: Versão e documentação.**
  - `"version": "1.10.0"` em `desktop/package.json` e no topo de `desktop/package-lock.json` (as duas linhas do topo).
  - **`CLAUDE.md`:**
    - no item do app da Kryptex: as paradas (`min-paradas`, `paradasDasAmostras`, `atualizarParadas`, os motivos, `desktop/energia.js` e `energia.json`, o "O PC voltou" só sem a leitura do app);
    - na lista do que o PC e o celular dividem: `min-paradas`, que só o PC grava;
    - nos testes: `python3 testes/paradas.py` e `node desktop/scripts/teste-energia.js`.
- [ ] **Step 3: Fotos.** `fotos(p, pasta)` em `testes/paradas.py` (com `--fotos <pasta>`) grava:
  - o Diário com `DADOS_UI` no PC (1366×900), claro e escuro, página inteira;
  - o Diário no celular (390×844), claro e escuro;
  - o Resumo no PC com a linha de hoje.

  Rodar `python3 testes/paradas.py --fotos <scratchpad>/fotos-paradas` e conferir a olho.
- [ ] **Step 4: Todos os testes**, cada um com `"falhas": []` ou `ok`:
  - `python3 testes/paradas.py`
  - `python3 testes/kryptex_app.py`
  - `python3 testes/visual.py`
  - `python3 testes/celular.py`
  - `python3 testes/mensagens_app.py`
  - `python3 testes/atualizador.py`
  - `python3 testes/pacote_celular.py`
  - `python3 testes/simulador.py`
  - `python3 testes/rolagem_fb.py`
  - `python3 testes/conferir_nativo.py`
  - `python3 web/gerar-simulador.py && python3 testes/simulador_web.py`
  - `node desktop/scripts/teste-energia.js`
  - `node desktop/scripts/teste-sincronia.js`
  - `node desktop/scripts/teste-kryptex-app.js`
  - `node desktop/scripts/teste-sensores-amd.js`

  O teste do aplicativo com o Electron (`desktop/scripts/teste.js`) precisa das páginas de exemplo de `PAINEL_FIXOS`, que não estão neste ambiente. Ele não roda aqui; o de energia cobre a parte nova do programa.
- [ ] **Step 5: Commit:** `git add -A notas/v1.10.0.md && git commit -am "Paradas: versão 1.10.0, novidades, notas e documentação"`
- [ ] **Step 6: Mandar as fotos ao Alex e pedir o OK para publicar.** Só com o OK:
  - juntar no `main` e fazer push (publica a release);
  - acompanhar por `repos/AlexsAzevedo/painel-mineracao/commits/<sha>/check-runs`;
  - publicar o `mineracao.html` de novo no painel online (`url` do artifact Nu8cNXUvFJKtnFFPBWFY9A).
