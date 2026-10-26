package br.alex.painelmineracao.celular.atualizacao;

/**
 * Algo que impediu a atualização agora. O código diz o tipo, para a página mostrar uma frase simples:
 * rede, nao-achou, assinatura, formato, tamanho, sha256, pacote, espaco, apk, endereco, erro.
 */
public final class ProblemaAtualizacao extends Exception {
    public final String codigo;

    public ProblemaAtualizacao(String codigo, String detalhe) {
        super(detalhe);
        this.codigo = codigo;
    }
}
