package br.alex.painelmineracao.celular.atualizacao;

/** O que fazer com cada resposta do instalador do Android (PackageInstaller.STATUS_*) e a frase para a página. */
public final class Instalacao {
    public enum Acao { CONFIRMAR, NADA, FALHOU }

    /* os números de PackageInstaller.STATUS_* */
    static final int PENDENTE = -1, SUCESSO = 0, BLOQUEADA = 2, ABORTADA = 3, INVALIDO = 4, CONFLITO = 5, ARMAZENAMENTO = 6, INCOMPATIVEL = 7;

    public static Acao decidir(int status) {
        if (status == PENDENTE) return Acao.CONFIRMAR;
        if (status == SUCESSO) return Acao.NADA;
        return Acao.FALHOU;
    }

    public static String motivo(int status, String msgDoAndroid) {
        switch (status) {
            case ABORTADA: return "a atualização foi cancelada";
            case INCOMPATIVEL: return "o app instalado foi assinado com outra chave: baixe pelo navegador";
            case ARMAZENAMENTO: return "falta espaço no celular";
            case BLOQUEADA: return "o Android bloqueou a instalação";
            case INVALIDO: return "o arquivo do app veio com defeito";
            case CONFLITO: return "outra instalação está em andamento";
            default: return msgDoAndroid == null || msgDoAndroid.isEmpty() ? "o Android não instalou" : "o Android não instalou (" + msgDoAndroid + ")";
        }
    }

    /** do Android 12 em diante, um app que atualiza a si mesmo pode pedir para instalar sem a tela de confirmação */
    public static boolean semPerguntar(int sdk) { return sdk >= 31; }

    private Instalacao() {}
}
