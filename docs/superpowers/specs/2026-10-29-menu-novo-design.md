# Menu novo: Resumo geral, Comprar e Configurações (1.12.0)

Data: 29/10/2026 · Pedido do Alex: "Conseguiria melhorar o layout? deixando um pouco mais organizado, minimalista, ajustar as premissas, alterando o nome para configuração criando sub menus para deixar mais clean e mais organizado tudo?"

Prévia aprovada: quadro "Novo menu do Painel de Mineração" (https://claude.ai/artifact/E5dPidANsyn6BmZP9zVbMM, versão 6), com "Computador — menu lateral curto, com botões em cima" e "Celular — menu embaixo". Os números da prévia são de exemplo; o que vale dela é onde cada coisa fica e o jeito dos menus e dos botões.

## O que o Alex escolheu

- **Menu lateral.** Ele viu primeiro uma prévia com o menu em cima e não gostou ("vamos voltar pro menu lateral msm").
- **A opção B, com botões em cima.** Entre as duas prévias de menu lateral, ele ficou com a de três itens, em que as telas de cada área aparecem no alto da tela ("Achei bem mais interessante pro layout"). Ficou também o que ele tinha pedido na outra prévia: "quero botões na parte de cima dentro da janela resumo geral com as opções do sub menu" ("as alterações citadas anteriores devem se manter").
- **Premissas vira Configurações**, com Integrações ("Tudo que for de integração"), Perfil ("o nome do usuario, dados de facebook, conta da kryptex") e Mineração ("tudo relacionado a mineração").
- **Resumo geral** reúne o Diário de ganhos, Minhas placas e o Meu setup ("montar setup iria pra resumo geral").
- **Ofertas, Analisar anúncio, Todas as placas e Simulador ficam juntos** ("em 1 janela ou organizar melhor").
- **Abrir com o Windows no quadro da placa.** Ele perguntou se dava para pôr as opções de abrir junto com o Windows e abrir minimizado no quadro da placa.
- **Primeiro o layout.** O segundo PC minerando, com o painel instalado nele como ajudante, fica para a versão seguinte ("pode sim faz primeiro o layout").

## Critérios de pronto

1. No PC (janela com 900 px ou mais), o menu lateral tem três itens: Resumo geral, Comprar e Configurações. Em cada área, o nome dela aparece grande e, embaixo, os botões das telas, como na prévia, nos dois temas.
2. No celular (menos de 900 px), a barra de baixo tem Resumo, Comprar e Configurações, e os botões das telas ficam numa linha no alto. A folha "Mais" sai.
3. Configurações tem Mineração, Perfil, Integrações, Este computador (Este celular, no celular) e Sobre, com os quadros de Premissas distribuídos como na seção 2.
   - Nenhum quadro some.
   - Nenhum quadro muda por dentro, a não ser os que a seção 2 diz que mudam.
4. A palavra Premissas sai:
   - dos textos do painel: dicas, avisos, a configuração inicial e os quadros;
   - da tela de vincular do app do celular;
   - do CLAUDE.md e do README.

   As novidades das versões antigas ficam como estão.
5. Os endereços de antes continuam abrindo a tela certa: `#premissas`, a última tela guardada (`min-view`) e os avisos do Windows com `tela:"premissas"`.
6. Nada muda nos dados, nas contas, na sincronia com o celular e no Simulador na web.
   - O app do celular não ganha .apk novo: só a página muda.
   - Todos os testes passam, com os que mudam de caminho atualizados e um teste novo do menu.

## Fora desta versão

- **O segundo PC (painel ajudante).** Vem na versão seguinte, com o desenho dela. O layout não muda nada nos dados de hoje.
- **O que tem dentro das telas.** A Visão geral é o Resumo de hoje. Os cartões de atalho da prévia (Diário, placas e setup) não entram, porque os botões no alto já levam a essas telas. As outras telas também ficam como estão por dentro, menos o que a seção 2 diz.
- **O botão de tema único da prévia.** Fica o seletor de hoje (Escuro | Claro), que já é curto e já tem teste.

## 1. Navegação

### Áreas e telas

| Área | Botão | Tela (`id`) | Hoje |
|---|---|---|---|
| Resumo geral | Visão geral | `resumo` | Resumo |
| | Diário de ganhos | `diario` | Diário de ganhos |
| | Minhas placas | `minhas` | Minhas placas |
| | Meu setup | `setup` | Montar setup |
| Comprar | Ofertas | `ofertas` | Ofertas (só onde a busca funciona, `OF_PODE()`, como hoje) |
| | Analisar anúncio | `anuncio` | Analisar anúncio |
| | Todas as placas | `placas` | Todas as placas |
| | Simulador | `sim` | Simulador |
| Configurações | Mineração | `mineracao` | parte de Premissas |
| | Perfil | `perfil` | parte de Premissas |
| | Integrações | `integracoes` | parte de Premissas |
| | Este computador | `computador` | parte de Premissas. No celular chama "Este celular"; no painel online, "Este aparelho" |
| | Sobre | `sobre` | Premissas › Sobre o painel |

- **Seções.** Cada tela continua sendo uma seção `v-<id>`, com os mesmos quadros e os mesmos ids dentro.
  - `v-premissas` vira as cinco seções de Configurações.
  - `VIEWS` ganha os ids novos e perde `premissas`.
- **Áreas.** Uma tabela `AREAS` diz as telas de cada área, na ordem dos botões.
- **Trocar de tela.** `irPara(v)` continua sendo o único jeito de trocar de tela. Ela:
  - mostra a seção;
  - marca com `aria-current="page"` o item da área e o botão da tela;
  - põe o nome da área no cabeçalho;
  - guarda `min-view` e o `#endereço`, como hoje;
  - lembra a última tela de cada área enquanto o painel estiver aberto.
- **Clicar numa área**, no menu lateral ou na barra de baixo, abre a última tela vista dela desde que o painel abriu. Na primeira vez, abre a primeira tela da área. Em Comprar, quando Ofertas não aparece, a primeira é Analisar anúncio.
- **Títulos das telas.** Os `t-<id>` são lidos pelo leitor de tela e mostrados na barra de cima do celular:
  - "Resumo geral", "Diário de ganhos", "Minhas placas", "Meu setup";
  - "Ofertas", "Analisar anúncio", "Todas as placas", "Simulador";
  - "Mineração", "Perfil", "Integrações", "Este computador" (ou "Este celular", "Este aparelho") e "Sobre".

### PC (900 px ou mais)

- **Menu lateral.**
  - Em cima, a marca, como hoje.
  - Os três itens com ícone: Resumo geral, Comprar e Configurações. O da área aberta fica com o fundo e a cor do destaque.
  - Os títulos de grupo de hoje (Acompanhar, Comprar, Ajustes) saem.
- **Rodapé do menu.**
  - O estado ao vivo (`#vivo`), num cartão. Mostra o mesmo de hoje: se está minerando e quanto entrou hoje, ou quanto o setup rende.
  - O seletor de tema.
  - O estado dos dados (`#sync`).
  - O crédito ("Criado por Alexsander Azevedo, com a ajuda do Claude"), que abre Configurações › Sobre.
- **Cabeçalho da área.** Fica no alto da tela, um só para todas as seções.
  - O nome da área aparece em letra grande, do tamanho do título de hoje.
  - Embaixo vêm os botões das telas da área, com ícone e nome, lado a lado; a linha quebra se faltar espaço.
  - O botão da tela aberta fica com o fundo, a borda e a cor do destaque.
- **Números nos botões.** Os números que hoje ficam ao lado dos itens do menu passam para os botões das telas, com os mesmos ids (`b-diario` e os outros). São os dias anotados, as placas, as ofertas que compensam, os anúncios analisados, as placas do catálogo e as máquinas do setup.
- **Título e frase de cada tela.** O título (`h1`) e a frase de explicação de cada tela ficam só para o leitor de tela, como já é no celular.
  - A saudação ("Olá, Alex"), que fica na frase do Resumo, some da vista junto com ela.
  - Os botões do cabeçalho de uma tela continuam à vista, como o "Editar dados das placas".

### Celular (menos de 900 px)

- **Barra de cima.** Fica como hoje: o título da tela, o estado da mineração e o botão de atualizar.
- **Botões das telas.** Ficam logo abaixo da barra de cima, numa linha que rola para o lado, como na prévia, sem o nome da área. A área de toque tem pelo menos 44 px de altura.
- **Barra de baixo.** Tem três itens: Resumo, Comprar e Configurações.
- **A folha Mais sai.**
  - O seletor de tema vai para Configurações › Este celular.
  - O estado da ligação com o PC (`#mais-sync`) também vai para lá.
- **O voltar do Android continua igual:** fecha a folha aberta e, sem folha, volta para o Resumo.
  - `window.fecharFolha` continua.
  - `window.fecharMais` fica, sem nada para fechar (devolve `false`).
- **O resto continua:**
  - as folhas (Diário, Minhas placas e a busca das Ofertas);
  - os cartões no lugar das tabelas;
  - os quadros que abrem pelo título. Agora são os quadros das cinco telas de Configurações.

### Endereços, links e avisos de antes

- **Endereços antigos.** `irPara("premissas")`, `#premissas` e um `min-view` antigo com "premissas" abrem Mineração.
- **Links de dentro do painel** que iam para Premissas vão para a tela nova:
  - o crédito abre Sobre;
  - "Mudar cidade", nas Ofertas, abre Perfil;
  - "Mudar premissas", em Todas as placas, abre Mineração e passa a se chamar "Mudar em Configurações".
- **Avisos do Windows.**
  - Os avisos da placa abrem Mineração.
  - O aviso da versão nova abre Este computador.
  - Um aviso antigo com `tela:"premissas"` abre Mineração.

## 2. Configurações: o que vai em cada tela

### Mineração

1. Cenário das contas (`cen-p`).
2. Receita, Energia e Investimento (os três `fieldset.grupo`).
3. Placa de vídeo deste PC (`placa-p`, no PC) e Placa de vídeo do PC (`placa-cel`, no celular).
   - **O que muda:** no PC, o quadro ganha "Abrir o painel junto com o Windows" e "Abrir minimizado".
   - São as mesmas escolhas de Este computador. Mudar num lugar muda no outro, pela mesma função (`renderInicio` desenha as duas).
   - Aparecem quando aparecem em Este computador, no programa do PC.
   - O aviso de hoje que mandava para Este computador (`placa-inicio`) sai.
4. Proteção de temperatura (quadro novo `protecao-p`). Aparece onde o quadro do app da Kryptex aparece: só no programa do PC (`PODE_KXA()`).
   - **O que muda:** a caixa "Pausar sozinho se a placa esquentar demais" e os três limites saem do quadro do app da Kryptex e vêm para cá, com os mesmos ids (`kxa-protecao`, `kxa-limtemp`, `kxa-limmem`, `kxa-limhot`).
   - Com a leitura do app desligada, uma frase diz que a proteção precisa dela (Integrações › App da Kryptex neste PC).
5. Tarifa branca (`branca-p`).
6. Como esses valores entram nas contas (`notas-prem`).

### Perfil

1. Seu perfil (`perfil-p`).
2. Facebook (quadro novo `fb-p`, só no programa do PC).
   - **O que muda:** o quadro explica para que o painel usa o Facebook: procurar placas no Marketplace e ler anúncios, numa janela escondida, com a senha só no Facebook.
   - O botão Entrar no Facebook sai de Este computador e vem para cá.
3. Sua conta da Kryptex (`kx-p`), como hoje, com o Entrar na Kryptex dele.
   - O Entrar na Kryptex de Este computador sai, porque fazia o mesmo.

### Integrações

1. App da Kryptex neste PC (`kxa-p`), agora sem a proteção.
2. App do celular (`appcel-p`).
3. Avisos no celular (`celular-p`).
4. Abrir no navegador do celular (`acesso-p`).
5. Dados de fora (`dados-fora`).

### Este computador

No celular, a tela chama Este celular; no painel online, Este aparelho.

1. No alto da tela, antes dos quadros, o estado da ligação com o PC (`#mais-sync`), à vista mesmo com os quadros fechados. Só aparece com menos de 900 px: no PC, o estado já fica no rodapé do menu (`#sync`).
2. Este celular (`estecel-p`, só no celular).
3. Este computador (`este-pc`, só no programa do PC): a atualização, o backup, o "Ao ligar o computador" e os botões Mostrar o navegador escondido, Exportar backup e Importar backup.
4. Aparência (quadro novo `aparencia-p`, em todos os aparelhos): o seletor de tema.
   - No PC, o seletor também fica no rodapé do menu.
   - Com este quadro, a tela nunca fica vazia, nem no painel online.

### Sobre

1. Sobre o painel (`sobre-p`).

Nenhuma das cinco telas fica vazia em aparelho nenhum. Seu perfil, Dados de fora, Cenário das contas, Aparência e Sobre o painel aparecem sempre.

## 3. Textos

- **Premissas.** A palavra sai de todos os textos do painel, trocada pelo caminho novo. Exemplos: "Configurações › Integrações › Dados de fora" e "Configurações › Perfil › Entrar no Facebook".
  - A configuração inicial diz "dá para mudar depois em Configurações".
  - O plano traz a lista dos textos, tirada do código.
- **Tela de vincular** do app do celular (`celular/src/ponte-app.js`): "No PC, abra o painel e vá em Configurações › Integrações › App do celular". Esse arquivo vai junto com a página, então chega aos celulares com ela.
- **Novidades.** As da 1.12.0 vão no começo de `NOVIDADES`. O texto da release vai em `notas/v1.12.0.md`.
- **Documentos.** CLAUDE.md e README ganham o menu novo e os caminhos novos.

## 4. O que depende do layout

- **Simulador na web.** `web/gerar-simulador.py` pega a seção `#v-sim` inteira e o CSS do simulador. A seção continua começando igual e com o mesmo id. Para conferir, rodar `python3 web/gerar-simulador.py` e `python3 testes/simulador_web.py`.
- **Montagem do app do celular e do programa do PC.** Em `celular/scripts/montar-www.py` e `desktop/scripts/gerar-index.py` não se espera mudança. Para conferir, montar os dois.
- **App do celular.** Só a página muda, sem .apk novo, e `python3 celular/scripts/conferir-nativo.py` continua passando.
- **Painel online** (artifact Nu8cNXUvFJKtnFFPBWFY9A). É republicado com o OK do Alex, como sempre.

## 5. Testes

**Novo `testes/menu.py`, que confere:**
- as três áreas e os botões de cada uma;
- a última tela de cada área;
- que Comprar sem Ofertas abre Analisar anúncio;
- que `#premissas` e um `min-view` antigo abrem Mineração, e que um aviso com `tela:"premissas"` também;
- cada quadro na tela certa, pela lista da seção 2;
- que as caixas de abrir com o Windows, na placa e em Este computador, andam juntas;
- os números nos botões;
- no celular: a barra de baixo, a linha de botões que rola, o voltar e o Este celular com o tema e a ligação com o PC;
- que nenhum texto à vista diz "Premissas".

**Atualizar os testes que mudam de caminho:**
- `visual.py`, inclusive as fotos de cada tela;
- `celular.py`: a folha Mais sai e Configurações abre em quadros;
- `kryptex_app.py`, `placa.py`, `atualizador.py`, `simulador.py`, `paradas.py` e `mensagens_app.py`;
- os testes do programa: `desktop/scripts/teste.js`, `teste-placa-app.js` e `teste-energia-app.js`.

**Rodar todos os testes da lista do CLAUDE.md.**

## Versão

- 1.12.0, na página e no programa do PC.
- O app do celular não muda de versão: só a página chega a ele.
