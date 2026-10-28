"use strict";
/* Os arquivos do programa que vão no instalador: cada módulo que o main.js carrega (e os que esses carregam, e o preload)
   tem que estar em build.files do package.json, senão o programa instalado nem abre ("Cannot find module", como na
   1.10.0, que saiu sem o energia.js). Com --asar <app.asar> (depois de montar o instalador), confere também dentro do
   pacote montado e os extraResources ao lado dele. O roteiro de teste (scripts/, só com PAINEL_TESTE) não entra.
   Uso: node desktop/scripts/teste-pacote.js [--asar desktop/dist/win-unpacked/resources/app.asar] */
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const pkg = JSON.parse(fs.readFileSync(path.join(raiz, "package.json"), "utf8"));
const files = (pkg.build && pkg.build.files) || [];
const cobre = (arq) => files.some((f) => f === arq || (f.endsWith("/**/*") && arq.startsWith(f.slice(0, -4))));

/* os módulos locais: require("./x.js") em cada arquivo, seguindo os que eles carregam */
function locais(arq, vistos) {
  if (vistos.has(arq)) return;
  vistos.add(arq);
  let txt = "";
  try { txt = fs.readFileSync(path.join(raiz, arq), "utf8"); } catch (e) { return; }
  for (const m of txt.matchAll(/require\(\s*["']\.\/([^"']+)["']\s*\)/g)) {
    if (m[1].startsWith("scripts/")) continue;
    locais(path.posix.normalize(/\.(js|json)$/.test(m[1]) ? m[1] : m[1] + ".js"), vistos);
  }
}
const mods = new Set();
locais(pkg.main || "main.js", mods);
locais("preload.js", mods);

const falhas = [];
for (const m of mods) {
  if (!fs.existsSync(path.join(raiz, m))) falhas.push(`${m}: o arquivo não existe`);
  else if (!cobre(m)) falhas.push(`${m}: carregado pelo programa, mas fora de build.files no package.json`);
}

/* os arquivos que vão ao lado do pacote (extraResources: os leitores em PowerShell) */
const extras = (pkg.build && pkg.build.extraResources) || [];
for (const x of extras) if (!fs.existsSync(path.join(raiz, x.from))) falhas.push(`${x.from}: está em extraResources, mas o arquivo não existe`);

const i = process.argv.indexOf("--asar");
if (i > 0) {
  const asar = require("@electron/asar");
  const arqAsar = path.resolve(process.argv[i + 1]);
  const dentro = new Set(asar.listPackage(arqAsar).map((f) => f.replace(/\\/g, "/").replace(/^\//, "")));
  for (const m of mods) if (!dentro.has(m)) falhas.push(`${m}: não está no pacote montado (app.asar)`);
  if (!dentro.has("app/index.html")) falhas.push("app/index.html: não está no pacote montado (app.asar)");
  for (const x of extras) if (!fs.existsSync(path.join(path.dirname(arqAsar), x.to))) falhas.push(`${x.to}: não está ao lado do pacote montado (resources)`);
}

if (falhas.length) { console.error("FALHOU:\n" + falhas.join("\n")); process.exitCode = 1; }
else console.log(`ok (${[...mods].sort().join(", ")})`);
