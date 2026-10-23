"use strict";
/* Gera o instalador do Windows a partir do Linux, sem precisar do wine.
   O electron-builder monta o desinstalador rodando um .exe auxiliar no wine; no macOS ele usa um
   leitor em JavaScript que tira o desinstalador de dentro desse .exe sem executá-lo.
   Aqui ele passa a usar esse mesmo leitor (é o único lugar onde essa checagem é usada). */
const versaoMac = require("app-builder-lib/out/util/macosVersion");
versaoMac.isMacOsCatalina = () => true;

const { build, Platform, Arch } = require("electron-builder");

build({ targets: Platform.WINDOWS.createTarget(["nsis"], Arch.x64), publish: "never" })
  .then((arquivos) => console.log("\npronto:\n" + arquivos.join("\n")))
  .catch((e) => { console.error(e); process.exit(1); });
