"use strict";
/* ntfy de mentira para os testes, com o comportamento do ntfy.sh que o painel usa:
   - publicar em JSON (POST /), em texto (POST /<tópico>) e com anexo (POST /<tópico>?filename=...&message=...);
   - agendar com delay + sequence_id (o mesmo sequence_id substitui o agendado) e cancelar (DELETE /<tópico>/<seq>);
   - guardar as mensagens de cada tópico para o since= (id, hora em segundos, duração como 12h, all) e entregar ao vivo
     a quem está escutando /<tópico>/json;
   - anexos em /file/<id>.bin;
   - CORS como o ntfy.sh (Access-Control-Allow-Origin: *), inclusive a pergunta OPTIONS.
   O caminho recebido é o que vem depois do prefixo (por exemplo "/pm-x-pc/json"). */
const crypto = require("crypto");

module.exports = function criarNtfyFalso(baseUrl) {
  const ntfy = {
    publicados: [],      /* só o que veio em JSON (os avisos do celular) */
    agendados: {}, apagados: [], escutas: [], n: 0,
    topicos: new Map(),  /* tópico → mensagens, na ordem */
    arquivos: new Map(), /* id → bytes do anexo */
    pedidos: [],         /* método + caminho de cada pedido (para conferir o CORS e o since=) */
    recusar: null,       /* (req, caminho) → status para simular erro (429 etc.) */
    anexosApagados: false
  };
  const novoId = () => { ntfy.n++; return crypto.randomBytes(9).toString("base64").replace(/\+/g, "a").replace(/\//g, "b").slice(0, 12); };
  const agora = () => Math.floor(Date.now() / 1000);
  const CORS = { "Access-Control-Allow-Origin": "*" };
  function responder(res, status, corpo, tipo) {
    res.writeHead(status, { "Content-Type": tipo || "application/json", ...CORS });
    res.end(typeof corpo === "string" ? corpo : JSON.stringify(corpo));
  }
  function guardar(m) {
    const l = ntfy.topicos.get(m.topic) || [];
    l.push(m); ntfy.topicos.set(m.topic, l);
    for (const e of ntfy.escutas) if (e.topico === m.topic) { try { e.res.write(JSON.stringify(m) + "\n"); } catch (err) {} }
    return m;
  }
  /* mensagem do botão Atualizar no celular etc.: chega ao vivo no tópico */
  function entregar(topico, texto) { return guardar({ id: novoId(), time: agora(), event: "message", topic: topico, message: texto }); }
  function desde(lista, since) {
    if (!since || since === "none") return [];
    if (since === "all") return lista.slice();
    const i = lista.findIndex((m) => m.id === since);
    if (i >= 0) return lista.slice(i + 1);
    if (/^\d+$/.test(since)) return lista.filter((m) => m.time >= +since);
    const d = /^(\d+)(s|m|h)$/.exec(since);
    if (d) return lista.filter((m) => m.time >= agora() - (+d[1]) * ({ s: 1, m: 60, h: 3600 })[d[2]]);
    return lista.slice();   /* id desconhecido (expirou): o ntfy devolve o que ainda tem guardado */
  }
  function lerCorpo(req) {
    return new Promise((ok) => { const partes = []; req.on("data", (d) => partes.push(d)); req.on("end", () => ok(Buffer.concat(partes))); });
  }
  async function tratar(req, res, u, caminho) {
    ntfy.pedidos.push(`${req.method} ${caminho}${u.search}`);
    if (req.method === "OPTIONS") {
      res.writeHead(200, { ...CORS, "Access-Control-Allow-Methods": "GET, PUT, POST, PATCH, DELETE", "Access-Control-Allow-Headers": "*" });
      res.end(); return;
    }
    const recusa = ntfy.recusar && ntfy.recusar(req, caminho);
    if (recusa) { responder(res, recusa, { code: recusa * 100, http: recusa, error: "recusado no teste" }); return; }
    /* publicar em JSON (avisos no celular) */
    if (req.method === "POST" && (caminho === "/" || caminho === "")) {
      let m = null; try { m = JSON.parse((await lerCorpo(req)).toString("utf8")); } catch (e) {}
      if (!m || !m.topic) { responder(res, 400, {}); return; }
      ntfy.publicados.push({ ...m, recebido: Date.now() });
      if (m.delay && m.sequence_id) ntfy.agendados[`${m.topic}/${m.sequence_id}`] = { ...m, recebido: Date.now() };
      const msg = { id: novoId(), sequence_id: m.sequence_id || undefined, time: agora(), event: "message", topic: m.topic, title: m.title, message: m.message, tags: m.tags };
      if (!m.delay) guardar(msg);
      responder(res, 200, msg); return;
    }
    const apagar = /^\/([\w-]{1,64})\/([\w-]{1,64})$/.exec(caminho);
    if (req.method === "DELETE" && apagar) { const k = `${apagar[1]}/${apagar[2]}`; ntfy.apagados.push(k); delete ntfy.agendados[k]; responder(res, 200, { event: "message_delete" }); return; }
    /* anexo */
    const arq = /^\/file\/([\w-]{12})\.bin$/.exec(caminho);
    if (req.method === "GET" && arq) {
      const b = ntfy.anexosApagados ? null : ntfy.arquivos.get(arq[1]);
      if (!b) { responder(res, 404, { code: 40401, http: 404, error: "page not found" }); return; }
      res.writeHead(200, { "Content-Type": "application/octet-stream", "Content-Length": b.length, ...CORS }); res.end(b); return;
    }
    /* publicar em texto ou anexo */
    const pub = /^\/([\w-]{1,64})$/.exec(caminho);
    if ((req.method === "POST" || req.method === "PUT") && pub) {
      const corpo = await lerCorpo(req), nome = u.searchParams.get("filename") || req.headers["x-filename"];
      const id = novoId(), msg = { id, time: agora(), expires: agora() + 43200, event: "message", topic: pub[1] };
      if (nome || corpo.length > 4096) {
        if (corpo.length > 2 * 1024 * 1024) { responder(res, 413, { code: 41301, http: 413, error: "attachment too large" }); return; }
        ntfy.arquivos.set(id, corpo);
        msg.message = u.searchParams.get("message") || req.headers["x-message"] || "You received a file: " + (nome || "attachment.bin");
        msg.attachment = { name: nome || "attachment.bin", type: "application/octet-stream", size: corpo.length, expires: agora() + 10800, url: `${baseUrl()}/file/${id}.bin` };
      } else msg.message = corpo.toString("utf8");
      responder(res, 200, guardar(msg)); return;
    }
    /* escutar: primeiro o que estava guardado (since=), depois ao vivo */
    const escuta = /^\/([\w-]{1,64})\/json$/.exec(caminho);
    if (req.method === "GET" && escuta) {
      const topico = escuta[1], since = u.searchParams.get("since");
      res.writeHead(200, { "Content-Type": "application/x-ndjson; charset=utf-8", "Cache-Control": "no-store", ...CORS });
      res.write(JSON.stringify({ id: novoId(), time: agora(), event: "open", topic: topico }) + "\n");
      for (const m of desde(ntfy.topicos.get(topico) || [], since)) res.write(JSON.stringify(m) + "\n");
      if (u.searchParams.get("poll") === "1") { res.end(); return; }
      const e = { topico, res, since, desde: Date.now() }; ntfy.escutas.push(e);
      const vivo = setInterval(() => { try { res.write(JSON.stringify({ id: novoId(), time: agora(), event: "keepalive", topic: topico }) + "\n"); } catch (err) {} }, 20000);
      req.on("close", () => { clearInterval(vivo); ntfy.escutas = ntfy.escutas.filter((x) => x !== e); });
      return;
    }
    responder(res, 404, { code: 40401, http: 404, error: "page not found" });
  }
  /* derruba as conexões de escuta (simula a internet caindo) */
  function derrubar(topico) { for (const e of ntfy.escutas.filter((x) => !topico || x.topico === topico)) { try { e.res.destroy(); } catch (err) {} } }
  return { ntfy, tratar, entregar, derrubar };
};
