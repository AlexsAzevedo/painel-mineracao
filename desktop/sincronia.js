/* Sincronia do Painel de Mineração: o PC e o app do celular trocam os dados do painel pelo ntfy.sh, com criptografia
   de ponta a ponta. Este arquivo é o mesmo nos dois lados: no aplicativo do computador (processo principal do Electron,
   com require) e no app do celular (WebView, como window.Sincronia). Só usa o que existe nos dois: fetch, WebCrypto e
   CompressionStream.

   - Vincular: o PC sorteia um código ("PM1-" + 32 bytes aleatórios), que vai para o celular num QR code. Do código saem,
     por HKDF-SHA256, o nome dos dois tópicos do ntfy e a chave AES-256-GCM. Sem o código, ninguém lê nem escreve nada
     que o outro lado aceite; o ntfy.sh só vê bytes embaralhados.
   - Carta: um objeto JSON → gzip → AES-256-GCM, com o remetente ("pc" ou "cel") nos dados autenticados (uma carta do
     celular não serve como carta do PC). Até ~2,9 KB vai como texto ("pm1.<iv>.<cifrado>"); maior, como anexo
     binário ("PM1" + iv + cifrado), que o ntfy.sh guarda por 3 horas.
   - O PC escreve em pm-<id>-pc e lê pm-<id>-cel; o celular, o contrário. */
(function (raiz, fabrica) {
  const S = fabrica();
  if (typeof module === "object" && module.exports) module.exports = S;
  else raiz.Sincronia = S;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const G = globalThis;
  /* chaves de dados que o PC e o celular dividem (iguais às de mineracao.html) */
  const SINCRONIZADAS = ["min-cfg", "min-placas", "min-anuncios", "min-setup", "min-diario", "min-ofertas", "min-ofertas-marcas", "min-ofertas-alerta", "min-ofertas-modelos"];
  const VERSAO = 1;
  const MAX_TEXTO = 3900;           /* mensagem comum do ntfy: até 4096 bytes */
  const MAX_ANEXO = 1900 * 1024;    /* anexo no ntfy.sh: até 2 MB */
  const enc = new TextEncoder();
  const sutil = () => G.crypto.subtle;

  /* ---------- base64url e base32 ---------- */
  function b64u(bytes) {
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return G.btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function deB64u(s) {
    s = String(s).replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    const b = G.atob(s), out = new Uint8Array(b.length);
    for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i);
    return out;
  }
  const BASE32 = "abcdefghijklmnopqrstuvwxyz234567";
  function base32(bytes) {
    let s = "", v = 0, bits = 0;
    for (const b of bytes) {
      v = ((v << 8) | b) & 0xffff; bits += 8;
      while (bits >= 5) { s += BASE32[(v >>> (bits - 5)) & 31]; bits -= 5; }
    }
    if (bits > 0) s += BASE32[(v << (5 - bits)) & 31];
    return s;
  }
  const aleatorio = (n) => G.crypto.getRandomValues(new Uint8Array(n));
  const novoId = () => b64u(aleatorio(9));

  /* ---------- código de vinculação ---------- */
  function novoCodigo() { return "PM1-" + b64u(aleatorio(32)); }
  /* aceita o código sozinho, dentro de um texto maior ou quebrado em linhas (colado de uma mensagem) */
  function lerCodigo(txt) {
    const t = String(txt || "");
    let m = /PM1-([A-Za-z0-9_-]{43})(?![A-Za-z0-9_-])/.exec(t);
    if (!m) m = /PM1-([A-Za-z0-9_-]{43})/.exec(t.replace(/\s+/g, ""));
    if (!m || !/[AEIMQUYcgkosw048]$/.test(m[1])) return null;   /* 32 bytes em base64url: a última letra só pode ser uma destas */
    return "PM1-" + m[1];
  }

  /* ---------- gzip ---------- */
  async function passar(bytes, transformacao) {
    const s = new G.Blob([bytes]).stream().pipeThrough(transformacao);
    return new Uint8Array(await new G.Response(s).arrayBuffer());
  }
  const comprimir = (b) => passar(b, new G.CompressionStream("gzip"));
  const descomprimir = (b) => passar(b, new G.DecompressionStream("gzip"));

  /* resumo curto de um valor (para saber se mudou sem guardar o valor inteiro); null é diferente de "null" */
  async function resumo(valor) {
    const h = await sutil().digest("SHA-256", enc.encode(valor === null || valor === undefined ? "\u0000nulo" : "v" + String(valor)));
    return b64u(new Uint8Array(h)).slice(0, 22);
  }

  const esperar = (ms, sinal) => new Promise((ok) => {
    const t = setTimeout(ok, ms);
    if (sinal) sinal.addEventListener("abort", () => { clearTimeout(t); ok(); }, { once: true });
  });
  function erroHttp(status) {
    const e = new Error(status === 429 ? "o ntfy.sh chegou ao limite de mensagens de hoje desta internet; amanhã volta ao normal"
      : status === 413 ? "dados grandes demais para o ntfy.sh" : `o ntfy.sh respondeu ${status}`);
    e.status = status;
    return e;
  }

  /* ---------- o canal de um código: tópicos, cifra e o ntfy ---------- */
  class Canal {
    constructor(codigo, id, chave, op) {
      this.codigo = codigo;
      this.id = id;
      this.chave = chave;
      this.servidor = String((op && op.servidor) || "https://ntfy.sh").replace(/\/+$/, "");
      this.buscar = (op && op.buscar) || ((...a) => G.fetch(...a));
      this.topico = { pc: `pm-${id}-pc`, cel: `pm-${id}-cel` };
    }
    aad(de) { return enc.encode("pm1|" + de); }
    async selar(carta, de) {
      const gz = await comprimir(enc.encode(JSON.stringify(carta)));
      const iv = aleatorio(12);
      const ct = new Uint8Array(await sutil().encrypt({ name: "AES-GCM", iv, additionalData: this.aad(de) }, this.chave, gz));
      const texto = "pm1." + b64u(iv) + "." + b64u(ct);
      if (texto.length <= MAX_TEXTO) return { texto };
      const bin = new Uint8Array(15 + ct.length);
      bin.set([0x50, 0x4d, 0x31]); bin.set(iv, 3); bin.set(ct, 15);
      if (bin.length > MAX_ANEXO) throw erroHttp(413);
      return { binario: bin };
    }
    async abrirPartes(iv, ct, de) {
      const gz = new Uint8Array(await sutil().decrypt({ name: "AES-GCM", iv, additionalData: this.aad(de) }, this.chave, ct));
      const carta = JSON.parse(new TextDecoder().decode(await descomprimir(gz)));
      if (!carta || typeof carta !== "object" || carta.v !== VERSAO || carta.de !== de) throw new Error("carta inválida");
      return carta;
    }
    async abrirTexto(t, de) {
      const p = String(t).split(".");
      if (p.length !== 3 || p[0] !== "pm1") throw new Error("não é uma carta");
      return this.abrirPartes(deB64u(p[1]), deB64u(p[2]), de);
    }
    async abrirBinario(b, de) {
      if (!b || b.length < 32 || b[0] !== 0x50 || b[1] !== 0x4d || b[2] !== 0x31) throw new Error("não é uma carta");
      return this.abrirPartes(b.subarray(3, 15), b.subarray(15), de);
    }
    /* uma mensagem do ntfy → a carta que veio nela (baixa o anexo, se for o caso). Só baixa anexos do próprio servidor. */
    async lerMensagem(m, de) {
      const a = m && m.attachment;
      if (a && a.url) {
        if (!String(a.url).startsWith(this.servidor + "/file/") || Number(a.size) > MAX_ANEXO + 1024) throw new Error("anexo estranho");
        const r = await this.buscar(String(a.url), { cache: "no-store" });
        if (!r.ok) { const e = new Error(`o anexo não está mais no ntfy (HTTP ${r.status})`); e.anexoPerdido = true; throw e; }
        return this.abrirBinario(new Uint8Array(await r.arrayBuffer()), de);
      }
      const t = String((m && m.message) || "");
      if (!t.startsWith("pm1.")) throw new Error("não é uma carta");
      return this.abrirTexto(t, de);
    }
    /* cifra e publica no tópico de quem manda; devolve a mensagem que o ntfy criou ({id, time, ...}) */
    async publicar(carta, de) {
      const s = await this.selar({ v: VERSAO, de, id: novoId(), t: Date.now(), ...carta }, de);
      const url = `${this.servidor}/${this.topico[de]}`;
      let r;
      /* POST sem cabeçalhos especiais: no celular, o navegador não precisa perguntar antes ao ntfy (CORS) */
      try { r = s.texto ? await this.buscar(url, { method: "POST", body: s.texto }) : await this.buscar(`${url}?filename=pm.bin&message=pm1`, { method: "POST", body: s.binario }); }
      catch (e) { const x = new Error("sem conexão com o ntfy.sh agora"); x.semRede = true; throw x; }
      if (!r.ok) throw erroHttp(r.status);
      try { return await r.json(); } catch (e) { return {}; }
    }
    /* escuta o tópico de quem escreve (de) até o sinal ser abortado. Reconecta sozinho e continua do último id visto.
       aoReceber(mensagem do ntfy) roda uma de cada vez, na ordem; aoEstado(true/false) diz se a conexão está de pé. */
    async escutar({ de, desde, aoReceber, aoEstado, sinal, vigia }) {
      let ultimo = desde || "12h", espera = 2000;
      const limite = vigia || 100000;   /* o ntfy.sh manda um "keepalive" a cada 45 s: 100 s em silêncio = conexão morta */
      while (!sinal.aborted) {
        const ctrl = new AbortController(), parar = () => ctrl.abort();
        sinal.addEventListener("abort", parar);
        let vigiaT = null;
        const vigiar = () => { clearTimeout(vigiaT); vigiaT = setTimeout(parar, limite); };
        let conectou = false;
        try {
          vigiar();
          const r = await this.buscar(`${this.servidor}/${this.topico[de]}/json?since=${encodeURIComponent(ultimo)}`, { signal: ctrl.signal, cache: "no-store" });
          if (!r.ok || !r.body) throw erroHttp(r.status);
          conectou = true; espera = 2000;
          if (aoEstado) aoEstado(true);
          const leitor = r.body.getReader(), dec = new TextDecoder();
          let resto = "";
          for (;;) {
            const { value, done } = await leitor.read();
            if (done) break;
            vigiar();
            resto += dec.decode(value, { stream: true });
            for (let i; (i = resto.indexOf("\n")) >= 0;) {
              const linha = resto.slice(0, i).trim(); resto = resto.slice(i + 1);
              if (!linha) continue;
              let m = null; try { m = JSON.parse(linha); } catch (e) { continue; }
              if (!m || m.event !== "message" || !m.id) continue;
              try { await aoReceber(m); } catch (e) {}
              ultimo = m.id;
            }
          }
        } catch (e) {} finally { clearTimeout(vigiaT); sinal.removeEventListener("abort", parar); }
        if (sinal.aborted) break;
        if (aoEstado) aoEstado(false);
        await esperar(conectou ? 1500 : espera, sinal);
        if (!conectou) espera = Math.min(espera * 2, 5 * 60e3);
      }
    }
  }

  async function abrirCanal(codigo, op) {
    const c = lerCodigo(codigo);
    if (!c) throw new Error("código de vinculação inválido");
    const base = await sutil().importKey("raw", deB64u(c.slice(4)), "HKDF", false, ["deriveBits", "deriveKey"]);
    const sal = enc.encode("painel-mineracao/sincronia/1");
    const bits = new Uint8Array(await sutil().deriveBits({ name: "HKDF", hash: "SHA-256", salt: sal, info: enc.encode("topico") }, base, 128));
    const chave = await sutil().deriveKey({ name: "HKDF", hash: "SHA-256", salt: sal, info: enc.encode("cripto") }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
    return new Canal(c, base32(bits).slice(0, 24), chave, op);
  }

  return { SINCRONIZADAS, VERSAO, novoCodigo, lerCodigo, abrirCanal, resumo, novoId, esperar, b64u, deB64u, base32 };
});
