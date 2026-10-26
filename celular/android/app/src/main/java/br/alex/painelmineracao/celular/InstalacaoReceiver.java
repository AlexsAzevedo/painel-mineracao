package br.alex.painelmineracao.celular;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import androidx.core.content.IntentCompat;
import br.alex.painelmineracao.celular.atualizacao.Instalacao;

/**
 * A resposta do instalador do Android (só ele chama: o receptor não é exportado e o PendingIntent é do próprio app).
 * Pendente: abre a tela de confirmação do Android (ela mesma pede, na primeira vez, para deixar o Mineração instalar
 * apps). Falhou: o motivo vai para o atualizador e a página mostra. Deu certo: nada (o Android fecha o app).
 */
public class InstalacaoReceiver extends BroadcastReceiver {
    static final String ACAO = "br.alex.painelmineracao.celular.INSTALACAO";

    @Override public void onReceive(Context ctx, Intent intent) {
        if (intent == null || !ACAO.equals(intent.getAction())) return;
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, 1);
        try {
            switch (Instalacao.decidir(status)) {
                case CONFIRMAR:
                    Intent confirmar = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_INTENT, Intent.class);
                    if (confirmar == null) { falhou(ctx, "o Android não abriu a tela de instalação"); break; }
                    confirmar.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    ctx.startActivity(confirmar);
                    break;
                case FALHOU:
                    falhou(ctx, Instalacao.motivo(status, intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)));
                    break;
                default:
                    break;
            }
        } catch (Throwable t) {
            falhou(ctx, "o Android não abriu a tela de instalação");
        }
    }

    private static void falhou(Context ctx, String motivo) {
        try { AtualizadorPlugin.nucleo(ctx).falhaInstalacao(motivo); } catch (Throwable t) { /* sem onde avisar */ }
    }
}
