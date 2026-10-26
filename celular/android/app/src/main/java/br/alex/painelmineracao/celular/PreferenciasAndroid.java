package br.alex.painelmineracao.celular;

import android.content.Context;
import android.content.SharedPreferences;
import br.alex.painelmineracao.celular.atualizacao.Armazem;

/** O estado do atualizador nas SharedPreferences do app, gravado na hora (commit), para sobreviver a um app que fecha. */
final class PreferenciasAndroid implements Armazem {
    private final SharedPreferences prefs;

    PreferenciasAndroid(Context c, String nome) { prefs = c.getSharedPreferences(nome, Context.MODE_PRIVATE); }

    @Override public String ler(String chave) { return prefs.getString(chave, null); }

    @Override public void gravar(String chave, String valor) {
        SharedPreferences.Editor e = prefs.edit();
        if (valor == null) e.remove(chave); else e.putString(chave, valor);
        e.commit();
    }
}
