package br.alex.painelmineracao.celular.atualizacao;

import java.io.File;

/** De onde vêm as versões: o manifesto da última release e os arquivos de uma release. */
public interface Fonte {
    /** o envelope assinado da última release (painel-celular.json) */
    byte[] manifesto() throws ProblemaAtualizacao;

    /** um arquivo da release da versão dada: "painel-celular.zip" ou "Painel-de-Mineracao.apk" */
    void baixar(String versao, String arquivo, File destino, long max, long esperado, Baixador.Progresso p) throws ProblemaAtualizacao;
}
