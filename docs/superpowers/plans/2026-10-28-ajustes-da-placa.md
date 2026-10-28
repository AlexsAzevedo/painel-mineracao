# Ajustes da placa no painel, no lugar do Afterburner (1.11.0) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o painel do PC lê e grava os ajustes da placa de vídeo AMD (limite de potência, tensão, clock máximo, memória, temporização e ventoinha), guarda o ajuste escolhido, aplica de novo quando a placa sai dele e volta para o último ajuste bom se um ajuste novo travar a placa. O celular só mostra.

**Architecture:**
- **O leitor** (`desktop/placa-amd.ps1`): Windows PowerShell 5.1 com C# dentro, como o `sensores-amd.ps1`. Fala com o ADL do driver da AMD (`atiadlxx.dll`) pelo Overdrive8 e conversa com o programa por linhas de JSON. É o único lugar que grava na placa.
- **O programa do PC:**
  - `placa-amd.js` cuida do processo do leitor (fila, prazos, quedas);
  - `placa-regras.js` são as decisões, em funções puras;
  - `placa.js` guarda o estado em `placa.json`, roda a vigia de cada minuto e as ações (cuidar, aplicar, de fábrica).
  - O `main.js` só liga tudo e expõe `window.desktop.placa` pelo `preload.js`.
- **A página:** a seção "Placa de vídeo deste PC" em Premissas (só no programa do PC), os avisos pelo caminho do `avisoKx` e a chave sincronizada `min-placa`, que o celular mostra sem campos.

**Tech Stack:**
- C# 5 dentro do PowerShell 5.1 (`Add-Type`), testado no Linux com o `mcs` do Mono e um ADL de mentira em C (`gcc`).
- Node e Electron 44 (`desktop/`).
- HTML/JS de uma página só (`mineracao.html`).
- Playwright em Python (`testes/`).

**Spec:** `docs/superpowers/specs/2026-10-28-ajustes-da-placa-design.md`

## Global Constraints

- **Biblioteca:** só o ADL (`atiadlxx.dll`). Nada do ADLX entra no repositório (a licença não deixa; veja a seção "Licença" da spec). O `placa-amd.ps1` começa com o aviso de onde vêm as declarações, como o `sensores-amd.ps1`: "Os nomes das funções, o formato das estruturas e os números dos ajustes vêm do ADL SDK da AMD (github.com/GPUOpen-LibrariesAndSDKs/display-library, cabeçalhos com licença MIT, Copyright (c) Advanced Micro Devices, Inc.)."
- **C# 5** (o do Windows PowerShell 5.1):
  - não pode: interpolação de texto, `?.`, `nameof`, membros com `=>`, `out var`;
  - não pode: `HashSet`, LINQ e `Func` (ficam no System.Core, que o `Add-Type` pode não carregar). Use `List`, `Dictionary` e delegates próprios.
- **Overdrive8** (posição na lista de ajustes):
  - clock máximo `0`, memória máxima `8`, potência `9`, temporização `14`, zero rpm `15`;
  - curva da ventoinha de `19` a `28`: temperatura do ponto p em `19+2p` e velocidade em `20+2p`, p de 0 a 4;
  - modo de energia `36`, tensão `37`.
- **Capacidades** (bits do `overdrive8Capabilities`):
  - clock `1<<0` (sem `1<<1`, a curva por pontos);
  - memória `1<<2`, potência `1<<3`, temporização `1<<8`, zero rpm `1<<9`, curva `1<<13`, modo `1<<16`, tensão `1<<17`.
- **Estruturas:**
  - Na leitura, o `count` de entrada é `OD8_COUNT = 77`, e as estruturas têm folga de 256 entradas.
  - Na gravação, o `count` é o número de ajustes que o driver respondeu na leitura (76 no driver de 10/2026).
  - `ADLOD8SingleInitSetting` = `{featureID, minValue, maxValue, defaultValue}` (16 bytes); `ADLOD8SingleSetSetting` = `{value, requested, reset}` (12 bytes).
  - `AdapterInfo` = 1572 bytes: índice no byte 4, barramento no 264, fabricante no 276 (1002 ou 0x1002), nome no 280 e `PNPString` no 1312.
- **Gravação:**
  - A única função de escrita é `ADL2_Overdrive8_Setting_Set`, e ela só leva os ajustes `0, 8, 9, 14, 15, 19–28, 36, 37`.
  - O modo (`36`) só com o valor 3. `reset` é sempre 0.
  - **Toda gravação leva a curva (os 10 ajustes) e o zero rpm quando a placa tem, numa chamada só.** Se o modo não for 3, uma chamada antes só com `{36: 3}`.
- **Formato do ajuste** (página, `placa.js`, regras e leitor): `{potencia?, tensao?, clock?, memoria?: inteiro, temporizacao?: 0|1, ventoinha?: {modo: "auto"} | {modo: "fixa", pct} | {modo: "curva", curva: [[°C, %] × 5], zeroRpm: 0|1}}`.
  - "auto" é a curva de fábrica com o zero rpm de fábrica.
  - "fixa" põe as 5 velocidades em `pct`, mantém as temperaturas da leitura e desliga o zero rpm.
  - "curva" é a de outro programa, mantida como está.
- **Tempos:**
  - Teste: 15 minutos contados, cada vigia com uso ≥ 80% conta um.
  - Vigia: a primeira 10 s depois de abrir; depois a cada 60 s (`PAINEL_PLACA_VIGIA_MS` no teste).
  - Ventoinha: a referência é a mediana das 3 primeiras rotações depois de aplicar; queda de mais de 15% faz gravar de novo.
  - Avisos: "outro", "ventoinha" e "parou", no máximo 1 por hora por tipo e placa; "travou" sai sempre. Depois de um erro de gravação da vigia, espera 10 min.
  - Driver: 2 reinícios em 24 h com o mesmo ajuste fazem ele travar. A lista dos que travaram guarda até 10.
  - Leitor: prazo de 60 s no primeiro pedido, 20 s nos outros e 30 s no de fábrica. Quedas esperam 1, 5 e 30 min; sem AMD ou sem ADL, 1 h. Ocioso por 5 min, encerra.
- **Textos (exatos):**
  - **Seção e controles:**
    - seção: "Placa de vídeo deste PC";
    - caixa: "O painel cuida dos ajustes da placa";
    - ao assumir: "O painel guardou o ajuste que a placa já tem e não mudou nada. A partir de agora ele confere a cada minuto e aplica de novo se a placa sair desse ajuste."
  - **Situações:**
    - "Em teste: faltam {n} minutos com a placa minerando. Se ela travar, o painel volta para o ajuste anterior." (com n = 1: "falta 1 minuto");
    - "Ajuste bom desde {quando}." e "O ajuste de {quando} travou a placa ({motivo}). O painel voltou para o anterior.", com o `quando(t)` do painel;
    - sem cuidar: "O painel não está cuidando dos ajustes desta placa."
  - **Motivos:** "o PC desligou de repente durante o teste", "o driver de vídeo reiniciou durante o teste", "o driver de vídeo reiniciou 2 vezes em 24 horas".
  - **Avisos (título / corpo):**
    - travou: "O ajuste da placa travou" / "{nome}: {motivo}. O painel voltou para o ajuste anterior." (de fábrica: "… O painel voltou a placa para o de fábrica.");
    - outro: "Outro programa mudou o ajuste da placa" / "{nome}: o painel aplicou o seu ajuste de novo. Se for o MSI Afterburner, desligue nele o "Aplicar overclock ao iniciar o sistema"." (as aspas de dentro são parte do texto);
    - ventoinha: "A ventoinha da placa foi para o automático" / "{nome}: as rotações caíram de {ref} para {rpm} rpm. O painel gravou a ventoinha de novo.";
    - parou: "O painel não conseguiu aplicar o ajuste da placa" / "{nome}: {msg}. Ele tenta de novo em 10 minutos."
  - **Faixas e ajustes:**
    - Faixa: "de {min} a {max} · padrão {padrao}". Os números com unidade ("%", " mV", " MHz") e sinal ("+3", "−20" com U+2212, "0") na potência e nos campos em offset.
    - `textoAjuste`: "Potência −20% · Tensão −75 mV · Clock máximo +0 MHz · Memória 2518 MHz · Ventoinha fixa em 74%". Com a temporização, entra " · Temporização rápida". A ventoinha "auto" vira "Ventoinha automática", e a "curva" vira "Ventoinha personalizada".
  - **Outros textos:** o do Afterburner e o de "sem abrir junto com o Windows" são os da spec, seção 3.
- **`min-placa`** = `{v: 1, quando, cuidar, placas: [{nome, ajuste, situacao: "bom"|"teste"|"travou"|"sem", desde, faltam, travou: {quando, motivo}|null}]}`.
  - A spec chama de `testeAte`; como os minutos só contam com a placa minerando, vai `faltam`.
  - Só o PC grava, só quando muda (sem contar `quando`). Fica igual na `SINCRONIZADAS` de `mineracao.html` e de `desktop/sincronia.js`.
- **Versões:** o programa do PC vai para 1.11.0. O app do celular continua igual (`celular/android` não muda; `conferir-nativo.py` passa).
- **Tela:** a 390 px, sem rolagem para o lado e com botões de 44 px; claro e escuro; sem NaN, Infinity ou undefined.
- **OK do Alex para:**
  - publicar (push no `main`) e o painel online (artifact Nu8cNXUvFJKtnFFPBWFY9A);
  - qualquer gravação na placa de verdade (Tarefa 9).

## Review Focus

1. **O painel fechado pelo Sair e o PC desligado normalmente durante um teste.** Sem o painel aberto, não há marca `desligou`; o PC ligando sem ela não pode virar "travou". Vale a regra do `saiu`. Teste na Tarefa 4 e na 5.
2. **Memória com um valor que o driver arredonda,** como 2601 MHz gravado e lido 2600. O ajuste guardado passa a ser o lido, e a vigia não aplica de novo a cada minuto nem avisa "outro programa". Teste na Tarefa 4 e na 5.
3. **Duas placas iguais** (duas RX 9070 XT). As chaves são diferentes, pelo `PNPString`, e a página não mistura os campos de uma com a outra. Teste na Tarefa 1 e na 6.
4. **Página recarregada com avisos pendentes,** como na atualização do painel. Cada aviso sai uma vez só: os avisos só chegam pelo `estado()`, que os entrega e apaga. Teste na Tarefa 5 e na 8.
5. **O leitor parado ou caído no meio da vigia** (driver travado). A vigia não trava o painel, não aplica em laço e não repete aviso. Teste na Tarefa 3 e na 5.

## Mapa dos arquivos

- **Criar:**
  - `desktop/placa-amd.ps1`: o leitor e gravador;
  - `desktop/placa-amd.js`: o processo do leitor;
  - `desktop/placa-regras.js`: as decisões;
  - `desktop/placa.js`: o estado, a vigia e as ações;
  - testes: `desktop/scripts/adl-falso.c`, `teste-placa-amd-cs.py`, `placa-falsa.js`, `teste-placa-amd.js`, `teste-placa-regras.js`, `teste-placa.js` e `teste-placa-app.js` (em `desktop/scripts/`), e `testes/placa.py`;
  - `notas/v1.11.0.md`.
- **Mudar:**
  - `desktop/main.js`, `desktop/preload.js` e `desktop/sincronia.js` (a `SINCRONIZADAS`);
  - `desktop/package.json` e `desktop/package-lock.json`;
  - `desktop/scripts/teste-pacote.js`;
  - `mineracao.html` e `CLAUDE.md`.

---

### Task 1: O leitor lê a placa

**Files:**
- Create: `desktop/placa-amd.ps1`, `desktop/scripts/adl-falso.c`, `desktop/scripts/teste-placa-amd-cs.py`

**Interfaces:**
- **Produces:**
  - `placa-amd.ps1 [-Pai <pid>]`:
    - compila o C# com `Add-Type -TypeDefinition $codigo -Language CSharp -IgnoreWarnings`;
    - se não compilar, imprime `{"id":null,"ok":false,"erro":"falhou","msg":"o leitor nao compilou: …"}` e sai com 2;
    - senão chama `[PlacaAmd]::Rodar([Console]::In, [Console]::Out, $Pai)`.
  - **C#:** `public static class PlacaAmd`, com `public static void Rodar(TextReader entrada, TextWriter saida, int pai)` e `public static string Responder(string linha)`.
    - Uma resposta por linha recebida, sempre com o mesmo `id`; um pedido que não é JSON responde com `id: null`.
    - Uma linha de vigia confere o `pai` a cada 5 s e chama `Environment.Exit(0)` quando ele acaba.
    - Com a entrada fechada, fecha o ADL e sai.
  - **Pedido** `{"id":1,"op":"ler"}`, **resposta** `{"id":1,"ok":true,"afterburner":bool,"placas":[placa]}`:
    - `placa` = `{chave, nome, bus, indice, deFabrica, modo, potencia, tensao, clock, memoria, temporizacao, ventoinha, agora}`;
    - cada número: `{suporta, min, max, passo: 1, atual, padrao}`; a tensão e o clock têm também `offset` (`min < 0`); sem a capacidade, só `{suporta: false}`;
    - `temporizacao` = `{suporta, atual, padrao, opcoes: [min..max]}`;
    - `ventoinha` = `{suporta, velMin, velMax, tempMin, tempMax, curva, curvaPadrao, zeroRpm: {suporta, atual, padrao}}`;
    - `agora` = `{clockMHz, memoriaMHz, tensaoMv, watts, tempC, quenteC, memoriaC, ventoinhaRpm, ventoinhaPct, usoPct}`, só com os sensores lidos (PMLog 1, 2, 21, 73, 8, 27, 9, 14, 15, 19).
  - **Chave:** o `PNPString` aparado; vazio, `"bus:" + bus`.
  - **`deFabrica`:** todos os ajustes que a placa tem estão no padrão, inclusive a curva e o zero rpm.
  - **Placas:** só as AMD com Overdrive versão 8 e leitura boa.
  - **Erros:** `erro` em `pedido`, `sem-adl`, `sem-amd` ou `falhou`.
    - Sem placa AMD: `sem-amd`.
    - Com AMD, mas sem Overdrive8: `ok: true` com `placas: []`.
  - **Funções do ADL declaradas no C#** (e nenhuma outra de escrita):
    - `ADL2_Main_Control_Create` e `ADL2_Main_Control_Destroy`;
    - `ADL2_Adapter_NumberOfAdapters_Get` e `ADL2_Adapter_AdapterInfo_Get`;
    - `ADL2_Overdrive_Caps`;
    - `ADL2_Overdrive8_Init_Setting_Get`, `ADL2_Overdrive8_Current_Setting_Get`, `ADL2_Overdrive8_Init_SettingX2_Get` e `ADL2_Overdrive8_Current_SettingX2_Get`;
    - `ADL2_New_QueryPMLogData_Get`;
    - e, na Tarefa 2, `ADL2_Overdrive8_Setting_Set`.
- **O ADL de mentira** (`adl-falso.c`):
  - **Funções:** as mesmas exportadas, mais `ADL2_Adapter_RegValueInt_Set`, que aborta ao ser chamada.
  - **Cenário:** `FALSO_CENARIO`, com a tabela da 9070 XT dos testes de 28/10 (potência −20 de −30 a +10, tensão −75 de −200 a 0, clock 0 de −500 a +1000, memória 2518 de 2518 a 3000, temporização 0 de 0 a 1, zero rpm 0 com padrão 1, curva 74% em 30/50/61/72/80 °C, curva de fábrica 15/32/49/66/100, faixas da curva 25–100 °C e 15–100%, modo 3 com padrão 3, 76 ajustes).
  - **Registro:** `FALSO_LOG` recebe uma linha por chamada (o nome da função).
  - **Conferências:** o contexto (aborta com "ERRADA" se errado), o `count` 77 de entrada nas funções antigas e o `*n == 77` nas X2 (senão −9, como o driver de verdade).
- **O teste** (`teste-placa-amd-cs.py`):
  - tira o C# de entre `$codigo = @'` e `'@` do `.ps1`;
  - escreve um `Main` de teste numa pasta temporária, que chama `PlacaAmd.Rodar(Console.In, Console.Out, 0)`;
  - compila com `mcs -langversion:5`, e o fake com `gcc` (mais uma variante `-DSO_X2`, sem as funções antigas);
  - liga a DLL por um `.exe.config` com `<dllmap dll="atiadlxx.dll" target="…"/>`;
  - manda os pedidos pela entrada.
  - Imprime "tudo certo" ou "N falha(s)" e sai com 1 na falha.

- [ ] **Step 1: Escrever o ADL de mentira e o teste.** Cenários e conferências:
  - **`9070xt`:**
    - `ler` devolve uma placa com exatamente os números da tabela acima;
    - `chave` = o `PNPString` do fake, `bus` 3, `indice` 0 (o fake lista 3 entradas do mesmo barramento);
    - `deFabrica` falso, `modo` 3, `afterburner` falso;
    - `agora.ventoinhaRpm` 2552, `agora.watts` 301, `agora.usoPct` 99;
    - o registro só tem funções de leitura.
  - **`so-x2`** (a variante sem as funções antigas): a mesma placa, lida pelas X2.
  - **`od7`:** `{"ok":true,"placas":[]}`.
  - **`sem-amd`** (só uma Intel): `erro` `sem-amd`.
  - **`sem-adl`** (o `Create` devolve −1): `erro` `sem-adl`.
  - **`duas`:** duas AMD em barramentos diferentes, as duas "AMD Radeon RX 9070 XT", com chaves diferentes; a segunda com `indice` 4.
  - **`reinicia`:** o segundo `Current_Setting_Get` devolve −10 até um novo `Create`. Dois `ler` seguidos respondem bem, e o registro mostra `Destroy` e `Create` entre eles.
  - **Pedidos ruins:** `x` → `{"id":null,"ok":false,"erro":"pedido"}`; `{"id":5,"op":"voar"}` → `erro` `pedido` com `id` 5.
  - **Entrada fechada:** o processo sai com 0 em até 5 s, com `Destroy` no registro.
  - **Compilação:** o C# compila também com `-warn:4 -warnaserror+`, e as `static extern int (ADL2_\w+)` são só as da lista.
- [ ] **Step 2: Rodar e ver falhar:** `python3 desktop/scripts/teste-placa-amd-cs.py` → falha porque `desktop/placa-amd.ps1` não existe.
- [ ] **Step 3: Implementar o `placa-amd.ps1`.**
  - Do `sensores-amd.ps1` vêm a lista das placas (uma por barramento) e o PMLog.
  - A leitura do Overdrive8 segue a Global Constraints: primeiro as funções antigas, com `count` 77 e folga de 256 entradas; se elas faltarem (`EntryPointNotFoundException`), as X2 com `n = 77` passado por `ref`. As listas das X2 vêm da memória pedida pelo nosso `Aloca` e saem com `Marshal.FreeHGlobal`.
  - **JSON de entrada:** um leitor mínimo, próprio, para objetos, listas, textos (com `\uXXXX`), números (`double`), `true`, `false` e `null`.
  - **JSON de saída:** escapa o que não é ASCII como `\uXXXX`.
  - **Driver reiniciado:** quando uma leitura que já funcionou falha, chama `Destroy`, `Create` e lista as placas de novo, uma vez, e repete.
  - **Afterburner:** `Process.GetProcessesByName("MSIAfterburner").Length > 0`.
- [ ] **Step 4: Rodar e ver passar:** `python3 desktop/scripts/teste-placa-amd-cs.py` → `tudo certo`.
- [ ] **Step 5: Commit:** `git add desktop/placa-amd.ps1 desktop/scripts/adl-falso.c desktop/scripts/teste-placa-amd-cs.py && git commit -m "Ajustes da placa: o leitor lê a placa AMD pelo ADL (Overdrive8)"`

### Task 2: O leitor grava (aplicar e de fábrica)

**Files:**
- Modify: `desktop/placa-amd.ps1`, `desktop/scripts/adl-falso.c`, `desktop/scripts/teste-placa-amd-cs.py`

**Interfaces:**
- **Consumes:** `PlacaAmd.Responder`, a leitura e o fake da Tarefa 1.
- **Produces:**
  - **Pedidos:** `{"id","op":"aplicar","chave","ajuste"}` e `{"id","op":"fabrica","chave"}`.
  - **Resposta:** `{"id","ok":true,"itens":{campo: {pedido, lido}},"placa": <leitura nova>}`.
    - Os `campo` são `potencia`, `tensao`, `clock`, `memoria`, `temporizacao`, `curva` (as listas `[[°C, %]]`) e `zeroRpm`.
  - **Erros:**
    - `sem-placa` (chave desconhecida);
    - `fora-da-faixa`, com a `msg` "{campo} {v} fora da faixa (de {min} a {max})", ou temperaturas da curva que não sobem;
    - `sem-ajuste`, com a `msg` "a placa não tem {campo}";
    - `pedido` (campo desconhecido, ou valor que não é inteiro);
    - `recusou`, com a `msg` "o driver recusou a gravação ({r}: {nome})". Os nomes: 0 ok, −1 erro, −3 parâmetro inválido, −8 sem suporte, −10 placa desligada, −20 gravação incompleta, −23 precisa de administrador, −27 placa em uso; o resto, "código".
  - **`fabrica`** = `aplicar` com o padrão de cada ajuste que a placa tem e `ventoinha: {modo: "auto"}`.
  - No C#, a lista do que pode ser gravado fica numa constante, e a função que monta a estrutura lança exceção fora dela (ajuste fora da lista, modo diferente de 3 ou `reset`).
- **O fake:**
  - O `Setting_Set` aborta com "PROIBIDO" para um `requested` fora da lista, um `reset` diferente de 0 ou um modo diferente de 3.
  - Anota `SET i=v` por ajuste e `SET fim`. Devolve −3 para o `count` diferente de 76 e para o valor fora da faixa.
  - Muda a tabela e, como a placa de verdade, põe a ventoinha no automático (rotação 1500) quando a gravação vem sem a curva.
  - Cenários novos: `modo-1` (o modo atual é 1), `sem-tensao` (sem o bit da tensão) e `sem-admin` (o `Setting_Set` devolve −23).

- [ ] **Step 1: Escrever os testes**, conferindo pelo registro cada chamada do `Setting_Set`:
  - **`aplicar {potencia:-21}`:**
    - uma chamada, com `count` 76 e exatamente `{0:0, 8:2518, 9:-21, 14:0, 15:0, 19:30, 20:74, 21:50, 22:74, 23:61, 24:74, 25:72, 26:74, 27:80, 28:74, 37:-75}`;
    - `itens.potencia` = `{pedido:-21, lido:-21}`;
    - `placa.agora.ventoinhaRpm` 2552 (a ventoinha não caiu).
  - **Ventoinha:**
    - `{modo:"fixa", pct:70}`: velocidades 70, temperaturas 30/50/61/72/80 e `15:0`;
    - `{modo:"auto"}`: velocidades 15/32/49/66/100 e `15:1`;
    - `{modo:"curva", curva:[[30,40],[50,50],[61,60],[72,70],[80,80]], zeroRpm:0}`: esses valores.
  - **`fabrica`:** `9:0, 37:0, 0:0, 8:2518, 14:0`, a curva de fábrica e `15:1`; `placa.deFabrica` verdadeiro.
  - **Fora da faixa, nada gravado:** potência −40, `pct` 101 ou −20.5, a curva `[[50,40],[30,50],…]` e o campo `"vram"`.
  - **`sem-tensao`:**
    - `aplicar {tensao:-80}` → `sem-ajuste`;
    - `aplicar {potencia:-21}` grava sem o ajuste 37.
  - **`modo-1`:** primeiro `{36:3}` sozinho, depois a chamada completa.
  - **`sem-admin`:** `erro` `recusou`, com "-23: precisa de administrador" na `msg`.
  - **`duas`:** `aplicar` na chave da segunda placa grava no índice 4.
  - **Sempre:**
    - nada de "PROIBIDO" nem "ERRADA" na saída de erro;
    - toda chamada, menos a do modo, leva os ajustes de 19 a 28 e o 15.
- [ ] **Step 2: Rodar e ver falhar:** `python3 desktop/scripts/teste-placa-amd-cs.py` → as conferências de gravação falham (a resposta de `aplicar` é `erro` `pedido`).
- [ ] **Step 3: Implementar** `aplicar` e `fabrica` no C#, com a ordem da spec:
  1. completa o ajuste com os valores de agora;
  2. confere;
  3. grava o modo, se ele não for 3;
  4. grava a chamada única;
  5. lê de novo.
- [ ] **Step 4: Rodar e ver passar:** `python3 desktop/scripts/teste-placa-amd-cs.py` → `tudo certo`.
- [ ] **Step 5: Commit:** `git add desktop/placa-amd.ps1 desktop/scripts/adl-falso.c desktop/scripts/teste-placa-amd-cs.py && git commit -m "Ajustes da placa: o leitor grava numa chamada só, sempre com a curva da ventoinha"`

### Task 3: O processo do leitor (`placa-amd.js`)

**Files:**
- Create: `desktop/placa-amd.js`, `desktop/scripts/placa-falsa.js`, `desktop/scripts/teste-placa-amd.js`

**Interfaces:**
- **Consumes:** o protocolo das Tarefas 1 e 2.
- **Produces:** `require("./placa-amd.js")` = `{pedir(op, dados?): Promise<resposta>, estado(): {rodando, erro, msg, proxima}, parar(): void}`.
  - `pedir` nunca rejeita.
  - Os erros do próprio módulo são: `indisponivel` (sem leitor neste sistema), `prazo`, `caiu` e `espera`. Este último traz a `msg` "o leitor da placa volta a tentar às {hh:mm}".
- **O processo:**
  - `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File <placa-amd.ps1> -Pai <pid>`, com o `.ps1` em `process.resourcesPath` ou ao lado do módulo, como o `sensores-amd.js`;
  - `stdio: ["pipe", "pipe", "ignore"]`, `windowsHide: true`;
  - um pedido de cada vez, com `id` crescente.
- **No teste:** `PAINEL_PLACA_CMD` (um `.js` rodado com `ELECTRON_RUN_AS_NODE=1`, como os sensores), `PAINEL_PLACA_PRAZO_MS`, `PAINEL_PLACA_ESPERA_MS` (o sem AMD espera 4 vezes isso) e `PAINEL_PLACA_OCIOSO_MS`.
- **Limpeza da resposta:**
  - números finitos com |v| ≤ 100000; o que não for, `null`;
  - textos com até 300 caracteres; até 8 placas;
  - só as chaves do protocolo.
- **O leitor de mentira** (`placa-falsa.js`):
  - Lê linhas de JSON e responde como o leitor, com uma placa igual à da Tarefa 1.
  - Guarda a placa num arquivo (`PAINEL_PLACA_FALSA_ESTADO`) que o teste pode mudar: `{deFabrica, rpm, potenciaOutro, uso, recusar}`.
  - O modo vem de `PAINEL_PLACA_FALSA`: `normal`, `mudo`, `cai`, `sem-amd` ou `lixo`.
  - Anota cada pedido em `PAINEL_PLACA_LOG` como `{t, op, chave, ajuste, placaJson}`. O `placaJson` é o conteúdo de `PAINEL_PLACA_JSON` naquele instante.
  - O `aplicar` muda a placa guardada. Sem a curva no ajuste, a ventoinha vai para 1500 rpm.

- [ ] **Step 1: Escrever o teste** (`assert`, pasta temporária, imprime "ok", sai com 1 na falha):
  - **`ler`:** devolve a placa, e um processo só atende dois pedidos.
  - **Fila:** dois `pedir` ao mesmo tempo; no registro, o segundo chega depois da resposta do primeiro.
  - **`mudo`** com prazo de 300 ms:
    - `{ok:false, erro:"prazo"}`, e o processo foi encerrado;
    - logo depois, `erro` `espera`;
    - depois da espera (200 ms), um processo novo responde.
  - **`cai`:** `erro` `caiu`.
  - **`sem-amd`:** o processo é encerrado, e o próximo processo só sai depois de 4× a espera.
  - **Ocioso:** com 300 ms, `estado().rodando` é falso depois de 400 ms sem pedido.
  - **`lixo`:** `NaN`, textos de 5000 caracteres e chaves estranhas não passam.
  - **`parar()`:** encerra o processo.
- [ ] **Step 2: Rodar e ver falhar:** `node desktop/scripts/teste-placa-amd.js` → `Cannot find module '../placa-amd.js'`.
- [ ] **Step 3: Implementar.** As esperas e o ocioso seguem o `sensores-amd.js`.
- [ ] **Step 4: Rodar e ver passar:** `node desktop/scripts/teste-placa-amd.js` → `ok`.
- [ ] **Step 5: Commit:** `git add desktop/placa-amd.js desktop/scripts/placa-falsa.js desktop/scripts/teste-placa-amd.js && git commit -m "Ajustes da placa: o processo do leitor, com fila, prazos e quedas"`

### Task 4: As regras (`placa-regras.js`)

**Files:**
- Create: `desktop/placa-regras.js`, `desktop/scripts/teste-placa-regras.js`

**Interfaces:**
- **Produces** (todas puras, sem `require` de nada do Electron):
  - `ajusteDaLeitura(placa) -> ajuste`:
    - só os ajustes que a placa tem;
    - a ventoinha é `fixa` com as 5 velocidades iguais e o zero rpm desligado; `auto` com a curva e o zero rpm de fábrica; `curva` no resto.
  - `ajusteDeFabrica(placa) -> ajuste`: o padrão de cada ajuste e a ventoinha `auto`.
  - `igual(placa, ajuste) -> boolean`: comparação exata com a leitura.
  - `mesmoAjuste(a, b) -> boolean`.
  - `validar(placa, ajuste) -> null | {erro: "fora-da-faixa"|"sem-ajuste"|"pedido", msg}`: as mesmas regras do C#.
  - `limparAjuste(x) -> ajuste | null`: o que vem da página. Só as chaves do formato e inteiros; senão `null`.
  - `reiniciou(energia, desde, saiu) -> null | "normal" | "repente"`. `ligou` é a primeira marca `ligou` com `t > desde`:
    - sem ela, `null`;
    - "normal" quando há `desligou` entre `desde` e `ligou.t`, ou quando `desde < saiu < ligou.t` (o painel tinha saído pelo Sair);
    - senão, "repente".
  - `decidir({placa, e, energia, saiu, agora}) -> {acao: "nada"|"esperar"|"contar"|"bom"|"aplicar"|"travou", motivo?, volta?: "bom"|"fabrica", aviso?: "outro"|"ventoinha", reiniciarTeste?, contarReset?}`.
    - `e` = o estado da placa: `{salvo, bom, teste: {ajuste, desde, minutos}|null, resetes: [t], rpm: {referencia, amostras}, ultimaVigia, erroAte}`.
    - O algoritmo, nesta ordem:
      1. sem `placa` ou sem `e.salvo` → `nada`; `e.erroAte > agora` → `esperar`;
      2. com teste:
         - `reiniciou(energia, teste.desde, saiu)` "repente" → `travou` ("o PC desligou de repente durante o teste", volta `bom`);
         - "normal" → `aplicar` com `reiniciarTeste`;
         - `placa.deFabrica` e o ajuste do teste não é o de fábrica → `travou` ("o driver de vídeo reiniciou durante o teste", volta `bom`);
         - diferente do salvo → `aplicar` com o aviso `outro`;
         - queda da ventoinha → `aplicar` com o aviso `ventoinha`;
         - `usoPct ≥ 80` → `bom` quando `minutos + 1 ≥ 15`, senão `contar`;
         - senão, `nada`;
      3. sem teste:
         - igual ao salvo → `nada` (ou `aplicar` com o aviso `ventoinha`, se a ventoinha caiu);
         - `deFabrica` → `aplicar` se `reiniciou(energia, e.ultimaVigia, saiu)` não for `null`. Senão conta os `resetes` das últimas 24 h, mais este: com 2, e o salvo não sendo o de fábrica → `travou` ("o driver de vídeo reiniciou 2 vezes em 24 horas", volta `fabrica`, `contarReset`); com menos → `aplicar` com `contarReset`;
         - outro valor → `aplicar` com o aviso `outro`.
    - **Queda da ventoinha** = salvo `fixa`, `rpm.referencia > 0`, `agora.ventoinhaRpm != null` e `< 0,85 × referencia`.
  - `mediana(lista) -> number`.

- [ ] **Step 1: Escrever o teste**, com `P(o)` = a placa lida da Tarefa 1 com mudanças:
  - **`ajusteDaLeitura(P())`** = `{potencia:-20, tensao:-75, clock:0, memoria:2518, temporizacao:0, ventoinha:{modo:"fixa", pct:74}}`.
    - Com a curva de fábrica e o zero rpm 1 → `{modo:"auto"}`.
    - Com a curva 40/50/60/70/80 → `{modo:"curva", curva, zeroRpm:0}`.
    - Sem a tensão (`suporta: false`) → sem a chave `tensao`.
  - **`ajusteDeFabrica(P())`** = `{potencia:0, tensao:0, clock:0, memoria:2518, temporizacao:0, ventoinha:{modo:"auto"}}`.
  - **`igual`:**
    - verdadeiro com o próprio `ajusteDaLeitura`;
    - falso com a potência −21, com a `fixa` 70 e com a `auto`;
    - verdadeiro com a memória 2600 numa placa lida em 2600 (Review Focus 2).
  - **`validar`:**
    - −40 → `fora-da-faixa`;
    - a tensão numa placa sem ela → `sem-ajuste`;
    - curva com temperatura descendo → `fora-da-faixa`.
  - **`limparAjuste`:**
    - `{potencia:"x"}`, `{vram:1}` e `{ventoinha:{modo:"turbo"}}` → `null`;
    - um ajuste bom volta igual.
  - **`reiniciou`:**
    - sem marcas → `null`;
    - `ligou` depois de `desde`, com `desligou` antes dela → "normal";
    - sem `desligou` → "repente";
    - sem `desligou`, mas com `saiu` entre os dois → "normal" (Review Focus 1);
    - `ligou` antes de `desde` → `null`.
  - **`decidir`:** um caso por linha do algoritmo, com o resultado exato:
    - teste com "repente" → `travou`;
    - teste com "normal" → `aplicar` com `reiniciarTeste`;
    - teste com placa de fábrica → `travou` do driver;
    - teste com outro valor → `aplicar` com `outro`;
    - minutos 13 e uso 100 → `contar`; minutos 14 → `bom`; uso 50 → `nada`;
    - sem teste e igual → `nada`;
    - de fábrica com reinício normal → `aplicar` sem `contarReset`;
    - de fábrica sem reinício → `aplicar` com `contarReset`; com um reset de 2 h atrás → `travou` de fábrica; com um de 25 h atrás → `aplicar` com `contarReset`;
    - outro valor → `aplicar` com `outro`;
    - ventoinha `fixa` com referência 2550 e 2000 rpm → `aplicar` com `ventoinha`; 2400 → `nada`; ventoinha `auto` com 1500 → `nada`;
    - `erroAte` no futuro → `esperar`; sem placa → `nada`.
- [ ] **Step 2: Rodar e ver falhar:** `node desktop/scripts/teste-placa-regras.js` → `Cannot find module '../placa-regras.js'`.
- [ ] **Step 3: Implementar** `desktop/placa-regras.js` (`"use strict"`, `module.exports = {…}`).
- [ ] **Step 4: Rodar e ver passar:** `node desktop/scripts/teste-placa-regras.js` → `ok`.
- [ ] **Step 5: Commit:** `git add desktop/placa-regras.js desktop/scripts/teste-placa-regras.js && git commit -m "Ajustes da placa: as regras da vigia (teste, travou, de fábrica, outro programa, ventoinha)"`

### Task 5: O estado, a vigia e a ponte (`placa.js`, `main.js`, `preload.js`, instalador)

**Files:**
- Create: `desktop/placa.js`, `desktop/scripts/teste-placa.js`
- Modify:
  - `desktop/main.js`: o `require` com `try` perto do `energia.js`; o IPC `placa` depois do `kryptex-app`; a criação e o relógio da vigia no `app.whenReady()`; `before-quit` e `will-quit`; o contexto do roteiro de teste;
  - `desktop/preload.js`;
  - `desktop/package.json` (`build.files` e `extraResources`);
  - `desktop/scripts/teste-pacote.js`.

**Interfaces:**
- **Consumes:** `placa-amd.js` (Tarefa 3), `placa-regras.js` (Tarefa 4) e `energia.estado()` (`{desde, marcas: [{t, tipo}]}`).
- **Produces:**
  - **`require("./placa.js").criar({arquivo, amd, energia: () => estado|null, agora = Date.now, aoMudar: () => void})`** devolve:
    - `estado()`: `Promise<{cuidar, leitura: {quando, placas, afterburner}|null, erro, placas: {chave: {nome, salvo, bom, teste, travou, situacao, bomDesde, faltam}}, eventos}>`. Devolve e apaga os `eventos` pendentes;
    - `ler()`: `Promise<leitura|{erro, msg}>`;
    - `cuidar(sim: boolean)`: `Promise<estado>`;
    - `aplicar(chave, ajuste, {mesmoQueTravou})`: `Promise<{ok:true, itens, leitura} | {ok:false, erro, msg} | {ok:false, precisaConfirmar:true, travou:{quando, motivo}}>`;
    - `fabrica(chave)`: `Promise<igual ao aplicar>`;
    - `vigiar()`: `Promise<void>`;
    - `saiu()`: síncrono, grava o `saiu`.
  - **`situacao`** de cada placa: `"sem"` sem `cuidar`; `"teste"` com teste; `"travou"` quando o primeiro da lista `travou` é mais novo que o `bomDesde`; senão `"bom"`. `faltam` = 15 − `teste.minutos` (só com teste).
  - **`ler()`** também guarda a leitura nova como a `leitura` do estado.
  - **`placa.json`** = `{v:1, cuidar, saiu, pendentes: [evento], placas: {chave: {nome, salvo, bom, bomDesde, teste, travou: [{ajuste, quando, motivo}], resetes, rpm: {referencia, amostras}, avisos: {outro, ventoinha, parou}, ultimaVigia, erroAte}}}`.
    - É gravado inteiro, com `fs.writeFileSync` e `fs.fsyncSync`, antes de cada `aplicar` ao leitor e depois de cada mudança.
    - Um arquivo estragado vira `{v:1, cuidar:false, placas:{}}`.
  - **`evento`** = `{tipo: "travou"|"outro"|"ventoinha"|"parou", chave, nome, titulo, corpo, quando}`, com os textos da Global Constraints.
  - **Ponte:** `window.desktop.placa = {estado(), ler(), cuidar(sim), aplicar(chave, ajuste, {mesmoQueTravou}), fabrica(chave), aoMudar(fn)}`. O `aoMudar` recebe só `{tipo: "mudou"}`; os avisos chegam pelo `estado()`.
  - **IPC:** `ipcMain.handle("placa", doPainel((op, a, b, c) => …))`, com `op` em `estado|ler|cuidar|aplicar|fabrica`. O ajuste passa por `limparAjuste` (inválido → `{ok:false, erro:"pedido"}`).
  - **No teste:** o contexto do roteiro ganha `placa` (o objeto do `criar`) e `placaTeste` (`{energia: null}`; quando não é `null`, o `placa.js` usa essa energia no lugar da real).
- **As ações:**
  - **`cuidar(true)` pela primeira vez:** lê; cada placa ganha `salvo = bom = ajusteDaLeitura`, `bomDesde = agora`. Nada é gravado na placa.
  - **`aplicar` e `fabrica` sem `cuidar`:** `{ok:false, erro:"pedido", msg:"o painel não está cuidando da placa"}`. Sem a vigia, não haveria a proteção contra travamento.
  - **`aplicar`:**
    1. um ajuste igual a um da lista `travou` (`mesmoAjuste`), sem `mesmoQueTravou` → `precisaConfirmar`;
    2. guarda `salvo = ajuste` e `teste = {ajuste, desde: agora, minutos: 0}`, zera `resetes` e `rpm`, e grava o arquivo;
    3. pede ao leitor;
    4. no sucesso, `salvo` e `teste.ajuste` passam a ser o `ajusteDaLeitura` da leitura de volta. Se o leitor falhar, volta o `salvo` e o `teste` de antes.
  - **`fabrica`:** pede ao leitor `fabrica`, sem teste. No sucesso, `salvo = bom = ajusteDaLeitura` da leitura de volta e `bomDesde = agora`.
- **A vigia** (`vigiar`, uma de cada vez com as ações, numa fila):
  1. só com `cuidar`; faz um `ler`;
  2. para cada placa, `decidir`, e então:
     - `contar` → `minutos + 1`;
     - `bom` → `bom = salvo`, `teste = null`, `bomDesde = agora`;
     - `aplicar` → pede ao leitor `aplicar` com o `salvo`. Com `reiniciarTeste`, `teste.desde = agora` e `minutos = 0`; com `contarReset`, `resetes.push(agora)`. O aviso sai se o último do mesmo tipo tem mais de 1 h. Um erro do leitor → `erroAte = agora + 10 min` e o aviso `parou`;
     - `travou` → põe `{ajuste, quando, motivo}` na frente da lista (até 10); `salvo` = o `bom`, aplicado com `aplicar`. Sem `bom`, ou com volta `fabrica`, o leitor recebe `fabrica`, e o lido vira `salvo` e `bom`. Depois, `teste = null`, `resetes = []` e o aviso `travou`;
  3. depois de cada aplicação de uma ventoinha `fixa`, junta as 3 primeiras rotações e guarda a mediana em `rpm.referencia`;
  4. no fim, `ultimaVigia = agora`; grava e chama `aoMudar()`.

- [ ] **Step 1: Escrever o teste** `desktop/scripts/teste-placa.js`. Usa um `amd` de mentira em JS (uma placa como a da Tarefa 1, que responde ao `aplicar` mudando a placa, lê o `placa.json` no momento do `aplicar` e falha se dois pedidos se sobrepõem), um relógio e uma energia de mentira:
  - **Sem cuidar:** `aplicar` → `erro` `pedido`, e nada chega ao leitor.
  - **Assumir:** `cuidar(true)` → `salvo = {potencia:-20, …, ventoinha:{modo:"fixa", pct:74}}`; nenhum `aplicar` chegou ao leitor; `situacao` "bom".
  - **Aplicar:**
    - `aplicar(chave, {…, potencia:-21})`: o `placa.json` lido no momento do `aplicar` já tem o `teste` com −21; depois, `situacao` "teste" e `faltam` 15;
    - o leitor devolve a memória 2600 para um pedido de 2601 → o `salvo` fica com 2600, e a vigia seguinte não aplica (Review Focus 2);
    - o leitor responde `fora-da-faixa` → o `salvo` volta ao de antes.
  - **Travou:**
    - um ajuste da lista sem `mesmoQueTravou` → `precisaConfirmar`; com ele → `ok`;
    - 15 vigias com uso 100 → `situacao` "bom" e `bomDesde`;
    - uma marca `ligou` depois do começo do teste, sem `desligou` → o `estado()` traz um evento `travou` com o corpo exato "AMD Radeon RX 9070 XT: o PC desligou de repente durante o teste. O painel voltou para o ajuste anterior."; o leitor recebeu o `bom`; o `estado()` seguinte vem sem eventos (Review Focus 4);
    - a mesma marca com `saiu()` antes dela → `aplicar` e o teste recomeça, sem travar;
    - dois reinícios do driver em 24 h, sem teste → `travou` de fábrica, e o salvo vira o de fábrica.
  - **Avisos:**
    - outro programa → o aviso `outro` sai uma vez; na vigia seguinte, de novo diferente, o painel aplica sem aviso; depois de 1 h, avisa de novo;
    - ventoinha → depois de 3 vigias, a referência é 2552; com 1500 rpm, o painel aplica e avisa `ventoinha`;
    - erro de gravação na vigia → aviso `parou` uma vez e nenhum `aplicar` até 10 min depois; o leitor `mudo` ou caído (`{ok:false, erro:"prazo"}`) dá o mesmo resultado (Review Focus 5).
  - **Robustez:**
    - uma placa que sumiu da leitura → nada muda, sem exceção;
    - o arquivo com "{" → começa com `cuidar` falso;
    - `vigiar()` e `aplicar()` ao mesmo tempo → o leitor de mentira nunca vê dois pedidos sobrepostos.
  - **Fiação** (o texto dos arquivos):
    - o `main.js` tem `ipcMain.handle("placa"`, o `require("./placa.js")` dentro de `try`, `placa.saiu()` no `before-quit`, `PAINEL_PLACA_VIGIA_MS` e a parada do `placa-amd.js` no `will-quit`;
    - o `preload.js` tem as 6 funções;
    - o `package.json` tem `placa.js`, `placa-amd.js` e `placa-regras.js` em `build.files`, e `{"from": "placa-amd.ps1", "to": "placa-amd.ps1"}` em `extraResources`.
- [ ] **Step 2: Rodar e ver falhar:** `node desktop/scripts/teste-placa.js` → `Cannot find module '../placa.js'`.
- [ ] **Step 3: Implementar** o `placa.js` e a fiação.
  - **No `main.js`:**
    - `placa = Placa.criar({arquivo: path.join(app.getPath("userData"), "placa.json"), amd: placaAmd, energia: () => (TESTE && placaTeste.energia) || (energia ? energia.estado() : null), aoMudar: () => { if (principal && !principal.isDestroyed()) principal.webContents.send("placa", {tipo: "mudou"}); }})`;
    - a vigia, com `setTimeout` de 10 s e `setInterval` de `PAINEL_PLACA_VIGIA_MS || 60e3`.
  - **No `teste-pacote.js`:**
    - confere que cada `extraResources[].from` existe em `desktop/`;
    - com `--asar`, confere `path.join(path.dirname(asar), to)`, e uma falha aparece como "{to}: não está ao lado do pacote montado (resources)".
- [ ] **Step 4: Rodar e ver passar:**
  - `node desktop/scripts/teste-placa.js` → `ok`;
  - `node desktop/scripts/teste-pacote.js` → `ok (…placa-amd.js, placa-regras.js, placa.js…)`;
  - `node desktop/scripts/teste-sem-energia.js`, `node desktop/scripts/teste-energia.js` e `node desktop/scripts/teste-sincronia.js` → como antes.
- [ ] **Step 5: Commit:** `git add desktop/placa.js desktop/scripts/teste-placa.js desktop/main.js desktop/preload.js desktop/package.json desktop/scripts/teste-pacote.js && git commit -m "Ajustes da placa: o estado, a vigia de cada minuto e a ponte para a página"`

### Task 6: A seção no PC (Premissas › "Placa de vídeo deste PC")

**Files:**
- Modify: `mineracao.html`:
  - a marcação logo depois do `<div class="grid2 kryptex-g">` de Premissas;
  - o JS perto do bloco do app da Kryptex (`renderKxaPremissas`);
  - o `sincronizarSegundoPlano`;
  - os estilos ao lado dos de `.kxa-lims`.
- Create: `testes/placa.py`

**Interfaces:**
- **Consumes:** `window.desktop.placa` (Tarefa 5), `quando`, `esc`, `status2`, `copiarTexto`, `celAtivo`, `inicioCfg` e `lsSet`.
- **Produces:**
  - **Funções:**
    - `PODE_PLACA()` = `DESKTOP && !!(window.desktop && window.desktop.placa && typeof window.desktop.placa.estado === "function")`;
    - `var placaEst = null`;
    - `async function carregarPlaca()`;
    - `function renderPlaca()`;
    - `function avisoPlaca(ev)`;
    - `function textoAjuste(a)`;
    - `function textoSituacao(p)`;
    - `function gravarMinPlaca()`;
    - `function textoDiagPlaca()`.
  - **Marcação:**
    - `#placa-p` (`article.painel`, `hidden`) com `#placa-quando`, `#placa-cuidar`, `#placa-ab`, `#placa-inicio`, `#placa-lista` e `#placa-status`;
    - por placa, `.placa-c[data-chave]`, com `.placa-agora`, `.placa-sit` e os campos `[data-campo="potencia|tensao|clock|memoria"]` (`input type=number`, com `aria-invalid` quando fora da faixa e a `.faixa` embaixo);
    - `[data-campo="temporizacao"]` (caixa "Temporização rápida");
    - `[data-campo="ventoinha"]` (`select`: `auto` "Automática (a da AMD)", `fixa` "Fixa em", `curva` "Personalizada (feita em outro programa)", que só aparece quando é a atual) e `[data-campo="pct"]`;
    - os botões `[data-acao="aplicar|desfazer|fabrica|copiar"]`, com os rótulos da spec.
- **O comportamento:**
  - **Abrir:** `carregarPlaca()` roda ao abrir o painel, a cada `aoMudar`, ao abrir Premissas e a cada 60 s com Premissas aberta.
    - Sem `cuidar` (ou com a leitura de mais de 2 min), chama antes `window.desktop.placa.ler()`.
    - Cada evento do `estado()` vai para `avisoPlaca`, que manda `window.desktop.notificar({titulo, corpo, tela: "premissas"})` e, com `celAtivo("maquinas")`, `window.desktop.celular.enviar({tipo: "maquina", titulo, corpo})`.
  - **Mostrar:** `#placa-p` aparece só com `PODE_PLACA()` e pelo menos uma placa lida.
    - Sem `cuidar`, os campos e os botões Aplicar, Desfazer e Voltar ao de fábrica ficam desligados, com a dica "Marque "O painel cuida dos ajustes da placa" para mudar." O Copiar continua.
    - "Agora: {clock} MHz · {W} W · {°C} °C · uso {uso}%", com `toLocaleString("pt-BR")` e sem os sensores que faltam.
    - `#placa-ab` com `afterburner`.
    - `#placa-inicio` com `cuidar` e `inicioCfg.comWindows` falso.
  - **Aplicar:**
    - monta o ajuste com todos os campos que a placa tem;
    - um campo fora da faixa → `aria-invalid`, status "Corrija os campos marcados." e nada é pedido;
    - `precisaConfirmar` → status "Esse ajuste travou a placa em {quando} ({motivo}). Clique de novo em até 6 segundos para aplicar mesmo assim." e o botão "Confirmar: aplicar mesmo assim" por 6 s, como o `apDesvArmado`; o segundo clique pede com `{mesmoQueTravou: true}`;
    - deu certo → status "Aplicado. A placa leu: {textoAjuste(lido)}.", e a situação vem do estado novo;
    - deu errado → "Não deu certo: {msg}."
  - **Fábrica:** o primeiro clique arma "Confirmar: voltar ao de fábrica" por 6 s.
  - **Desfazer:** os campos voltam para o `salvo`.
  - **Copiar:** `copiarTexto(textoDiagPlaca())`, com a versão, a leitura e o estado (sem nada pessoal) e o status "Copiado. Cole na conversa com o Claude para conferir a leitura."
  - **Cuidar:** a caixa chama `cuidar(sim)`. Na primeira vez, o status é o texto de assumir. Depois, `sincronizarSegundoPlano()`, onde `plc = PODE_PLACA() && !!(placaEst && placaEst.cuidar)` entra no `bandeja` e no `iniciar`.
  - **`gravarMinPlaca()`:** monta a `min-placa` da Global Constraints e só chama `lsSet` quando ela muda.
    - Cada placa leva `ajuste` = o `salvo` e a `situacao` e o `faltam` do estado.
    - `desde` = `teste.desde` com teste, senão o `bomDesde`.
    - `travou` = `{quando, motivo}` do primeiro da lista com a situação "travou", senão `null`.

- [ ] **Step 1: Escrever `testes/placa.py`** (a parte do PC), com `FIX`, uma ponte de mentira posta pelo `extra`: `window.desktop.placa = {…}`, que anota as chamadas em `window.__placa` e responde com uma leitura da 9070 XT (os números da Tarefa 1, com `agora` = `{clockMHz: 2201, watts: 273, tempC: 43, usoPct: 100, ventoinhaRpm: 2554}`):
  - **Sem a ponte** (o `_PC` de sempre): `#placa-p` escondida e sem erros.
  - **Com a ponte e sem cuidar:**
    - a potência −20, com a faixa "de −30% a +10% · padrão 0%";
    - o rótulo da tensão com "ajuste";
    - a ventoinha `fixa` em 74;
    - o Agora "Agora: 2.201 MHz · 273 W · 43 °C · uso 100%";
    - a situação "O painel não está cuidando dos ajustes desta placa.";
    - os campos e o Aplicar desligados, com a dica.
  - **Cuidar:** marcar a caixa → `cuidar(true)` e o texto de assumir; `segundoPlano` chamado com `bandeja` e `iniciar` verdadeiros.
  - **Aplicar:**
    - potência −40 → `aria-invalid="true"`, "Corrija os campos marcados." e nenhum `aplicar`;
    - −21 → `aplicar(chave, {potencia:-21, tensao:-75, clock:0, memoria:2518, temporizacao:0, ventoinha:{modo:"fixa", pct:74}}, {mesmoQueTravou:false})`, e a situação "Em teste: faltam 15 minutos com a placa minerando. Se ela travar, o painel volta para o ajuste anterior.";
    - `precisaConfirmar` → o texto e o botão; o segundo clique leva `mesmoQueTravou: true`; depois de 6 s sem clicar, o botão volta.
  - **Botões:** Fábrica com confirmação; Desfazer.
  - **Avisos:** um evento `travou` no `estado()` → `__notificacoes` com o título "O ajuste da placa travou" e `tela` "premissas"; com o celular ligado (`celCfg` de mentira com `maquinas`), `__celular` também; o mesmo evento não sai de novo no próximo `carregarPlaca()`.
  - **Afterburner e Windows:** o aviso do Afterburner aparece com o texto exato; o do "abrir junto com o Windows" também.
  - **`min-placa`:** igual a `{v:1, cuidar:true, placas:[{nome:"AMD Radeon RX 9070 XT", ajuste, situacao:"teste", desde, faltam:15, travou:null}]}` (sem `quando`); `dadosMudaram("min-placa")` uma vez por mudança, e nenhuma vez num `carregarPlaca()` igual.
  - **Duas placas com o mesmo nome:** mudar a potência da segunda manda a chave da segunda, e os campos da primeira ficam como estavam (Review Focus 3).
  - **Tela:** fotos claro e escuro a 1366 px e a 390 px; sem rolagem para o lado; sem NaN, Infinity ou undefined no texto da seção; sem erros na página.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/placa.py` → falhas em "seção aparece" (a seção não existe).
- [ ] **Step 3: Implementar** a marcação, os estilos (os de `.painel`, `.kxa-lims`, `.acoes` e `.status`) e o JS.
- [ ] **Step 4: Rodar e ver passar:**
  - `python3 testes/placa.py` → `"falhas": []`;
  - `python3 testes/kryptex_app.py`, `python3 testes/paradas.py` e `python3 testes/visual.py` → como antes.
- [ ] **Step 5: Commit:** `git add mineracao.html testes/placa.py && git commit -m "Ajustes da placa: a seção em Premissas no PC, os avisos e a min-placa"`

### Task 7: O celular só mostra

**Files:**
- Modify: `mineracao.html` (a `SINCRONIZADAS`, o `recarregarDados` e a marcação `#placa-cel` em Premissas), `desktop/sincronia.js` (a `SINCRONIZADAS`), `testes/placa.py`

**Interfaces:**
- **Consumes:** a `min-placa` (Tarefa 6), `textoAjuste` e `textoSituacao`.
- **Produces:**
  - `"min-placa"` no fim das duas `SINCRONIZADAS`;
  - `function renderPlacaCel()`;
  - `#placa-cel` (`article.painel`, `hidden`), com o título "Placa de vídeo do PC" e, por placa, o nome, o `textoAjuste` e a situação. Sem campos e sem botões.
  - No `recarregarDados`: `if(tem("min-placa")) renderPlacaCel();`.

- [ ] **Step 1: Acrescentar ao `testes/placa.py`:**
  - **Celular** (`celular=True`) com a `min-placa` nos `dados`:
    - `#placa-cel` aparece com "Potência −20% · Tensão −75 mV · Clock máximo +0 MHz · Memória 2518 MHz · Ventoinha fixa em 74%" e a situação;
    - nenhum `input` nem `button` dentro.
  - **Situações:** "teste" com `faltam` 1 → "falta 1 minuto"; "travou" → o texto com o motivo.
  - **Sem a `min-placa`:** escondida.
  - **O PC** nunca mostra a `#placa-cel`.
  - **A lista:** as duas `SINCRONIZADAS` são iguais e têm `min-placa` (ler os dois arquivos, como o `paradas.py`).
  - **A tela:** a 390 px, sem rolagem para o lado; claro e escuro.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/placa.py` → falha em "celular mostra a placa".
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar:**
  - `python3 testes/placa.py` → `"falhas": []`;
  - `node desktop/scripts/teste-sincronia.js` → como antes;
  - `python3 testes/celular.py` e `python3 testes/mensagens_app.py` → como antes.
- [ ] **Step 5: Commit:** `git add mineracao.html desktop/sincronia.js testes/placa.py && git commit -m "Ajustes da placa: o celular mostra o ajuste e a situação, sem mudar"`

### Task 8: O programa inteiro (roteiro do Electron)

**Files:**
- Create: `desktop/scripts/teste-placa-app.js`

**Interfaces:**
- **Consumes:**
  - o contexto do roteiro (`x.placa` e `x.placaTeste`, da Tarefa 5);
  - `placa-falsa.js` (Tarefa 3), com `PAINEL_PLACA_CMD`, `PAINEL_PLACA_FALSA_ESTADO`, `PAINEL_PLACA_LOG` e `PAINEL_PLACA_JSON`;
  - `PAINEL_PLACA_VIGIA_MS=1000`.
- **Produces:**
  - grava `teste-placa-app.json` (`{ok, falhas}`) em `PAINEL_SAIDA` e sai com 1 na falha;
  - o uso, no comentário do começo, como o `teste-energia-app.js`: `PAINEL_TESTE=1 PAINEL_TESTE_ROTEIRO=teste-placa-app.js PAINEL_DADOS=<pasta vazia> PAINEL_SAIDA=<pasta> PAINEL_NTFY=http://127.0.0.1:9 PAINEL_PLACA_CMD=scripts/placa-falsa.js PAINEL_PLACA_VIGIA_MS=1000 xvfb-run -a ./node_modules/.bin/electron . --no-sandbox`.

- [ ] **Step 1: Escrever o roteiro:**
  1. **Abrir:** a página carrega e mostra `#placa-p` com a placa de mentira.
  2. **Cuidar:** marcar a caixa pela página (`executeJavaScript`, clique) → nenhum `aplicar` no registro do leitor de mentira.
  3. **Aplicar** a potência −21 pela página:
     - o registro mostra um `aplicar` com o ajuste completo;
     - o `placaJson` do registro já tinha o `teste`;
     - a seção diz "Em teste".
  4. **Teste bom:** 15 vigias com uso 100 → a seção diz "Ajuste bom desde".
  5. **Travou:**
     - outro `aplicar` (−22) e uma `placaTeste.energia` com uma marca `ligou` sem `desligou` → evento `travou`;
     - `testeSegundoPlano.notificacoes` tem "O ajuste da placa travou" uma vez só, mesmo depois de recarregar a página (`principal.webContents.reload()`) (Review Focus 4);
     - o leitor recebeu −21.
  6. **Outro programa:** `potenciaOutro: -10` no estado do falso → o painel aplica de novo e avisa uma vez.
  7. **Ventoinha:** `rpm: 1500` depois da referência → o painel aplica de novo e avisa.
  8. **`min-placa`:** no `localStorage` da janela, com `situacao` "bom".
  9. **Sair:** `app.emit("before-quit")` → o `placa.json` tem `saiu`.
- [ ] **Step 2: Ver o roteiro falhar com o leitor quebrado:** o comando do uso, dentro de `desktop/`, com `PAINEL_PLACA_FALSA=cai` → `falhas` não vazias, a começar pela seção sem placa. Isso prova que o roteiro pega um leitor que não responde.
- [ ] **Step 3: Corrigir o que o roteiro mostrar errado** com o leitor normal. Cada correção começa com um teste que falha, no teste da tarefa do arquivo mexido (`teste-placa.js` ou `testes/placa.py`).
- [ ] **Step 4: Rodar e ver passar:**
  - o mesmo comando → `{"ok": N, "falhas": []}`;
  - o roteiro de sempre (`teste.js`, com as páginas de exemplo, se estiverem à mão) e `PAINEL_TESTE_ROTEIRO=teste-energia-app.js` → como antes.
- [ ] **Step 5: Commit:** `git add desktop/scripts/teste-placa-app.js && git commit -m "Ajustes da placa: teste do programa inteiro, do cuidar ao travou"`

### Task 9: Versão 1.11.0, documentação e o teste no PC do Alex

**Files:**
- Create: `notas/v1.11.0.md`
- Modify:
  - `desktop/package.json` e `desktop/package-lock.json` (a 1.11.0);
  - `mineracao.html` (`NOVIDADES`);
  - `CLAUDE.md`: um item "Ajustes da placa (1.11.0)" em `desktop/`, com os arquivos, o protocolo, a regra da curva, a vigia, os testes e a licença (ADL e não ADLX), e os testes novos na lista de `testes/`.

- [ ] **Step 1: Subir a versão, escrever as novidades e as notas,** no formato das anteriores.
  - Primeira novidade: "Ajustes da placa no painel: potência, tensão, clock, memória e ventoinha, sem o MSI Afterburner".
  - Contar a proteção contra travamento e que o celular mostra.
- [ ] **Step 2: Rodar tudo:**
  - os testes de `testes/` (`visual.py`, `kryptex_app.py`, `celular.py`, `atualizador.py`, `pacote_celular.py`, `simulador.py`, `simulador_web.py`, `mensagens_app.py`, `paradas.py`, `conferir_nativo.py`, `placa.py`);
  - os de `desktop/scripts/` (`teste-sincronia.js`, `teste-kryptex-app.js`, `teste-sensores-amd.js`, `teste-energia.js`, `teste-sem-energia.js`, `teste-pacote.js`, `teste-placa-amd-cs.py`, `teste-placa-amd.js`, `teste-placa-regras.js`, `teste-placa.js`);
  - os roteiros do Electron.
  - Esperado: tudo como antes, mais os novos passando.
- [ ] **Step 3: Montar o instalador local** e conferir:
  - `node desktop/scripts/build-win.js` (sem `--com-dados`);
  - `node desktop/scripts/teste-pacote.js --asar desktop/dist/win-unpacked/resources/app.asar` → `ok`, com o `placa-amd.ps1` ao lado do pacote.
- [ ] **Step 4: Teste no PC do Alex, só com o OK dele.**
  - Pela pasta "mineração", um `.cmd` com um script de teste, fora do repositório, na pasta do rascunho. Ele abre o `placa-amd.ps1` da versão nova e manda `ler`; monta o `aplicar` com os valores lidos (os mesmos); manda e lê de novo. As respostas vão para um arquivo.
  - Esperado:
    - a leitura igual à de 28/10;
    - `aplicar` com `ok` e os `itens` iguais;
    - a ventoinha não cai (as rotações no `agora` do último `ler`).
  - Se algo não bater, parar e mostrar ao Alex.
- [ ] **Step 5: Commit:** `git add desktop/package.json desktop/package-lock.json mineracao.html notas/v1.11.0.md CLAUDE.md && git commit -m "Versão 1.11.0: ajustes da placa no painel, no lugar do Afterburner"`. Publicar (push no `main`) só com o OK do Alex.
