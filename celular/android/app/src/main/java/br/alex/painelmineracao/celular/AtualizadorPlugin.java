package br.alex.painelmineracao.celular;

import android.content.Context;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import br.alex.painelmineracao.celular.atualizacao.Atualizador;
import br.alex.painelmineracao.celular.atualizacao.Baixador;
import br.alex.painelmineracao.celular.atualizacao.FonteGithub;
import br.alex.painelmineracao.celular.atualizacao.Instalacao;
import br.alex.painelmineracao.celular.atualizacao.Vigia;
import com.getcapacitor.Bridge;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

/**
 * A ponte entre a página e o atualizador (Java puro, em atualizacao/). Antes de a página carregar (load), escolhe a
 * pasta da página: a do .apk, a baixada que já confirmou que abre, ou uma nova em prova. Troca de página com
 * Bridge.setServerBasePath (o endereço continua https://localhost, então os dados da página continuam os mesmos) e, com
 * uma página nova em prova, vigia: se ela não confirmar em 30 s com o app na frente, volta para a anterior.
 * Nada aqui pode derrubar o app: um erro do atualizador só faz o app não se atualizar agora.
 */
@CapacitorPlugin(name = "Atualizador")
public class AtualizadorPlugin extends Plugin {
    /* um atualizador e uma fila por processo: a atividade pode ser recriada, os downloads continuam os mesmos */
    private static final ExecutorService FILA = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "atualizador");
        t.setDaemon(true);
        return t;
    });
    private static volatile Atualizador nucleo;
    private static volatile AtualizadorPlugin ativo;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private final Vigia vigia = new Vigia(Atualizador.VIGIA);
    private volatile boolean naFrente;
    private final Runnable conferirVigia = this::conferirVigia;

    private volatile long instalandoDesde;

    private static long agora() { return SystemClock.elapsedRealtime(); }

    /** o atualizador do processo (o receptor da instalação também usa, mesmo com o app fechado) */
    static synchronized Atualizador nucleo(Context ctx) {
        if (nucleo == null) {
            Context c = ctx.getApplicationContext();
            nucleo = new Atualizador(c.getFilesDir(), new PreferenciasAndroid(c, "atualizador"), System::currentTimeMillis,
                new FonteGithub(FonteGithub.BASE, new Baixador(true)), new AppAndroid(c), AtualizadorPlugin::mudou);
        }
        return nucleo;
    }

    @Override public void load() {
        try {
            ativo = this;
            nucleo(getContext());
            String pasta = nucleo.aoAbrir();
            if (pasta != null) gravarCaminho(pasta);
            if (nucleo.emProva()) vigia.zerar(agora(), false);   /* começa a contar quando a atividade vier para a frente */
            if (nucleo.procuraVencida()) FILA.execute(() -> nucleo.procurar(false));
        } catch (Throwable t) {
            /* o app abre com a página que o Capacitor escolher sozinho */
        }
    }

    /** o estado mudou (pode vir de outra thread): a página ativa fica sabendo */
    private static void mudou(JSONObject estado) {
        AtualizadorPlugin p = ativo;
        if (p != null) {
            try { p.notifyListeners("estado", p.paraPagina(estado)); } catch (Throwable t) { /* página fechando */ }
        }
    }

    /** o estado do atualizador mais o que só o Android sabe: se o app já pode instalar apps e a versão do Android */
    private JSObject paraPagina(JSONObject estado) {
        JSObject r;
        try { r = JSObject.fromJSONObject(estado); } catch (Exception e) { r = new JSObject(); }
        boolean pode = true;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try { pode = getContext().getPackageManager().canRequestPackageInstalls(); } catch (Throwable t) { pode = false; }
        }
        r.put("podeInstalar", pode);
        r.put("android", Build.VERSION.SDK_INT);
        return r;
    }

    private boolean pronto(PluginCall call) {
        if (nucleo != null) return true;
        call.reject("atualizador indisponível");
        return false;
    }

    /* ---------- trocar de página ---------- */

    private void gravarCaminho(String pasta) {
        getContext().getSharedPreferences("CapWebViewSettings", Context.MODE_PRIVATE).edit().putString("serverBasePath", pasta).commit();
    }

    /** na thread principal: grava a escolha (vale na próxima abertura) e recarrega a página daquela pasta */
    private void trocarPara(String pasta) {
        try {
            gravarCaminho(pasta);
            Bridge b = getBridge();
            if (pasta.isEmpty()) b.setServerAssetPath(Bridge.DEFAULT_WEB_ASSET_DIR);
            else b.setServerBasePath(pasta);
        } catch (Throwable t) {
            /* fica a página de agora; na próxima abertura vale o que foi gravado */
        }
    }

    private void agendarVigia() {
        principal.removeCallbacks(conferirVigia);
        if (naFrente && nucleo != null && nucleo.emProva()) principal.postDelayed(conferirVigia, Math.max(0, vigia.falta(agora())));
    }

    private void conferirVigia() {
        try {
            if (nucleo == null || !nucleo.emProva()) return;
            if (!vigia.venceu(agora())) { agendarVigia(); return; }
            String para = nucleo.vigiaVenceu();
            if (para != null) trocarPara(para);
        } catch (Throwable t) {
            /* sem a vigia, a próxima abertura do app decide (duas aberturas sem confirmar voltam) */
        }
    }

    @Override protected void handleOnResume() {
        super.handleOnResume();
        naFrente = true;
        vigia.naFrente(agora());
        agendarVigia();
        /* voltou da tela do Android sem resposta (ou ela ficou para trás): libera o botão de novo */
        if (instalandoDesde > 0 && agora() - instalandoDesde > 5_000 && nucleo != null) {
            instalandoDesde = 0;
            nucleo.instalando(false);
        }
    }

    @Override protected void handleOnPause() {
        naFrente = false;
        principal.removeCallbacks(conferirVigia);
        vigia.atras(agora());
        super.handleOnPause();
    }

    /* ---------- métodos para a página ---------- */

    @PluginMethod public void estado(PluginCall call) {
        if (!pronto(call)) return;
        call.resolve(paraPagina(nucleo.estado()));
    }

    @PluginMethod public void procurar(PluginCall call) {
        if (!pronto(call)) return;
        boolean forcar = Boolean.TRUE.equals(call.getBoolean("forcar", false));
        FILA.execute(() -> nucleo.procurar(forcar));
        call.resolve(paraPagina(nucleo.estado()));
    }

    @PluginMethod public void usarPainel(PluginCall call) {
        if (!pronto(call)) return;
        String pasta = nucleo.usarPainel();
        call.resolve(paraPagina(nucleo.estado()));
        if (pasta != null) {
            principal.post(() -> {
                vigia.zerar(agora(), naFrente);
                trocarPara(pasta);
                agendarVigia();
            });
        }
    }

    @PluginMethod public void painelOk(PluginCall call) {
        if (!pronto(call)) return;
        JSONObject e = nucleo.painelOk(call.getString("versao"));
        if (!nucleo.emProva()) principal.removeCallbacks(conferirVigia);
        call.resolve(paraPagina(e));
    }

    @PluginMethod public void visto(PluginCall call) {
        if (!pronto(call)) return;
        nucleo.visto(call.getString("qual"));
        call.resolve(paraPagina(nucleo.estado()));
    }

    /** instala o .apk baixado; um toque só vale uma vez (os métodos rodam um de cada vez, na mesma thread) */
    @PluginMethod public void instalarApp(PluginCall call) {
        if (!pronto(call)) return;
        if (nucleo.estado().optBoolean("instalando")) { call.resolve(paraPagina(nucleo.estado())); return; }
        File apk = nucleo.apkPronto();
        if (apk == null) {
            nucleo.falhaInstalacao("o arquivo do app sumiu; ele é baixado de novo na próxima procura");
        } else {
            instalandoDesde = agora();
            nucleo.instalando(true);
            Context c = getContext().getApplicationContext();
            Thread t = new Thread(() -> {
                try { InstaladorApk.instalar(c, apk); }
                catch (Throwable e) { instalandoDesde = 0; nucleo.falhaInstalacao(Instalacao.motivo(1, e.getMessage())); }
            }, "instalar-app");
            t.setDaemon(true);
            t.start();
        }
        call.resolve(paraPagina(nucleo.estado()));
    }
}
