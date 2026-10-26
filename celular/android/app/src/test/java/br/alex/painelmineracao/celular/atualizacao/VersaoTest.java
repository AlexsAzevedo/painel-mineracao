package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class VersaoTest {
    @Test public void compara() {
        assertTrue(Versao.comparar("1.10.0", "1.9.9") > 0);
        assertTrue(Versao.comparar("1.8.0", "1.8.1") < 0);
        assertTrue(Versao.comparar("2.0.0", "1.99.99") > 0);
    }

    @Test public void igual() { assertEquals(0, Versao.comparar("1.8.0", "1.8.0")); }

    @Test(expected = IllegalArgumentException.class)
    public void invalidaLanca() { Versao.comparar("1.8", "1.8.0"); }

    @Test public void valida() {
        assertTrue(Versao.valida("1.8.0"));
        assertFalse(Versao.valida("1.8"));
        assertFalse(Versao.valida("1.8.0-beta"));
        assertFalse(Versao.valida(null));
        assertFalse(Versao.valida("1.100.0"));
    }

    @Test public void codigo() {
        assertEquals(10800, Versao.codigo("1.8.0"));
        assertEquals(20012, Versao.codigo("2.0.12"));
    }
}
