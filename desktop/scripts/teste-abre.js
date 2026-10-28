"use strict";
/* Roteiro de teste que só confere que o programa carregou inteiro (este roteiro roda no fim do main.js) e que a página
   tem a ponte. Grava teste-abre.json em PAINEL_SAIDA. Usado por teste-sem-energia.js. */
const fs = require("fs");
const os = require("os");
const path = require("path");

module.exports = async (principal, x) => {
  const js = (c) => principal.webContents.executeJavaScript(c);
  let ok = false;
  for (let i = 0; i < 150 && !ok; i++) {
    ok = await js("!!(window.desktop && window.desktop.segundoPlano)").catch(() => false);
    if (!ok) await new Promise((r) => setTimeout(r, 100));
  }
  const energia = ok ? await js("window.desktop.energia()").catch((e) => "erro: " + e.message) : "sem página";
  fs.writeFileSync(path.join(process.env.PAINEL_SAIDA || os.tmpdir(), "teste-abre.json"), JSON.stringify({ ok, energia }));
  x.app.exit(ok ? 0 : 1);
};
