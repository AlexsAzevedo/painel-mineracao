"use strict";
/* Leitor de sensores AMD de mentira para os testes (no lugar do sensores-amd.ps1): imprime uma linha de JSON a cada
   PAINEL_SENSORES_INTERVALO_MS (padrão 50 ms), no mesmo formato do leitor de verdade.
   SENSORES_FALSO_MODO: "ok" (padrão), "sem-amd" (só a linha de erro, e continua rodando, como o de verdade), "cai" (uma
   leitura e sai), "sem-sensores" (o ADL parou de mandar os sensores: a linha de erro a cada vez, e continua rodando) e
   "mudo" (roda sem imprimir nada). SENSORES_FALSO_PLACAS: a lista das placas (JSON); o consumo alterna entre placaW e
   placaW + 30.
   SENSORES_FALSO_PID: arquivo onde grava o número do processo (para o teste ver se ele foi encerrado). */
const fs = require("fs");
const modo = process.env.SENSORES_FALSO_MODO || "ok";
const intervalo = Number(process.env.PAINEL_SENSORES_INTERVALO_MS) || 50;
const placas = JSON.parse(process.env.SENSORES_FALSO_PLACAS || '[{"bus":3,"nome":"AMD Radeon RX 9070 XT","metodo":"pmlog","borda":46,"memoria":76,"quente":77,"placaW":372,"rpm":2765,"vent":83,"uso":100,"clock":2521,"clockMem":1741,"mv":855}]');
if (process.env.SENSORES_FALSO_PID) fs.writeFileSync(process.env.SENSORES_FALSO_PID, String(process.pid));
let n = 0;
function linha() {
  if (modo === "sem-amd") return { ok: false, erro: "sem-amd", msg: "nenhuma placa AMD" };
  if (modo === "sem-sensores") return { ok: false, erro: "sem-sensores", msg: "o ADL não mandou os sensores das placas AMD" };
  return { ok: true, quando: Date.now(), placas: placas.map((p) => ({ ...p, ...(p.placaW != null ? { placaW: p.placaW + (n % 2) * 30 } : {}) })) };
}
function passo() {
  if (modo !== "mudo") process.stdout.write(JSON.stringify(linha()) + "\r\n");
  n++;
  if (modo === "cai") process.exit(0);
}
passo();
setInterval(passo, intervalo);
/* como o -Pai do leitor de verdade: sai quando quem o abriu acabou */
const pai = process.ppid;
setInterval(() => { if (process.ppid !== pai) process.exit(0); }, 500);
