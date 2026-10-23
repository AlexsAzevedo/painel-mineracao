"use strict";
/* Ponte entre o painel (página) e o aplicativo: só estas funções ficam visíveis para a página. */
const { contextBridge, ipcRenderer } = require("electron");
const versao = ((process.argv || []).find((a) => a.startsWith("--painel-versao=")) || "--painel-versao=1.0.0").split("=")[1];

contextBridge.exposeInMainWorld("desktop", {
  versao,
  navegar: (url) => ipcRenderer.invoke("navegar", String(url)),
  texto: (max) => ipcRenderer.invoke("texto", Number(max) || 50000),
  buscarAnuncios: (op) => ipcRenderer.invoke("buscar-anuncios", { site: String(op && op.site || ""), url: String(op && op.url || ""), rolar: Number(op && op.rolar) || 0 }),
  detalhesAnuncio: (op) => ipcRenderer.invoke("detalhes-anuncio", { site: String(op && op.site || ""), url: String(op && op.url || "") }),
  entrarFacebook: () => ipcRenderer.invoke("facebook"),
  mostrarNavegador: () => ipcRenderer.invoke("mostrar-navegador"),
  salvarArquivo: (nome, conteudo) => ipcRenderer.invoke("salvar-arquivo", String(nome), String(conteudo)),
  abrirArquivo: () => ipcRenderer.invoke("abrir-arquivo"),
  /* backup automático do dia, numa pasta (Documentos › Painel de Mineração › Backups, ou a que a pessoa escolher) */
  backup: {
    salvar: (dia, conteudo) => ipcRenderer.invoke("backup-salvar", String(dia), String(conteudo)),
    info: () => ipcRenderer.invoke("backup-info"),
    escolherPasta: () => ipcRenderer.invoke("backup-escolher-pasta"),
    abrirPasta: () => ipcRenderer.invoke("backup-abrir-pasta")
  },
  /* alerta de ofertas: aviso do Windows, ícone perto do relógio / abrir com o Windows, e o pedido de abrir uma tela (clique num aviso) */
  notificar: (n) => ipcRenderer.invoke("notificar", { titulo: String(n && n.titulo || ""), corpo: String(n && n.corpo || ""), tela: String(n && n.tela || ""), chave: String(n && n.chave || "") }),
  segundoPlano: (op) => ipcRenderer.invoke("segundo-plano", op ? { bandeja: !!op.bandeja, iniciar: !!op.iniciar } : null),
  janelaVisivel: () => ipcRenderer.invoke("janela-visivel"),
  aoAbrir: (fn) => {
    if (typeof fn !== "function") return;
    ipcRenderer.on("abrir", (_e, p) => { try { fn({ tela: String(p && p.tela || ""), chave: String(p && p.chave || "") }); } catch (err) {} });
  },
  /* atualização automática: estado atual, procurar agora, instalar a que já baixou e aviso a cada mudança */
  atualizacao: {
    estado: () => ipcRenderer.invoke("atualizacao-estado"),
    procurar: () => ipcRenderer.invoke("atualizacao-procurar"),
    instalar: () => ipcRenderer.invoke("atualizacao-instalar"),
    aoMudar: (fn) => {
      if (typeof fn !== "function") return;
      ipcRenderer.on("atualizacao", (_e, estado) => { try { fn(estado); } catch (err) {} });
    }
  }
});
