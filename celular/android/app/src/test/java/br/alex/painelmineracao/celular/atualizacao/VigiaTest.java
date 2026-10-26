package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class VigiaTest {
    @Test public void contaSoNaFrente() {
        Vigia v = new Vigia(30_000);
        v.zerar(0, true);
        v.atras(10_000);              /* 10 s na frente */
        v.naFrente(3_610_000);        /* 1 h atrás */
        assertEquals(5_000, v.falta(3_625_000));   /* mais 15 s na frente */
    }

    @Test public void venceEm30s() {
        Vigia v = new Vigia(30_000);
        v.zerar(0, true);
        assertEquals(1, v.falta(29_999));
        assertFalse(v.venceu(29_999));
        assertTrue(v.venceu(30_000));
        assertEquals(0, v.falta(31_000));
    }

    @Test public void zerarRecomeca() {
        Vigia v = new Vigia(30_000);
        v.zerar(0, true);
        assertEquals(10_000, v.falta(20_000));
        v.zerar(20_000, true);
        assertEquals(30_000, v.falta(20_000));
    }

    @Test public void comecaAtrasNaoConta() {
        Vigia v = new Vigia(30_000);
        v.zerar(0, false);
        assertEquals(30_000, v.falta(100_000));
        v.naFrente(100_000);
        assertEquals(20_000, v.falta(110_000));
    }

    @Test public void atrasOuNaFrenteDuasVezesNaoContaEmDobro() {
        Vigia v = new Vigia(30_000);
        v.zerar(0, true);
        v.naFrente(5_000);            /* já estava na frente: continua contando desde 0 */
        v.atras(10_000);
        v.atras(20_000);              /* já estava atrás */
        assertEquals(20_000, v.falta(50_000));
    }
}
