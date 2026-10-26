package br.alex.painelmineracao.celular.atualizacao;

/** Onde o estado do atualizador fica guardado (no Android, SharedPreferences). gravar(null) apaga; grava na hora. */
public interface Armazem {
    String ler(String chave);

    void gravar(String chave, String valor);
}
