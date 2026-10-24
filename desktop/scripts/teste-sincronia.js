"use strict";
/* Teste da sincronia (sincronia.js) com o ntfy de mentira, fora do Electron: node scripts/teste-sincronia.js
   Código de vinculação, cifra nos dois sentidos, carta grande como anexo, escuta que reconecta e continua de onde parou. */
const http = require("http");
const assert = require("assert");
const S = require("../sincronia.js");
const criarNtfyFalso = require("./ntfy-falso.js");

const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
const resultados = [];
const ok = (nome, cond, info) => { resultados.push({ nome, ok: !!cond, info }); if (!cond) console.error("FALHOU:", nome, info === undefined ? "" : JSON.stringify(info).slice(0, 400)); };

(async () => {
  let base = "";
  const falso = criarNtfyFalso(() => base);
  const srv = http.createServer((req, res) => { const u = new URL(req.url, "http://x"); falso.tratar(req, res, u, u.pathname); });
  await new Promise((r) => srv.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${srv.address().port}`;

  /* código */
  const codigo = S.novoCodigo();
  ok("código tem o formato PM1- + 43", /^PM1-[A-Za-z0-9_-]{43}$/.test(codigo), codigo);
  ok("código lido sozinho", S.lerCodigo(codigo) === codigo);
  ok("código dentro de um texto", S.lerCodigo(`Meu código: ${codigo}. Abs`) === codigo);
  ok("código quebrado em linhas", S.lerCodigo(codigo.slice(0, 20) + "\n  " + codigo.slice(20)) === codigo);
  ok("código errado recusado", S.lerCodigo("PM1-abc") === null && S.lerCodigo("") === null && S.lerCodigo(codigo.slice(0, -1) + "B") === null);
  ok("códigos diferentes a cada vez", S.novoCodigo() !== S.novoCodigo());

  const pc = await S.abrirCanal(codigo, { servidor: base });
  const cel = await S.abrirCanal(codigo, { servidor: base });
  const outro = await S.abrirCanal(S.novoCodigo(), { servidor: base });
  ok("os dois lados chegam aos mesmos tópicos", pc.topico.pc === cel.topico.pc && pc.topico.cel === cel.topico.cel && /^pm-[a-z2-7]{24}-pc$/.test(pc.topico.pc), pc.topico);
  ok("outro código, outros tópicos", outro.topico.pc !== pc.topico.pc);
  let recusou = false; try { await S.abrirCanal("PM1-nada"); } catch (e) { recusou = true; }
  ok("abrir com código inválido dá erro", recusou);

  /* cifra */
  const pequena = { v: 1, de: "pc", id: "a", t: 1, tipo: "dados", chaves: { "min-cfg": { v: '{"dolar":5.1}', t: 1 } } };
  const s1 = await pc.selar(pequena, "pc");
  ok("carta pequena vai como texto", typeof s1.texto === "string" && s1.texto.startsWith("pm1.") && s1.texto.length < 3900, s1.texto && s1.texto.length);
  ok("o outro lado abre", JSON.stringify(await cel.abrirTexto(s1.texto, "pc")) === JSON.stringify(pequena));
  let falhou = 0;
  try { await cel.abrirTexto(s1.texto, "cel"); } catch (e) { falhou++; }       /* carta do PC não passa por carta do celular */
  try { await outro.abrirTexto(s1.texto, "pc"); } catch (e) { falhou++; }      /* outro código não abre */
  const adulterada = s1.texto.slice(0, -3) + (s1.texto.slice(-3, -2) === "A" ? "B" : "A") + s1.texto.slice(-2);
  try { await cel.abrirTexto(adulterada, "pc"); } catch (e) { falhou++; }
  ok("sentido errado, outro código e carta adulterada são recusados", falhou === 3, falhou);
  /* grande: 200 anúncios com texto que não comprime muito */
  const itens = Array.from({ length: 400 }, (_, i) => ({ k: "fb:" + (1e15 + i), titulo: "RTX 3070 " + require("crypto").randomBytes(24).toString("hex"), preco: 1500 + i }));
  const grande = { v: 1, de: "pc", id: "b", t: 2, tipo: "dados", chaves: { "min-ofertas": { v: JSON.stringify({ itens }), t: 2 } } };
  const s2 = await pc.selar(grande, "pc");
  ok("carta grande vai como anexo binário", s2.binario instanceof Uint8Array && s2.binario[0] === 0x50 && s2.binario.length > 3900, s2.binario && s2.binario.length);
  ok("o anexo abre do outro lado", (await cel.abrirBinario(s2.binario, "pc")).chaves["min-ofertas"].v === grande.chaves["min-ofertas"].v);

  /* publicar e escutar: 3 cartas (a do meio grande), depois a conexão cai e volta */
  const recebidas = [], estados = [];
  const ctrl = new AbortController();
  const escuta = cel.escutar({ de: "pc", desde: "all", sinal: ctrl.signal, vigia: 4000,
    aoEstado: (x) => estados.push(x),
    aoReceber: async (m) => { recebidas.push({ id: m.id, carta: await cel.lerMensagem(m, "pc") }); } });
  await esperar(300);
  const r1 = await pc.publicar({ tipo: "dados", n: 1 }, "pc");
  await pc.publicar({ tipo: "dados", n: 2, chaves: grande.chaves }, "pc");
  await pc.publicar({ tipo: "dados", n: 3 }, "pc");
  await esperar(500);
  ok("publicar devolve o id do ntfy", typeof r1.id === "string" && r1.id.length === 12, r1);
  ok("as 3 cartas chegam, na ordem", recebidas.map((x) => x.carta.n).join() === "1,2,3", recebidas.map((x) => x.carta.n));
  ok("a carta grande chega inteira (anexo baixado)", recebidas[1] && recebidas[1].carta.chaves["min-ofertas"].v === grande.chaves["min-ofertas"].v);
  ok("cada carta tem id, hora e remetente", recebidas.every((x) => x.carta.v === 1 && x.carta.de === "pc" && x.carta.id && x.carta.t > 0));
  const anexos = [...falso.ntfy.topicos.get(pc.topico.pc)].filter((m) => m.attachment).length;
  ok("só a grande virou anexo", anexos === 1, anexos);
  /* a internet cai: o que for publicado enquanto isso chega depois, sem repetir nada */
  falso.derrubar(pc.topico.pc);
  await pc.publicar({ tipo: "dados", n: 4 }, "pc");
  await esperar(2500);
  await pc.publicar({ tipo: "dados", n: 5 }, "pc");
  await esperar(500);
  ok("depois de cair, continua de onde parou (sem repetir)", recebidas.map((x) => x.carta.n).join() === "1,2,3,4,5", recebidas.map((x) => x.carta.n));
  ok("o estado da conexão caiu e voltou", estados.includes(false) && estados[estados.length - 1] === true, estados);
  const sinces = falso.ntfy.pedidos.filter((p) => p.startsWith("GET /" + pc.topico.pc + "/json"));
  ok("reconectou com since=<último id>", sinces.length >= 2 && sinces[1].includes("since=" + recebidas[2].id), sinces);
  /* conexão morta (sem nem keepalive): a vigia derruba e reconecta */
  const nAntes = falso.ntfy.pedidos.length;
  for (const e of falso.ntfy.escutas) e.res.write("");   /* nada chega */
  falso.ntfy.escutas.forEach((e) => { e.res.write = () => true; });
  await pc.publicar({ tipo: "dados", n: 6 }, "pc");
  await esperar(6500);
  ok("a vigia reconecta uma conexão muda", recebidas.map((x) => x.carta.n).join() === "1,2,3,4,5,6" && falso.ntfy.pedidos.length > nAntes, recebidas.map((x) => x.carta.n));
  ctrl.abort(); await escuta;
  ok("parar a escuta encerra o laço", true);

  /* erros do ntfy */
  falso.ntfy.recusar = () => 429;
  let e429 = null; try { await pc.publicar({ tipo: "x" }, "pc"); } catch (e) { e429 = e; }
  ok("limite do ntfy (429) vira um erro com status", e429 && e429.status === 429 && /limite/.test(e429.message), e429 && e429.message);
  falso.ntfy.recusar = null;
  /* anexo que expirou */
  falso.ntfy.anexosApagados = true;
  const m2 = falso.ntfy.topicos.get(pc.topico.pc).find((m) => m.attachment);
  let perdido = null; try { await cel.lerMensagem(m2, "pc"); } catch (e) { perdido = e; }
  ok("anexo que expirou avisa", perdido && perdido.anexoPerdido === true, perdido && perdido.message);
  /* anexo de fora do servidor não é baixado */
  let fora = null; try { await cel.lerMensagem({ ...m2, attachment: { ...m2.attachment, url: "https://example.com/file/x.bin" } }, "pc"); } catch (e) { fora = e; }
  ok("anexo de outro endereço é recusado", fora && /estranho/.test(fora.message));
  /* resumo */
  ok("resumo diferencia null de \"null\"", (await S.resumo(null)) !== (await S.resumo("null")) && (await S.resumo("a")) === (await S.resumo("a")));

  srv.close();
  const falhas = resultados.filter((x) => !x.ok);
  console.log(`${resultados.length - falhas.length}/${resultados.length} ok`);
  process.exit(falhas.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
