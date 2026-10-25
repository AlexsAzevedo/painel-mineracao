# Novo visual e app da Kryptex (versão 1.6.0)

Data: 25/10/2026 · Pedido do Alex: "o designer do aplicativo está muito feio e desorganizado" e "conseguimos integrar com o app da Kryptex?". Prazo: antes de segunda, 26/10, quando a RX 9070 XT começa a minerar no PC pessoal (o mesmo do painel e do app da Kryptex).

Prévia aprovada: quadro de design "Novo visual do Painel de Mineração" (https://claude.ai/artifact/3C2zoebUjjp65qgBc2FFYL), com o Resumo no PC (escuro e claro), o Resumo no celular (escuro e claro) e as Ofertas no celular.

## O que o Alex quer

Abrir o painel e ver na hora, nesta ordem: se está minerando e quanto entrou hoje; ganho e lucro do mês; ofertas de placas; retorno das placas. Mais gráficos, e fotos nas ofertas.

Escolhas dele (25/10):
- Visual da prévia, com o **tema escuro como padrão** e um botão para o claro.
- Automação no app da Kryptex: **só "pausar se esquentar demais"**. Horário de ponta e "luz custa mais do que rende" ficam de fora: no máximo viram aviso, nunca pausa.

## Critérios de pronto

1. O visual da prévia vale no aplicativo do PC, no app do celular, no painel aberto pelo navegador do celular e no painel online, nos dois temas, de 360 px a 1920 px de largura, sem rolagem para os lados.
2. Menu em três grupos no PC; barra de baixo no celular. Todas as telas de hoje continuam lá, com os mesmos dados.
3. Resumo na ordem pedida, com gráficos.
4. Ofertas com a foto do anúncio (quando o site mostra uma), o gráfico de preço × tempo para se pagar e os cartões novos.
5. No PC, o painel lê o app da Kryptex a cada minuto: estado, moeda, hashrate, temperatura, consumo, ventoinha, saldo e o ganho de hoje. Pausar e voltar a minerar pelo PC e pelo celular. Pausa sozinha se a placa esquentar demais.
6. Nada se perde: os dados de hoje, a sincronia com o celular, os avisos e os testes antigos continuam passando.

## Fora desta versão

- Pausar no horário de ponta ou quando a luz custa mais do que rende (Alex não marcou).
- Mudar overclock, algoritmo, minerador ou qualquer configuração da Kryptex pelo painel. O painel só lê e só usa a pausa.
- Ler o app da Kryptex de outros computadores pela rede. Só o do próprio PC do painel.
- Gráfico de preço por modelo ao longo do tempo nas ofertas (já existe em Todas as placas).

## 1. Visual

### Tema
- Duas paletas com os valores da prévia (escuro: fundo `#0C1016`, destaque `#F5A524`; claro: fundo `#F3F5F8`, destaque `#A35F00`), nos nomes de cor que o painel já usa (`--bg`, `--surface`, `--sunk`, `--line`, `--fg`, `--muted`, `--accent`, `--good`, `--warn`, `--bad` e os do menu e dos gráficos; a tela de vincular do app do celular também usa esses nomes), mais as novas `--onaccent` (texto sobre o destaque), `--foto` (fundo da foto), `--scrim` e `--onscrim` (selos sobre a foto).
- O escuro é o padrão. A escolha fica em `min-tema` (localStorage), por aparelho, e **não sincroniza**: o PC e o celular podem ficar diferentes.
- Um script no topo da página põe `data-tema="escuro"` ou `"claro"` no `<html>` antes de desenhar, para não piscar. `color-scheme` acompanha o tema (barras de rolagem e campos).
- Todas as cores do painel passam a vir dessas variáveis. Nenhuma cor fixa no meio do código, para os dois temas ficarem sempre legíveis.
- O botão de tema fica no rodapé do menu (PC) e em Mais (celular).

### Fontes
- Sora (600 e 700) nos títulos e números grandes; Inter (400, 500, 600 e 700) no texto. Números de tabela com algarismos de largura igual.
- No aplicativo do PC e no app do celular, os arquivos das fontes vão junto, como hoje (sem internet, a fonte continua). No painel online, pelo Google Fonts.

### Navegação
- PC (janela com 900 px ou mais): menu fixo à esquerda, em três grupos:
  - **Acompanhar**: Resumo, Diário, Minhas placas
  - **Comprar**: Ofertas, Analisar anúncio, Todas as placas
  - **Ajustes**: Montar setup, Premissas
  No rodapé do menu: o estado ao vivo (Minerando, Pausada ou Parada, e quanto entrou hoje) e o botão de tema.
- Celular ou janela estreita (menos de 900 px): barra de baixo com Resumo, Diário, Placas, Ofertas e Mais. Mais abre uma folha com Analisar anúncio, Todas as placas, Montar setup, Premissas e o tema. Botões com pelo menos 44 px de altura.
- As telas, os ids e a função de trocar de tela continuam os mesmos; muda só onde ficam os botões. Os números nos botões (por exemplo, ofertas que compensam) continuam.

### Peças comuns
- Cartões com o mesmo canto (16 a 18 px), a mesma borda e o mesmo espaçamento em todas as telas.
- Cabeçalho de cada tela: título à esquerda, ações à direita.
- Selos de estado sempre com ícone e palavra, nunca só com cor (compensa, apertado, não compensa; minerando, pausada, parada).
- As explicações longas que hoje ficam no meio das telas viram um texto curto e um "Saiba mais" que abre o resto.

### Gráficos
Seguem as regras de visualização: traços finos, marcadores de 8 px ou mais, legenda quando há mais de uma série, rótulos só nos pontos que importam, dica ao passar o mouse ou tocar, e um texto para leitores de tela com o resumo do gráfico. Sem dois eixos no mesmo gráfico. As cores de estado (verde, amarelo, vermelho) são só para estado.

## 2. Telas

### Resumo (nesta ordem)
1. **Agora**: Minerando, Pausada (até que horas) ou Parada; moeda e minerador; quanto entrou hoje e o lucro depois da luz; uma linha do ganho ao longo do dia; e quatro números: hashrate (agora e média de 24 h), temperatura (núcleo e memória), consumo (watts e a luz de hoje) e ventoinha. Botões: Pausar (1 hora, 3 horas, 8 horas, até eu voltar) ou Voltar a minerar. Embaixo, a proteção: "Pausa sozinha acima de 85 °C".
2. **O mês**: lucro, recebido, previsto e quanto as placas já se pagaram, nos mesmos cálculos de hoje.
3. **Ganho por dia**: barras dos últimos 14 dias do Diário e uma linha tracejada com o estimado da Kryptex.
4. **Retorno das placas**: para cada placa, barra do real × previsto e quando ela se paga (o que hoje fica no cartão de retorno).
5. **Ofertas perto de você**: as 3 melhores da última busca, com foto, preço e "se paga em X meses".
6. **Avisos recentes**: parou, voltou, esquentou, app da Kryptex fechado, ofertas novas.

As partes que hoje ficam no Resumo e não estão nessa lista mudam de lugar sem sumir (a lista exata fica no plano): a conta da Kryptex no site vai para Premissas, junto com o app da Kryptex; os ganhos lidos da conta esperando confirmação aparecem no Diário e num aviso curto no Resumo.

Quando não há dado (o app da Kryptex fechado, nenhum dia no Diário, nenhuma busca de ofertas), cada cartão mostra uma frase curta do que fazer, e não um cartão vazio.

### Ofertas
- Filtros de hoje viram fichas numa linha: só os que compensam, sem troca, salvos, descartados, modelo e ordem.
- **Gráfico de preço × tempo para se pagar**: um ponto por anúncio (os que passam nos filtros); círculo cheio verde para compensa, anel amarelo para apertado e X vermelho para não compensa; faixa verde até o seu prazo; nome nos 3 melhores; tocar num ponto leva ao cartão.
- **Cartão**: foto (com o site e o botão Salvar por cima), modelo e selo (anúncio novo, baixou de preço), título, cidade e distância, preço (e o preço antigo riscado), lucro por mês, quanto está abaixo do preço típico, barra do tempo para se pagar contra o prazo, e os botões Falar com o vendedor, Analisar e Mais (ver detalhes, descartar).
- Sem foto (o anúncio não tem, ou a imagem não carregou): o desenho da placa no lugar.

### As outras telas
Diário, Minhas placas, Analisar anúncio, Todas as placas, Montar setup e Premissas ganham as cores, as fontes, os cartões e os cabeçalhos novos. O conteúdo e os cálculos ficam como estão. Premissas ganha a parte "App da Kryptex" (seção 3).

## 3. App da Kryptex no PC

O app da Kryptex do Windows tem um serviço (KryptexService.exe) que responde em `http://localhost:8107`, sem senha, só dentro do computador. É o que o próprio app da Kryptex usa para desenhar a janela dele. O painel usa só estas leituras e estas duas ações:

| O quê | Pedido |
|---|---|
| Placas e processador: nome, minerando ou não, moeda, minerador, hashrate, rendimento, temperatura, clock, ventoinha | `GET /devices` |
| Saldo em BTC | `GET /balance` |
| Se está pausado | `GET /pause` |
| Cotações (por dólar) | `GET /currency-rates` |
| Moeda escolhida e nome do computador | `GET /configuration` |
| Pausar por um tempo | `PUT /pause {"pause_for": ms}` |
| Voltar a minerar | `PUT /pause {"pause": false}` |

### No aplicativo (desktop)
- Um arquivo novo, `desktop/kryptex-app.js`, faz os pedidos. Ele só conhece esses endereços: não existe jeito de a página pedir outro endereço ou mandar outra coisa. Pedidos com 4 s de limite e resposta de até 2 MB. Endereço `http://127.0.0.1:8107`, ou o de `PAINEL_KRYPTEX_LOCAL` no teste.
- Do que volta, ele separa só os campos que o painel usa (nada de nome de usuário, e-mail ou códigos). Os nomes dos campos de temperatura de memória e de consumo em watts só aparecem com a placa minerando: a leitura aceita os nomes prováveis e o painel guarda os nomes desconhecidos para o botão "Copiar o que o painel leu".
- Pausar só aceita 15 minutos (proteção), 1, 3 e 8 horas e "até eu voltar" (31 dias, como no menu do próprio app da Kryptex).
- Na ponte (`preload.js`): `window.desktop.kryptexApp.ler()`, `.pausar(minutos)` e `.voltar()`, aceitas só da janela do painel.

### No painel do PC
- Lê a cada minuto, e logo depois de pausar ou voltar. Ligado sozinho: se o app da Kryptex responder, o Resumo passa a mostrar os dados ao vivo; se não, mostra como abrir o app. Dá para desligar em Premissas.
- **Ganho de hoje**: a diferença do saldo desde a primeira leitura do dia (ou da última antes da meia-noite, se foi até 30 minutos antes), em BTC, vezes a cotação em reais do próprio app. Saldo que cai (saque) não vira ganho negativo: conta a partir dali. Quando o painel começou a ler depois de 0h30, aparece "desde HH:MM". Ao lado, o ritmo de agora: o rendimento por dia que o app da Kryptex mostra.
- **Luz de hoje**: soma do consumo medido minuto a minuto (watts × tempo, com no máximo 5 minutos por leitura, para um buraco não virar consumo), vezes a tarifa de Premissas. Sem o consumo na leitura, usa a potência da tabela das placas nas horas minerando. O lucro de hoje é o ganho menos a luz.
- **Saldo para o Diário**: as leituras do saldo do app (no máximo uma a cada 15 minutos) entram no mesmo cálculo dos dias que a conta da Kryptex já usa, com a moeda e a cotação do app. Assim os ganhos de cada dia aparecem para confirmar mesmo sem entrar na conta pelo site.
- **Avisos** (no Windows e no celular, no mesmo interruptor dos avisos das máquinas):
  - parou: uma placa que minerava fica 3 leituras seguidas sem minerar, sem pausa;
  - voltou a minerar, depois de um aviso de parada;
  - app da Kryptex fechado: respondia e ficou 5 minutos sem responder;
  - esquentou (proteção, abaixo).
- **Proteção de temperatura** (ligada, como o Alex escolheu): duas leituras seguidas com o núcleo da placa em 85 °C ou mais, ou a memória em 100 °C ou mais, pausa por 15 minutos e avisa. Se esquentar de novo em até 2 horas depois de voltar, pausa até ele voltar pelo botão e avisa. Os dois limites e o interruptor ficam em Premissas › App da Kryptex.
- **Guardado**:
  - `min-kx-app` (vai para o celular; só o PC grava): o último retrato (estado, pausa, placas, números de hoje, ritmo, saldo, hora da leitura). Gravado quando o estado muda (minerando, pausada, parada, fechado), quando há aviso, depois de pausar ou voltar, quando o celular pede e, fora isso, a cada 30 minutos. Assim o celular fica em dia sem gastar as mensagens do ntfy.sh (o PC só manda na hora para um celular com o app aberto).
  - `min-kxa-hist` (só no PC): as leituras de cada minuto das últimas 36 horas (hora, ganho, watts, hashrate, temperaturas), para a linha do dia e os números de 24 h.

### No celular (app e navegador)
- O Resumo mostra o retrato de `min-kx-app` com "lido há X minutos".
- Atualizar pede ao PC um retrato novo (pedido `kryptex-agora`, no máximo um a cada 2 minutos). Ao abrir o Resumo com o retrato com mais de 10 minutos, o celular pede sozinho, no máximo uma vez a cada 10 minutos.
- Pausar e Voltar a minerar viram pedidos ao PC (`kryptex-pausar` com os minutos, `kryptex-voltar`). O PC atende esses três pedidos mesmo no meio de uma busca de ofertas.
- Os três nomes entram na lista de pedidos aceitos do PC (`APP_PEDIDOS`), que vale para o app e para o navegador.

### Erros
- App da Kryptex fechado ou sem responder: o Agora diz "O app da Kryptex não está aberto neste PC" e o botão de pausar some. O resto do painel funciona.
- Pausar ou voltar que não deu certo: mensagem na hora, e o estado volta a ser o que o app da Kryptex disser na leitura seguinte.
- Resposta com formato inesperado: o painel mostra o que entendeu e guarda o resto para o "Copiar o que o painel leu".

## 4. Fotos das ofertas
- Na busca do Facebook e da OLX, junto com o texto de cada anúncio, a leitura pega o endereço da foto que aparece no resultado (a miniatura). Só endereços https das imagens desses sites (`*.fbcdn.net` e as de imagem da OLX). Fica no anúncio, no campo `foto`.
- A política de segurança das páginas do aplicativo, do app do celular e da página do navegador do celular passa a aceitar imagens só desses endereços.
- No painel online, o Claude.ai não deixa carregar imagens de fora: lá fica o desenho da placa.
- As fotos do Facebook expiram depois de alguns dias; foto que não carrega vira o desenho, sem erro na tela.

## 5. Testes
- Navegador (PC, 1366 px, e celular, 390 px; tema escuro e claro): Resumo com e sem dados, menu e barra de baixo, Ofertas com e sem foto, gráfico de ofertas, nenhuma rolagem para os lados, contraste do texto nos dois temas, as suítes de hoje (relatório e conta da Kryptex) passando.
- App da Kryptex de mentira (`desktop/scripts/kryptex-falso.js`): minerando, pausado, quente, parado e fechado. No teste do aplicativo: liga sozinho, mostra os números, pausa e volta (conferindo o que chegou ao app de mentira), proteção de temperatura, avisos de parou, voltou e fechado, e os pedidos do celular.
- Ofertas de mentira com foto (páginas de exemplo com miniatura).
- Os testes de hoje: sincronia, aplicativo de ponta a ponta, relatório e conta da Kryptex.

## 6. Publicação
- Versão 1.6.0 no PC. O app do celular também sobe para 1.6.0, porque a tela mudou.
- Novidades no painel, `notas/v1.6.0.md` e o CLAUDE.md (arquivo novo, chaves novas, pedidos novos).
- Push no `main` só depois do OK do Alex. Depois, conferir a release e publicar de novo o painel online.
- Segunda, com a placa minerando: ler `localhost:8107/devices` para acertar os nomes dos campos de temperatura e consumo, e ver se a porta 8107 aparece para outros aparelhos da rede de casa (se aparecer, avisar o Alex).

## Riscos
- O visual mexe em quase toda a página: a mudança vai por partes (cores e fontes; menu; Resumo; Ofertas; demais telas), com teste a cada parte.
- Os nomes dos campos com a placa minerando podem ser outros: a leitura aceita vários nomes e mostra "—" no que faltar; ajuste na segunda.
- O saldo da Kryptex pode subir em degraus (de hora em hora): o ganho de hoje mostra o que já entrou, e o ritmo de agora mostra o rendimento esperado.
