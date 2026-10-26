package br.alex.painelmineracao.celular.atualizacao;

/**
 * Conta quanto tempo a página nova ficou na tela sem confirmar que abriu. Só conta com o app na frente: em segundo plano
 * o Android pode pausar a página, e isso não é defeito dela.
 */
public final class Vigia {
    private final long limite;
    private long acumulado, desde;
    private boolean naFrente;

    public Vigia(long limite) { this.limite = limite; }

    /** recomeça a contagem (página nova em prova) */
    public synchronized void zerar(long agora, boolean naFrente) {
        acumulado = 0;
        this.naFrente = naFrente;
        desde = agora;
    }

    public synchronized void naFrente(long agora) {
        if (naFrente) return;
        naFrente = true;
        desde = agora;
    }

    public synchronized void atras(long agora) {
        if (!naFrente) return;
        acumulado += Math.max(0, agora - desde);
        naFrente = false;
    }

    public synchronized long falta(long agora) {
        long usado = acumulado + (naFrente ? Math.max(0, agora - desde) : 0);
        return Math.max(0, limite - usado);
    }

    public boolean venceu(long agora) { return falta(agora) <= 0; }
}
