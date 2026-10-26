package br.alex.painelmineracao.celular.atualizacao;

import java.io.File;
import java.security.PublicKey;
import java.util.List;

/** O app instalado, como o Android o vê (no celular, AppAndroid). */
public interface App {
    /** versionName, do tipo X.Y.Z */
    String versao();

    /** versionCode */
    long codigo();

    /** a versão da página que vem no .apk (assets/public/painel.json); "0.0.0" se não der para ler */
    String painelEmbutido();

    /** as chaves públicas dos certificados com que o app foi assinado */
    List<PublicKey> chaves();

    /** o .apk baixado é deste app, da versão do manifesto e assinado com a mesma chave; senão, ProblemaAtualizacao("apk") */
    void conferirApk(File apk, Manifesto m) throws ProblemaAtualizacao;
}
