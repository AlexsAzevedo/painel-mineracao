# Painel de Mineração

Painel para acompanhar mineração de criptomoedas com placas de vídeo: quanto cada placa ganha e gasta de luz, em quanto tempo se paga, ofertas de placas usadas perto de você, diário de ganhos e montagem do setup.

## Baixar

Baixe o instalador do Windows na [versão mais nova](https://github.com/AlexsAzevedo/painel-mineracao/releases/latest) (arquivo `Painel-de-Mineracao-Setup-….exe`, em *Assets*). Quem já tem o painel instalado recebe as versões novas sozinho.

Na primeira vez, o painel pergunta o seu nome, a cidade, a conta de luz e os seus computadores. Os dados ficam só no seu computador.

## O que tem aqui

- `mineracao.html`: o painel (a mesma página do painel online).
- `desktop/`: o aplicativo do Windows, que embala o painel.
- `notas/`: as novidades de cada versão.

Quando a versão em `desktop/package.json` muda, o GitHub monta o instalador e publica a versão com o texto de `notas/vX.Y.Z.md` ([.github/workflows/publicar.yml](.github/workflows/publicar.yml)). O instalador não leva dados de ninguém.

---
Criado por **Alexsander Azevedo** · alexs_azevedo@hotmail.com · WhatsApp (79) 99920-2165  
Desenvolvido com a ajuda do Claude, a inteligência artificial da Anthropic.
