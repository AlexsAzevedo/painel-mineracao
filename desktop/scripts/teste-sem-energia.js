"use strict";
/* O programa abre mesmo sem o energia.js (o arquivo que faltou no instalador da 1.10.0, que nem abria): monta uma cópia
   do programa sem esse arquivo, abre no Electron com o roteiro teste-abre.js (que só roda se o main.js carregou inteiro)
   e confere que a página tem a ponte e que a energia vem vazia.
   Uso, dentro de desktop/ ou da raiz: node desktop/scripts/teste-sem-energia.js (no Linux, precisa do xvfb-run) */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const raiz = path.join(__dirname, "..");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sem-energia-"));
let falhou = true;
try {
  for (const f of ["main.js", "preload.js", "sincronia.js", "kryptex-app.js", "sensores-amd.js", "package.json"]) fs.copyFileSync(path.join(raiz, f), path.join(tmp, f));
  fs.cpSync(path.join(raiz, "app"), path.join(tmp, "app"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "scripts"));
  fs.copyFileSync(path.join(__dirname, "teste-abre.js"), path.join(tmp, "scripts", "teste-abre.js"));
  fs.symlinkSync(path.join(raiz, "node_modules"), path.join(tmp, "node_modules"), "dir");
  for (const d of ["dados", "saida", "cache"]) fs.mkdirSync(path.join(tmp, d));
  const electron = path.join(raiz, "node_modules", ".bin", "electron");
  const env = { ...process.env, PAINEL_TESTE: "1", PAINEL_TESTE_ROTEIRO: "teste-abre.js", PAINEL_DADOS: path.join(tmp, "dados"), PAINEL_SAIDA: path.join(tmp, "saida"),
    PAINEL_NTFY: "http://127.0.0.1:9", XDG_CACHE_HOME: path.join(tmp, "cache") };
  spawnSync("xvfb-run", ["-a", electron, tmp, "--no-sandbox"], { env, timeout: 90e3, stdio: "ignore" });
  let r = null;
  try { r = JSON.parse(fs.readFileSync(path.join(tmp, "saida", "teste-abre.json"), "utf8")); } catch (e) {}
  if (!r) console.error("FALHOU: o programa sem o energia.js não carregou inteiro (o roteiro de teste não rodou)");
  else if (!r.ok) console.error("FALHOU: a página abriu sem a ponte", JSON.stringify(r));
  else if (r.energia !== null) console.error("FALHOU: sem o energia.js, a energia devia vir vazia", JSON.stringify(r));
  else { console.log("ok"); falhou = false; }
} finally {
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (e) {}
}
process.exitCode = falhou ? 1 : 0;
