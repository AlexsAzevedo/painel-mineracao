package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class InstalacaoTest {
    @Test public void pendenteConfirma() { assertEquals(Instalacao.Acao.CONFIRMAR, Instalacao.decidir(-1)); }

    @Test public void sucessoNadaFaz() { assertEquals(Instalacao.Acao.NADA, Instalacao.decidir(0)); }

    @Test public void falhaFalha() {
        for (int s = 1; s <= 8; s++) assertEquals("status " + s, Instalacao.Acao.FALHOU, Instalacao.decidir(s));
    }

    @Test public void motivos() {
        assertEquals("a atualização foi cancelada", Instalacao.motivo(3, null));
        assertEquals("o app instalado foi assinado com outra chave: baixe pelo navegador", Instalacao.motivo(7, "INSTALL_FAILED_UPDATE_INCOMPATIBLE"));
        assertEquals("falta espaço no celular", Instalacao.motivo(6, null));
        assertEquals("o Android bloqueou a instalação", Instalacao.motivo(2, null));
        assertEquals("o arquivo do app veio com defeito", Instalacao.motivo(4, null));
        assertEquals("outra instalação está em andamento", Instalacao.motivo(5, null));
        assertEquals("o Android não instalou (INSTALL_FAILED_INTERNAL_ERROR)", Instalacao.motivo(1, "INSTALL_FAILED_INTERNAL_ERROR"));
        assertEquals("o Android não instalou", Instalacao.motivo(1, null));
    }

    @Test public void semPerguntarSoNo12() {
        assertFalse(Instalacao.semPerguntar(30));
        assertTrue(Instalacao.semPerguntar(31));
        assertTrue(Instalacao.semPerguntar(36));
    }
}
