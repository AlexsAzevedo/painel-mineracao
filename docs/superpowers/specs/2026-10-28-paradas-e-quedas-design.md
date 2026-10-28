# Paradas e quedas de energia no Diário (1.10.0)

Data: 28/10/2026 · Pedido do Alex: "Poderia melhorar a parte financeira? Exemplo, esses últimos 2 dias tive interrupções por falta de energia e isso repercutiu no valor recebido. Teria como o sistema identificar essas interrupções e informar que de tal horário até tal horário estava fora, ou informar que o valor está reduzido devido a isso?"

## O que o Alex escolheu

- **Onde ver:** no dia do Diário, no ganho de hoje (Resumo), numa lista de todas as paradas e num aviso no celular quando a mineração volta.
- **Caminho:** o PC anota as próprias paradas. Ele usa as leituras de cada minuto do app da Kryptex, a hora em que o Windows ligou e a marca de desligamento normal. As paradas dos dias que já passaram saem das leituras que já estão guardadas.
- As partes 1 a 4 foram aprovadas como estão abaixo.

## Critérios de pronto

1. **Queda de energia.** O PC apaga e liga de novo, e isso vira uma parada com o motivo "Falta de energia?". Ela tem o início (a última leitura minerando), a hora em que o Windows ligou e o fim (a placa minerando de novo), com precisão de 1 minuto.
2. **Os outros motivos.** O painel reconhece "PC desligado", "PC em suspensão", "App da Kryptex fechado", "Placa parada", "Pausada por você" e "Pausada pela proteção de temperatura". Paradas com menos de 10 minutos ficam de fora, menos a falta de energia.
3. **Os dias que já passaram.** Na primeira vez, as paradas que estão nas leituras já guardadas aparecem com o motivo "Sem leitura (PC desligado ou sem energia)" ou "Sem minerar (motivo não registrado)".
4. **O Diário.** Cada dia mostra as paradas e quanto deixou de ganhar. Nos dias que vieram da Kryptex, as horas minerando descontam as paradas, e o estimado e a margem real usam essas horas.
5. **A lista de paradas.** Fica no Diário, com o período, o filtro "Só falta de energia" e o botão "Copiar a lista".
6. **O Resumo.** O "Hoje até agora" mostra as paradas de hoje, e os Avisos recentes ganham um aviso por parada.
7. **O celular.** Recebe a lista e mostra o mesmo. Quando a mineração volta depois de uma parada, chega um aviso no lugar do "O PC voltou" de hoje. As pausas da própria pessoa não geram aviso.
8. **Sem quebrar nada.** Não aparece NaN, Infinity nem undefined. Funciona no PC e no celular, no claro e no escuro, sem rolagem para o lado, e os testes de antes continuam passando.

## Fora desta versão

- **As outras máquinas da conta:** continuam como hoje, pela conta da Kryptex. Esta versão olha só este PC, o único que minera.
- **O registro de eventos do Windows** (o caminho 3).
- **Queda de internet:** o app da Kryptex não diz se a pool está recebendo o trabalho.
- **O valor recebido** de qualquer dia e o relatório do ano para o contador: não mudam.

## 1. Como o painel percebe uma parada

### As leituras e as marcas

- **Cada leitura de minuto** do app da Kryptex passa a guardar o estado:
  - minerando;
  - pausada por você;
  - pausada pela proteção (`kxa.protecao`);
  - parada (o app aberto, sem minerar e sem pausa);
  - fechado (o app não respondeu).

  Os minutos com o app fechado também viram leituras, sem saldo.
- **O programa do PC anota marcas novas** num arquivo da pasta de dados (`energia.json`):
  - o desligamento normal do Windows (`session-end`), que também vale para reiniciar;
  - a suspensão e a volta dela (`powerMonitor`: `suspend` e `resume`);
  - o "Sair" do painel.
- **A hora em que o Windows ligou** é calculada a cada abertura: agora menos `os.uptime()`.
- **A página pergunta isso** por uma função nova da ponte, `window.desktop.energia()`. Ela devolve a hora em que o Windows ligou e as marcas.

### O que é uma parada

- Uma parada é um período em que este PC não minerou.
  - **Início:** a última leitura com a placa minerando.
  - **Fim:** a primeira leitura com ela minerando de novo.
- **Buraco:** duas leituras seguidas com mais de 10 minutos entre elas. Nesse tempo, o painel não estava lendo.
- **O motivo de um buraco** vem das marcas que caem dentro dele:
  - O Windows ligou depois do começo do buraco, com uma marca de desligamento normal dentro dele: **"PC desligado"**.
  - O Windows ligou depois do começo do buraco, sem essa marca: **"Falta de energia?"**. O PC apagou de repente; um travamento ou o cabo puxado deixam o mesmo rastro, por isso a interrogação.
  - O Windows não ligou de novo, mas há uma marca de suspensão: **"PC em suspensão"**.
  - Nenhuma das marcas (o painel foi fechado com o PC ligado): **não vira parada**, porque o painel não sabe se a placa minerou nesse tempo.
- **Leituras sem minerar:** viram "App da Kryptex fechado", "Placa parada", "Pausada por você" ou "Pausada pela proteção de temperatura", pelo estado de cada leitura.
- **Uma parada só:** os pedaços seguidos viram uma parada única. Numa queda de energia, os pedaços são o buraco, depois o app da Kryptex abrindo e depois o minerador começando. Quando o PC religou, a parada guarda também a hora em que o Windows ligou.
- **O motivo da parada:** é o do primeiro pedaço. A exceção é quando algum pedaço é "Falta de energia?", "PC desligado" ou "PC em suspensão": aí vale o primeiro desses. Uma queda de energia no meio de uma pausa sua aparece como falta de energia, e não como pausa.
- **Mínimo:** paradas com menos de 10 minutos não entram, menos "Falta de energia?", que entra sempre.
- **Parada que não acabou:** fica na lista sem fim ("parada desde 02:15").
- **PC religou e a placa não voltou:** se, 15 minutos depois de o Windows ligar, a placa ainda não estiver minerando, o celular recebe o aviso "O PC voltou, mas a placa ainda não está minerando". Esse aviso sai uma vez por parada e não sai nas pausas da pessoa.

### Os dias que já passaram (uma vez só, na primeira abertura desta versão no PC)

- **Das leituras de cada minuto** (as últimas 36 horas): buracos de mais de 10 minutos viram "Sem leitura (PC desligado ou sem energia)". As sequências sem minerar viram "Sem minerar (motivo não registrado)", porque as leituras antigas não guardam o estado.
- **Antes disso,** dos saldos guardados (`kxHist.saldos`, até 6 dias, a cada 15 minutos com o app da Kryptex e a cada 30 pelo site): buracos de mais de 45 minutos viram "Sem leitura" com horário aproximado.
  - Isso só vale quando o saldo cresceu menos da metade do que a conta vinha rendendo por hora vezes a duração do buraco.
  - Assim, um tempo com o painel fechado e a placa minerando não vira parada.
- **As paradas desses dias não geram avisos.**

## 2. O que fica guardado

- **A chave nova `min-paradas`:** `{v: 1, lista: [...], retro: true}`. Cada parada tem:
  - `ini`, `fim` e `ligou`: horas em ms; `fim` fica vazio enquanto a parada dura, e `ligou` é a hora em que o Windows ligou, quando for o caso;
  - `motivo`: um destes, `energia`, `desligado`, `suspensao`, `fechado`, `parada`, `pausa`, `protecao`, `semleitura` ou `semminerar`;
  - `aprox`: se o horário é aproximado, de meia hora;
  - `ritmo`: os R$ por hora da conta no fim da parada (veja a parte 4).
- **Quanto tempo:** 1 ano, contado pelo fim de cada parada, e no máximo 1.000 paradas.
- **Quem grava:** só o PC, e só quando uma parada começa, muda ou acaba (não a cada minuto).
- **Celular:** a chave entra na lista `SINCRONIZADAS`, a mesma em `desktop/sincronia.js` e em `mineracao.html`. O app do celular recebe as paradas como recebe o Diário.
- **Só no PC:**
  - as marcas do `energia.json`, dos últimos 30 dias;
  - as leituras de cada minuto, como hoje (36 horas), agora com o estado.

## 3. Onde aparece

### Os textos

- **Os motivos:** "Falta de energia?", "PC desligado", "PC em suspensão", "App da Kryptex fechado", "Placa parada", "Pausada por você", "Pausada pela proteção de temperatura", "Sem leitura (PC desligado ou sem energia)" e "Sem minerar (motivo não registrado)".
- **A frase de cada motivo,** usada na lista copiada e nos avisos:

  | Motivo | Frase |
  |---|---|
  | `energia` | "o PC apagou de repente (falta de energia?) e ligou às {hh:mm}" |
  | `desligado` | "o PC foi desligado e ligou às {hh:mm}" |
  | `suspensao` | "o PC ficou em suspensão" |
  | `fechado` | "o app da Kryptex ficou fechado" |
  | `parada` | "a placa ficou parada" |
  | `pausa` | "a mineração ficou pausada por você" |
  | `protecao` | "a mineração ficou pausada pela proteção de temperatura" |
  | `semleitura` | "o PC ficou sem leitura (desligado ou sem energia)" |
  | `semminerar` | "a placa ficou sem minerar" |

- **Durações:** no formato que o painel já usa (`duracao`): "45 min", "6 h 10 min".
- **Valores:** "uns R$ 6,35", sempre com "uns", porque são estimativas.
- **Horários aproximados:** levam "~" na frente ("~02:00").

### Diário de ganhos

- **No dia** (a linha da tabela no PC, o cartão no celular): embaixo da data, as horas minerando, como hoje ("17,8 h"). Abaixo, a linha "Fora do ar {duração}: {início}–{fim} ({motivo}) · deixou de ganhar uns {R$}". Com mais de uma parada no dia, os horários vêm em sequência: "Fora do ar 6 h 50 min: 02:15–08:25 (Falta de energia?), 14:00–14:40 (Placa parada) · deixou de ganhar uns R$ 7,05".
- **Embaixo dos números do período:** "No período, a placa ficou {duração} parada ({n} paradas) e deixou de ganhar uns {R$}". Sem paradas no período, a frase não aparece.
- **Nos ganhos lidos da Kryptex** (os dias que esperam ser anotados): "{h} h minerando · parou {duração} ({motivo principal})".
- **No gráfico "Real × estimado por dia":** a dica do dia ganha a linha "parou {duração}".

### Lista de paradas

- Um painel "Paradas" no Diário, embaixo da tabela.
- **Cada parada mostra:**
  - o dia;
  - de que horas a que horas ("desde 02:15" enquanto não acabou);
  - a duração;
  - o motivo;
  - quanto deixou de ganhar.
- **A mais nova vem primeiro.** Segue os botões de período do Diário (7 dias, 30 dias, tudo) e tem o filtro "Só falta de energia".
- **O botão "Copiar a lista"** copia o que está na tela, uma linha por parada: "{dd/mm/aaaa}, das {hh:mm} às {hh:mm} ({duração}): {frase do motivo}". Exemplo: "27/10/2026, das 02:15 às 08:25 (6 h 10 min): o PC apagou de repente (falta de energia?) e ligou às 08:19".
- **Sem paradas:** "Nenhuma parada neste período".

### Resumo

- **"Hoje até agora"** (no PC e no celular): uma linha "parou {duração} hoje ({início}–{fim}, {motivo})". Com a placa parada agora: "parada desde {hh:mm}".
- **Avisos recentes:** um aviso por parada, quando ela acaba: "Ficou fora do ar das {início} às {fim} ({duração}): {frase}. Deixou de ganhar uns {R$}". Ele usa o caminho dos avisos que já existem (`avisoKx`), com a cor verde de "voltou".

### Celular

- O app mostra as mesmas telas com as paradas que vêm do PC.
- **Aviso quando a mineração volta:** sai uma vez por parada de 10 minutos ou mais (sempre, na falta de energia). Não sai nas pausas da pessoa nem nas paradas dos dias que já passaram.
  - Título: "{placa} voltou a minerar".
  - Texto: "Ficou fora do ar das {início} às {fim} ({duração}): {frase}. Deixou de ganhar uns {R$}".
  - Ele substitui o "{placa} voltou a minerar" de hoje (que só dizia a moeda e o hashrate) e o "O PC voltou" que o programa do PC manda ao abrir. Esse segundo continua só quando a leitura do app da Kryptex está desligada nas Premissas.
- **Durante a queda,** o "O PC parou de dar sinal" (o sinal de vida) continua como está.

## 4. As contas

- **Horas minerando do dia:** 24 horas menos as paradas daquele dia.
  - Uma parada que atravessa a meia-noite é cortada nos limites de cada dia.
  - Hoje conta até agora.
  - Nos dias da Kryptex (`kx.dias`), isso substitui as horas que vinham das leituras de meia em meia hora (`horasDoDiaKx`).
  - No dia em que o painel começou a ler a conta, continua valendo só o tempo desde a primeira leitura (`parcial`).
- **Estimado do dia:** a mesma conta de hoje (`estDia(data, horas)`), com essas horas. "Recebeu do estimado" e a margem real passam a comparar o que entrou com as horas minerando de verdade.
- **O ritmo da conta:** quanto ela vinha rendendo por hora minerando, em R$.
  - É a soma do valor dos dias da Kryptex dos 7 dias antes do dia em que a parada começou, dividida pela soma das horas minerando desses dias.
  - Entram só os dias inteiros, não aproximados e com horas. Valor em US$ vira R$ pelo dólar das Premissas.
  - Sem nenhum dia assim: a estimativa da Kryptex deste PC por hora, com a correção pelo real (a mesma do simulador, `fatorSim`).
  - Fica guardado na parada quando ela acaba (`ritmo`), e nas antigas, quando elas são achadas.
- **Deixou de ganhar:** as horas paradas vezes o `ritmo` da parada. No dia, entram só as horas da parada que caem naquele dia. O aviso, o Diário, a lista e o Resumo usam o mesmo número.
- **Dias que já estão no Diário:**
  - Os que vieram da Kryptex (`fonte: "kryptex"`): as horas são corrigidas sozinhas quando uma parada que cai naquele dia é achada ou muda.
  - Os que a pessoa digitou: continuam com as horas dela, e o dia mostra as paradas.
- **O que não muda:** o valor recebido de cada dia e o relatório do ano.

## 5. Testes

Com dados inventados e o relógio fixo, como os de agora.

**Na página** (um arquivo novo, `testes/paradas.py`, com a ponte do PC de mentira: o app da Kryptex lido a cada minuto e a `window.desktop.energia()`):
- **Queda de energia:** as leituras param, o Windows liga depois e não há marca de desligamento. A parada tem o motivo `energia` e o início, a hora em que ligou e o fim certos.
- **Os outros motivos:** desligamento normal, suspensão, painel fechado com o PC ligado (não vira parada), app fechado, placa parada, pausa da pessoa e pausa da proteção.
- **Os limites de tempo:** menos de 10 minutos fica de fora, menos a falta de energia; uma parada que atravessa a meia-noite; uma parada que ainda não acabou.
- **"O PC voltou, mas a placa ainda não está minerando"** 15 minutos depois de o Windows ligar.
- **Os dias que já passaram:** saem das leituras de 36 horas e dos saldos, e a conferência pelo saldo descarta o painel fechado com a placa minerando. Esses dias não geram avisos.
- **As contas:** as horas dos dias da Kryptex, o estimado, a margem real, o ritmo (com e sem 7 dias) e quanto deixou de ganhar. Os dias digitados pela pessoa não mudam.
- **Os textos:** a linha do dia, a frase do período, os ganhos lidos da Kryptex, a dica do gráfico, a lista (ordem, período, filtro e o texto copiado), o "Hoje até agora" e os Avisos recentes.
- **Os avisos do celular:** uma vez por parada, nenhum nas pausas da pessoa, e o "O PC voltou" do programa só com a leitura do app da Kryptex desligada.
- **O celular** (`REMOTO`): mostra o mesmo a partir de `min-paradas`.
- **A tela:** claro e escuro, PC e celular (390 px), sem rolagem para o lado, botões de 44 px no celular e sem NaN, Infinity nem undefined.

**No programa do PC:** `node desktop/scripts/teste-energia.js` testa a hora em que o Windows ligou, as marcas de desligamento normal, suspensão e "Sair", o arquivo e a ponte.

**O que já existe:**
- A chave `min-paradas` está igual nas duas listas `SINCRONIZADAS`.
- Os testes de antes continuam passando: os da página, os do programa e o do aplicativo com o Electron.
- O Simulador na web continua sendo gerado (`python3 web/gerar-simulador.py` e `python3 testes/simulador_web.py`).

## 6. Publicação

- **Versões:** a do programa do PC sobe para 1.10.0, e a página do app do celular chega sozinha. O app do celular continua na 1.8.0, porque a parte Android não muda.
- **Textos da versão:** as novidades no começo de `NOVIDADES` e o texto da release em `notas/v1.10.0.md`.
- **Painel online:** republicado no mesmo artifact (Nu8cNXUvFJKtnFFPBWFY9A, pela `url`). Lá não há app da Kryptex, então a lista fica vazia e o Diário fica como hoje.
- **Release:** o push no `main` publica a release, por isso só sai com o OK do Alex.
- **CLAUDE.md:** ganha as paradas no item do app da Kryptex e a chave nova na lista de dados que o PC e o celular dividem.
