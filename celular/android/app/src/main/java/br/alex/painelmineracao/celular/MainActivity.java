package br.alex.painelmineracao.celular;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        /* o atualizador escolhe a pasta da página antes de ela carregar: precisa estar registrado antes do onCreate */
        registerPlugin(AtualizadorPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
