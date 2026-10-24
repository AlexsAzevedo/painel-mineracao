# Painel de Mineração: como trabalhar neste repositório

- O dono é o Alex (Alexsander Azevedo). Responda em português do Brasil.
- `mineracao.html` é o painel. É a mesma página do painel online, o artifact https://claude.ai/artifact/Nu8cNXUvFJKtnFFPBWFY9A. Depois de mudar o painel, publique de novo nesse artifact passando a `url` dele: os dados do Alex ficam no banco desse artifact, e um artifact novo começaria vazio.
- `desktop/` é o aplicativo do Windows (Electron 44 e electron-builder 26).
  - `python3 desktop/scripts/gerar-index.py` monta `desktop/app/index.html` a partir de `mineracao.html`: fontes locais, política de segurança e a ponte `window.claude` → `window.desktop`.
  - Nunca use `--com-dados` num build que vai ser publicado. O instalador público não pode levar dados de ninguém: na primeira vez, o painel pergunta nome, cidade, luz e computadores.
  - `node desktop/scripts/build-win.js` gera o instalador NSIS no Linux, sem wine.
  - Teste do aplicativo: com `PAINEL_TESTE=1`, o Electron roda `desktop/scripts/teste.js` (no Linux, com `xvfb-run`). O teste começa pela configuração inicial e grava `teste-desktop.json` e as fotos em `PAINEL_SAIDA`. Ele precisa das páginas de exemplo em `PAINEL_FIXOS`, que não estão no repositório. Exemplo, dentro de `desktop/`: `PAINEL_TESTE=1 PAINEL_DADOS=<pasta vazia> PAINEL_SAIDA=<pasta> PAINEL_FIXOS=<páginas> PAINEL_DESCANSO=20000 PAINEL_SINAL_MS=2000 XDG_CACHE_HOME=<pasta> xvfb-run -a ./node_modules/.bin/electron . --no-sandbox`.
  - Abrir no celular: o aplicativo serve o painel na porta 7777 (rede de casa e Tailscale), com senha de 6 números e cookie assinado (`acesso.json`). Os dados ficam no localStorage da janela principal; a página do celular chega com um retrato deles e a lista `SINCRONIZADAS` (igual em `main.js` e em `mineracao.html`) diz quais chaves os dois dividem. Mudança no celular: `POST /api/dados` → `aplicarDadosRemotos` no PC; mudança no PC: `dados-mudaram` → evento em `/api/eventos`. A busca de ofertas pedida no celular roda no navegador escondido do PC (`/api/acao`). No modo celular, `REMOTO` é verdadeiro e `DESKTOP` é falso.
  - Avisos no celular: o aplicativo publica no ntfy.sh, num tópico aleatório guardado em `celular.json` (pasta de dados). O "sinal de vida" é uma mensagem agendada para 45 minutos com `sequence_id` `pc-sinal`, reagendada a cada 15 minutos; o botão Atualizar do resumo publica no tópico `<tópico>-p`, que o aplicativo escuta. No teste, o ntfy é um servidor de mentira dentro de `teste.js`.

## Publicar uma versão

1. Suba a versão em `desktop/package.json` e no topo de `desktop/package-lock.json`.
2. Ponha as novidades no começo de `NOVIDADES`, em `mineracao.html`, e escreva `notas/vX.Y.Z.md` (o texto da release, no formato das anteriores).
3. Teste e faça push no `main`. O workflow `.github/workflows/publicar.yml` monta o instalador e cria a release `vX.Y.Z` com o `.exe`, o `.blockmap` e o `latest.yml`. Os painéis instalados se atualizam sozinhos.

Daqui não dá para criar releases pela API do GitHub: quem publica é o workflow. A API de Actions também é bloqueada; acompanhe o andamento por `repos/AlexsAzevedo/painel-mineracao/commits/<sha>/check-runs`.
