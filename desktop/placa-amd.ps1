<#
  Leitor e gravador dos ajustes das placas de vídeo AMD para o Painel de Mineração.

  Fala com a biblioteca da AMD que vem com o driver (atiadlxx.dll, o ADL), pelo Overdrive8: limite de potência, tensão,
  clock máximo, memória, temporização da memória e ventoinha. Fica rodando escondido e conversa com o programa por linhas
  de JSON: cada pedido é uma linha na entrada, e cada resposta, uma linha na saída, com o mesmo "id" do pedido.
  - {"id":1,"op":"ler"} -> {"id":1,"ok":true,"afterburner":false,"placas":[...]}
  - {"id":2,"op":"aplicar","chave":"...","ajuste":{"potencia":-21,...}} -> {"id":2,"ok":true,"itens":{...},"placa":{...}}
  - {"id":3,"op":"fabrica","chave":"..."}: o aplicar com o padrão de cada ajuste
  Toda gravação leva todos os ajustes e a curva da ventoinha numa chamada só: uma gravação sem a curva devolve a
  ventoinha ao automático (visto na RX 9070 XT do Alex, 28/10/2026).
  Termina quando a entrada fecha ou quando o processo -Pai acaba.

  Uso: placa-amd.ps1 [-Pai <pid>]

  Os nomes das funções, o formato das estruturas e os números dos ajustes vêm do ADL SDK da AMD
  (github.com/GPUOpen-LibrariesAndSDKs/display-library, cabeçalhos com licença MIT, Copyright (c) Advanced Micro Devices, Inc.).
  O código em C# é compatível com o Windows PowerShell 5.1 (C# 5).
#>
param([int]$Pai = 0)
$ErrorActionPreference = "Stop"

$codigo = @'
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

public static class PlacaAmd
{
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    public delegate IntPtr Aloca(int tamanho);

    [DllImport("atiadlxx.dll")] static extern int ADL2_Main_Control_Create(Aloca cb, int conectados, out IntPtr ctx);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Main_Control_Destroy(IntPtr ctx);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Adapter_NumberOfAdapters_Get(IntPtr ctx, out int n);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Adapter_AdapterInfo_Get(IntPtr ctx, IntPtr info, int tamanho);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive_Caps(IntPtr ctx, int indice, out int suporta, out int ligado, out int versao);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_Init_Setting_Get(IntPtr ctx, int indice, IntPtr init);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_Current_Setting_Get(IntPtr ctx, int indice, IntPtr atual);
    /* nas X2, o número de ajustes também entra: com 0, o driver responde -9 */
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_Init_SettingX2_Get(IntPtr ctx, int indice, out int caps, ref int n, out IntPtr lista);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_Current_SettingX2_Get(IntPtr ctx, int indice, ref int n, out IntPtr lista);
    [DllImport("atiadlxx.dll")] static extern int ADL2_New_QueryPMLogData_Get(IntPtr ctx, int indice, IntPtr saida);
    /* a única função que muda a placa */
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_Setting_Set(IntPtr ctx, int indice, IntPtr set, IntPtr atual);

    /* AdapterInfo no Windows: 1572 bytes. ADLPMLogDataOutput: int size + 256 x (supported, value). */
    const int TAM_INFO = 1572, AMD = 1002, AMD_HEX = 0x1002, MAX_SENSORES = 256, TAM_SAIDA = 4 + MAX_SENSORES * 8;
    /* quantos ajustes o ADL SDK 18.1 conhece (OD8_COUNT) e o espaço que o leitor reserva nas estruturas fixas */
    const int OD8_COUNT = 77, FOLGA = 256;
    /* os ajustes (posição na lista do Overdrive8) */
    const int CLK_MAX = 0, MEM_MAX = 8, POTENCIA = 9, TEMPORIZACAO = 14, ZERO_RPM = 15, CURVA = 19, MODO = 36, TENSAO = 37;
    /* as capacidades (bits do overdrive8Capabilities) */
    const int C_CLOCK = 1 << 0, C_CLOCK_PONTOS = 1 << 1, C_MEMORIA = 1 << 2, C_POTENCIA = 1 << 3, C_TEMPORIZACAO = 1 << 8,
              C_ZERO_RPM = 1 << 9, C_CURVA = 1 << 13, C_MODO = 1 << 16, C_TENSAO = 1 << 17;

    /* o que o painel pode gravar: clock, memória, potência, temporização, zero rpm, a curva, o modo (só em 3) e a tensão */
    static readonly int[] PODE_GRAVAR = { CLK_MAX, MEM_MAX, POTENCIA, TEMPORIZACAO, ZERO_RPM, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, MODO, TENSAO };
    static readonly int[] CODIGOS = { 0, -1, -3, -8, -10, -20, -23, -27 };
    static readonly string[] NOMES_CODIGO = { "ok", "erro", "parâmetro inválido", "sem suporte", "placa desligada", "gravação incompleta", "precisa de administrador", "placa em uso" };

    static Aloca aloca = new Aloca(AlocaMemoria);   /* guardado: o ADL chama de volta para pedir memória */
    static IntPtr AlocaMemoria(int tamanho) { return Marshal.AllocHGlobal(tamanho); }
    static IntPtr ctx = IntPtr.Zero;
    static bool usarX2 = false;   /* o driver não tem as funções de estrutura fixa */

    class Placa { public int indice, bus; public string nome, chave; }
    class Od8 { public int caps, n; public int[] min, max, padrao, atual; }

    /* uma chamada do ADL que devia funcionar e não funcionou (o driver reiniciou, foi atualizado...) */
    class FalhaAdl : Exception { public FalhaAdl(string funcao, int r) : base("o ADL respondeu " + r.ToString(CultureInfo.InvariantCulture) + " em " + funcao) { } }
    class SemAdl : Exception { public SemAdl(string msg) : base(msg) { } }
    /* um pedido que não dá para gravar: fora da faixa, ajuste que a placa não tem, pedido estranho */
    class Recusa : Exception { public string erro; public Recusa(string codigo, string msg) : base(msg) { erro = codigo; } }
    static string N(int v) { return v.ToString(CultureInfo.InvariantCulture); }

    /* ---------------- JSON ---------------- */
    class J
    {
        public List<string> k = new List<string>();
        public List<object> v = new List<object>();
        public J Put(string chave, object valor) { k.Add(chave); v.Add(valor); return this; }
    }

    static string Texto(string s)
    {
        StringBuilder b = new StringBuilder("\"");
        foreach (char c in s ?? "")
        {
            if (c == '"' || c == '\\') { b.Append('\\'); b.Append(c); }
            else if (c < 32 || c > 126) b.Append("\\u" + ((int)c).ToString("x4"));
            else b.Append(c);
        }
        return b.Append('"').ToString();
    }

    static void Escreve(StringBuilder b, object o)
    {
        if (o == null) b.Append("null");
        else if (o is string) b.Append(Texto((string)o));
        else if (o is bool) b.Append((bool)o ? "true" : "false");
        else if (o is int) b.Append(((int)o).ToString(CultureInfo.InvariantCulture));
        else if (o is long) b.Append(((long)o).ToString(CultureInfo.InvariantCulture));
        else if (o is double)
        {
            double d = (double)o;
            if (double.IsNaN(d) || double.IsInfinity(d)) b.Append("null");
            else if (d == Math.Floor(d) && Math.Abs(d) < 1e15) b.Append(((long)d).ToString(CultureInfo.InvariantCulture));
            else b.Append(d.ToString("R", CultureInfo.InvariantCulture));
        }
        else if (o is J)
        {
            J j = (J)o;
            b.Append('{');
            for (int i = 0; i < j.k.Count; i++) { if (i > 0) b.Append(','); b.Append(Texto(j.k[i])).Append(':'); Escreve(b, j.v[i]); }
            b.Append('}');
        }
        else if (o is IList)
        {
            IList l = (IList)o;
            b.Append('[');
            for (int i = 0; i < l.Count; i++) { if (i > 0) b.Append(','); Escreve(b, l[i]); }
            b.Append(']');
        }
        else b.Append(Texto(o.ToString()));
    }
    static string Json(object o) { StringBuilder b = new StringBuilder(); Escreve(b, o); return b.ToString(); }

    /* leitor de JSON mínimo: objetos (Dictionary), listas (List), textos, números (double), true, false e null */
    class LeitorJson
    {
        readonly string s;
        int i, fundo;
        LeitorJson(string texto) { s = texto; }
        public static object Ler(string texto)
        {
            LeitorJson l = new LeitorJson(texto ?? "");
            object v = l.Valor();
            l.Espacos();
            if (l.i != l.s.Length) throw new FormatException("texto sobrando depois do JSON");
            return v;
        }
        void Espacos() { while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n')) i++; }
        void Espera(char c) { Espacos(); if (i >= s.Length || s[i] != c) throw new FormatException("esperava " + c); i++; }
        object Valor()
        {
            Espacos();
            if (i >= s.Length) throw new FormatException("o JSON acabou antes da hora");
            char c = s[i];
            if (c == '{' || c == '[')
            {
                if (++fundo > 32) throw new FormatException("JSON fundo demais");
                object o = c == '{' ? (object)Objeto() : Lista();
                fundo--;
                return o;
            }
            if (c == '"') return Txt();
            if (c == 't') { Palavra("true"); return true; }
            if (c == 'f') { Palavra("false"); return false; }
            if (c == 'n') { Palavra("null"); return null; }
            return Numero();
        }
        void Palavra(string p)
        {
            if (i + p.Length > s.Length || string.CompareOrdinal(s, i, p, 0, p.Length) != 0) throw new FormatException("esperava " + p);
            i += p.Length;
        }
        Dictionary<string, object> Objeto()
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            i++;
            Espacos();
            if (i < s.Length && s[i] == '}') { i++; return d; }
            while (true)
            {
                Espacos();
                if (i >= s.Length || s[i] != '"') throw new FormatException("esperava o nome de um campo");
                string chave = Txt();
                Espera(':');
                d[chave] = Valor();
                Espacos();
                if (i < s.Length && s[i] == ',') { i++; continue; }
                Espera('}');
                return d;
            }
        }
        List<object> Lista()
        {
            List<object> l = new List<object>();
            i++;
            Espacos();
            if (i < s.Length && s[i] == ']') { i++; return l; }
            while (true)
            {
                l.Add(Valor());
                Espacos();
                if (i < s.Length && s[i] == ',') { i++; continue; }
                Espera(']');
                return l;
            }
        }
        string Txt()
        {
            StringBuilder b = new StringBuilder();
            i++;
            while (true)
            {
                if (i >= s.Length) throw new FormatException("texto sem fim");
                char c = s[i++];
                if (c == '"') return b.ToString();
                if (c != '\\') { b.Append(c); continue; }
                if (i >= s.Length) throw new FormatException("escape sem fim");
                char e = s[i++];
                if (e == '"' || e == '\\' || e == '/') b.Append(e);
                else if (e == 'b') b.Append('\b');
                else if (e == 'f') b.Append('\f');
                else if (e == 'n') b.Append('\n');
                else if (e == 'r') b.Append('\r');
                else if (e == 't') b.Append('\t');
                else if (e == 'u')
                {
                    if (i + 4 > s.Length) throw new FormatException("\\u sem os 4 dígitos");
                    b.Append((char)int.Parse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                    i += 4;
                }
                else throw new FormatException("escape desconhecido");
            }
        }
        double Numero()
        {
            int ini = i;
            if (i < s.Length && s[i] == '-') i++;
            while (i < s.Length && (char.IsDigit(s[i]) || s[i] == '.' || s[i] == 'e' || s[i] == 'E' || s[i] == '+' || s[i] == '-')) i++;
            double d;
            if (i == ini || !double.TryParse(s.Substring(ini, i - ini), NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                throw new FormatException("número inválido");
            return d;
        }
    }

    /* ---------------- o ADL ---------------- */
    static void Abrir()
    {
        if (ctx != IntPtr.Zero) return;
        int r;
        try { r = ADL2_Main_Control_Create(aloca, 1, out ctx); }
        catch (DllNotFoundException) { throw new SemAdl("o driver da AMD não está instalado (atiadlxx.dll)"); }
        catch (EntryPointNotFoundException) { throw new SemAdl("o ADL deste driver não tem o ADL2_Main_Control_Create"); }
        if (r != 0) { ctx = IntPtr.Zero; throw new SemAdl("o ADL não iniciou (" + r.ToString(CultureInfo.InvariantCulture) + ")"); }
    }

    static void Fechar()
    {
        if (ctx == IntPtr.Zero) return;
        try { ADL2_Main_Control_Destroy(ctx); } catch (Exception) { }
        ctx = IntPtr.Zero;
    }

    /* as placas AMD, uma por barramento PCI (o ADL dá uma entrada por saída de vídeo) */
    static List<Placa> Placas()
    {
        List<Placa> placas = new List<Placa>();
        int n;
        int r = ADL2_Adapter_NumberOfAdapters_Get(ctx, out n);
        if (r != 0) throw new FalhaAdl("ADL2_Adapter_NumberOfAdapters_Get", r);
        if (n <= 0 || n > 512) return placas;
        IntPtr info = Marshal.AllocHGlobal(TAM_INFO * n);
        try
        {
            for (int i = 0; i < TAM_INFO * n; i++) Marshal.WriteByte(info, i, 0);
            r = ADL2_Adapter_AdapterInfo_Get(ctx, info, TAM_INFO * n);
            if (r != 0) throw new FalhaAdl("ADL2_Adapter_AdapterInfo_Get", r);
            List<int> vistos = new List<int>();
            for (int i = 0; i < n; i++)
            {
                IntPtr p = new IntPtr(info.ToInt64() + (long)TAM_INFO * i);
                int indice = Marshal.ReadInt32(p, 4), bus = Marshal.ReadInt32(p, 264), vendor = Marshal.ReadInt32(p, 276);
                if ((vendor != AMD && vendor != AMD_HEX) || bus < 0 || vistos.Contains(bus)) continue;
                vistos.Add(bus);
                Placa pl = new Placa();
                pl.indice = indice; pl.bus = bus;
                pl.nome = (Marshal.PtrToStringAnsi(new IntPtr(p.ToInt64() + 280)) ?? "").Trim();
                string pnp = (Marshal.PtrToStringAnsi(new IntPtr(p.ToInt64() + 1312)) ?? "").Trim();
                pl.chave = pnp.Length > 0 ? pnp : "bus:" + bus.ToString(CultureInfo.InvariantCulture);
                placas.Add(pl);
            }
        }
        finally { Marshal.FreeHGlobal(info); }
        return placas;
    }

    static IntPtr Zerada(int tam)
    {
        IntPtr p = Marshal.AllocHGlobal(tam);
        for (int i = 0; i < tam; i++) Marshal.WriteByte(p, i, 0);
        return p;
    }
    static void Libera(IntPtr p) { if (p != IntPtr.Zero) Marshal.FreeHGlobal(p); }

    /* o Overdrive8 de uma placa: as faixas, os padrões e os valores de agora */
    static Od8 LerOd8(Placa pl)
    {
        if (!usarX2)
        {
            try { return LerOd8Antigo(pl); }
            catch (EntryPointNotFoundException) { usarX2 = true; }
        }
        return LerOd8X2(pl);
    }

    static Od8 Novo(int caps, int n)
    {
        Od8 o = new Od8();
        o.caps = caps; o.n = n;
        o.min = new int[n]; o.max = new int[n]; o.padrao = new int[n]; o.atual = new int[n];
        return o;
    }

    static Od8 LerOd8Antigo(Placa pl)
    {
        IntPtr init = Zerada(8 + FOLGA * 16), atual = Zerada(4 + FOLGA * 4);
        try
        {
            Marshal.WriteInt32(init, 0, OD8_COUNT);
            int r = ADL2_Overdrive8_Init_Setting_Get(ctx, pl.indice, init);
            if (r != 0) throw new FalhaAdl("ADL2_Overdrive8_Init_Setting_Get", r);
            Marshal.WriteInt32(atual, 0, OD8_COUNT);
            r = ADL2_Overdrive8_Current_Setting_Get(ctx, pl.indice, atual);
            if (r != 0) throw new FalhaAdl("ADL2_Overdrive8_Current_Setting_Get", r);
            int n = Math.Min(Marshal.ReadInt32(init, 0), Marshal.ReadInt32(atual, 0));
            if (n <= 0) throw new FalhaAdl("ADL2_Overdrive8_Init_Setting_Get (nenhum ajuste)", n);
            n = Math.Min(n, FOLGA);
            Od8 o = Novo(Marshal.ReadInt32(init, 4), n);
            for (int i = 0; i < n; i++)
            {
                o.min[i] = Marshal.ReadInt32(init, 8 + i * 16 + 4);
                o.max[i] = Marshal.ReadInt32(init, 8 + i * 16 + 8);
                o.padrao[i] = Marshal.ReadInt32(init, 8 + i * 16 + 12);
                o.atual[i] = Marshal.ReadInt32(atual, 4 + i * 4);
            }
            return o;
        }
        finally { Marshal.FreeHGlobal(init); Marshal.FreeHGlobal(atual); }
    }

    static Od8 LerOd8X2(Placa pl)
    {
        IntPtr lista = IntPtr.Zero, valores = IntPtr.Zero;
        try
        {
            int caps, n = OD8_COUNT, nAtual = OD8_COUNT;
            int r = ADL2_Overdrive8_Init_SettingX2_Get(ctx, pl.indice, out caps, ref n, out lista);
            if (r != 0 || lista == IntPtr.Zero) throw new FalhaAdl("ADL2_Overdrive8_Init_SettingX2_Get", r);
            r = ADL2_Overdrive8_Current_SettingX2_Get(ctx, pl.indice, ref nAtual, out valores);
            if (r != 0 || valores == IntPtr.Zero) throw new FalhaAdl("ADL2_Overdrive8_Current_SettingX2_Get", r);
            int m = Math.Min(Math.Min(n, nAtual), FOLGA);
            if (m <= 0) throw new FalhaAdl("ADL2_Overdrive8_Init_SettingX2_Get (nenhum ajuste)", m);
            Od8 o = Novo(caps, m);
            for (int i = 0; i < m; i++)
            {
                o.min[i] = Marshal.ReadInt32(lista, i * 16 + 4);
                o.max[i] = Marshal.ReadInt32(lista, i * 16 + 8);
                o.padrao[i] = Marshal.ReadInt32(lista, i * 16 + 12);
                o.atual[i] = Marshal.ReadInt32(valores, i * 4);
            }
            return o;
        }
        finally { Libera(lista); Libera(valores); }
    }

    /* os sensores de agora (o mesmo PMLog do sensores-amd.ps1); sem eles, a placa vem sem o "agora" */
    static readonly int[] SENSORES = { 1, 2, 21, 73, 8, 27, 9, 14, 15, 19 };
    static readonly string[] NOMES_SENSORES = { "clockMHz", "memoriaMHz", "tensaoMv", "watts", "tempC", "quenteC", "memoriaC", "ventoinhaRpm", "ventoinhaPct", "usoPct" };
    static J Agora(Placa pl)
    {
        J a = new J();
        IntPtr saida = Zerada(TAM_SAIDA);
        try
        {
            if (ADL2_New_QueryPMLogData_Get(ctx, pl.indice, saida) != 0) return a;
            for (int k = 0; k < SENSORES.Length; k++)
                if (Marshal.ReadInt32(saida, 4 + SENSORES[k] * 8) != 0) a.Put(NOMES_SENSORES[k], Marshal.ReadInt32(saida, 8 + SENSORES[k] * 8));
        }
        catch (EntryPointNotFoundException) { }
        finally { Marshal.FreeHGlobal(saida); }
        return a;
    }

    /* ---------------- a placa em JSON ---------------- */
    static bool Tem(Od8 o, int cap, int i) { return (o.caps & cap) != 0 && i < o.n; }
    static bool TemClock(Od8 o) { return Tem(o, C_CLOCK, CLK_MAX) && (o.caps & C_CLOCK_PONTOS) == 0; }
    static bool TemCurva(Od8 o) { return Tem(o, C_CURVA, CURVA + 9); }

    static J Numero(Od8 o, bool tem, int i, bool comOffset)
    {
        if (!tem) return new J().Put("suporta", false);
        J j = new J().Put("suporta", true).Put("min", o.min[i]).Put("max", o.max[i]).Put("passo", 1).Put("atual", o.atual[i]).Put("padrao", o.padrao[i]);
        if (comOffset) j.Put("offset", o.min[i] < 0);
        return j;
    }

    static List<object> Par(int c, int p) { List<object> l = new List<object>(); l.Add(c); l.Add(p); return l; }

    static J Ventoinha(Od8 o)
    {
        if (!TemCurva(o)) return new J().Put("suporta", false);
        List<object> curva = new List<object>(), padrao = new List<object>();
        for (int p = 0; p < 5; p++)
        {
            curva.Add(Par(o.atual[CURVA + 2 * p], o.atual[CURVA + 2 * p + 1]));
            padrao.Add(Par(o.padrao[CURVA + 2 * p], o.padrao[CURVA + 2 * p + 1]));
        }
        J zero = Tem(o, C_ZERO_RPM, ZERO_RPM)
            ? new J().Put("suporta", true).Put("atual", o.atual[ZERO_RPM]).Put("padrao", o.padrao[ZERO_RPM])
            : new J().Put("suporta", false);
        return new J().Put("suporta", true).Put("velMin", o.min[CURVA + 1]).Put("velMax", o.max[CURVA + 1])
            .Put("tempMin", o.min[CURVA]).Put("tempMax", o.max[CURVA]).Put("curva", curva).Put("curvaPadrao", padrao).Put("zeroRpm", zero);
    }

    static J Temporizacao(Od8 o)
    {
        if (!Tem(o, C_TEMPORIZACAO, TEMPORIZACAO)) return new J().Put("suporta", false);
        List<object> op = new List<object>();
        for (int v = o.min[TEMPORIZACAO]; v <= o.max[TEMPORIZACAO] && op.Count < 16; v++) op.Add(v);
        return new J().Put("suporta", true).Put("atual", o.atual[TEMPORIZACAO]).Put("padrao", o.padrao[TEMPORIZACAO]).Put("opcoes", op);
    }

    /* os ajustes que o painel cuida, e que esta placa tem */
    static List<int> Cuidados(Od8 o)
    {
        List<int> l = new List<int>();
        if (Tem(o, C_POTENCIA, POTENCIA)) l.Add(POTENCIA);
        if (Tem(o, C_TENSAO, TENSAO)) l.Add(TENSAO);
        if (TemClock(o)) l.Add(CLK_MAX);
        if (Tem(o, C_MEMORIA, MEM_MAX)) l.Add(MEM_MAX);
        if (Tem(o, C_TEMPORIZACAO, TEMPORIZACAO)) l.Add(TEMPORIZACAO);
        if (TemCurva(o)) for (int i = CURVA; i < CURVA + 10; i++) l.Add(i);
        if (TemCurva(o) && Tem(o, C_ZERO_RPM, ZERO_RPM)) l.Add(ZERO_RPM);
        return l;
    }

    static bool DeFabrica(Od8 o)
    {
        foreach (int i in Cuidados(o)) if (o.atual[i] != o.padrao[i]) return false;
        return true;
    }

    static J PlacaJson(Placa pl, Od8 o)
    {
        return new J().Put("chave", pl.chave).Put("nome", pl.nome).Put("bus", pl.bus).Put("indice", pl.indice)
            .Put("deFabrica", DeFabrica(o)).Put("modo", Tem(o, C_MODO, MODO) ? (object)o.atual[MODO] : null)
            .Put("potencia", Numero(o, Tem(o, C_POTENCIA, POTENCIA), POTENCIA, false))
            .Put("tensao", Numero(o, Tem(o, C_TENSAO, TENSAO), TENSAO, true))
            .Put("clock", Numero(o, TemClock(o), CLK_MAX, true))
            .Put("memoria", Numero(o, Tem(o, C_MEMORIA, MEM_MAX), MEM_MAX, false))
            .Put("temporizacao", Temporizacao(o))
            .Put("ventoinha", Ventoinha(o))
            .Put("agora", Agora(pl));
    }

    /* ---------------- gravar ---------------- */
    /* grava numa chamada do Setting_Set: só os ajustes da lista, sem reset, e o modo só em 3 */
    static int Gravar(Placa pl, int n, Dictionary<int, int> valores)
    {
        foreach (KeyValuePair<int, int> kv in valores)
        {
            if (Array.IndexOf(PODE_GRAVAR, kv.Key) < 0) throw new InvalidOperationException("ajuste fora da lista: " + N(kv.Key));
            if (kv.Key == MODO && kv.Value != 3) throw new InvalidOperationException("o modo de energia só pode ir para 3");
            if (kv.Key >= n) throw new InvalidOperationException("ajuste que o driver não tem: " + N(kv.Key));
        }
        IntPtr set = Zerada(4 + FOLGA * 12), atual = Zerada(4 + FOLGA * 4);
        try
        {
            Marshal.WriteInt32(set, 0, n);
            Marshal.WriteInt32(atual, 0, n);
            foreach (KeyValuePair<int, int> kv in valores)
            {
                Marshal.WriteInt32(set, 4 + kv.Key * 12, kv.Value);
                Marshal.WriteInt32(set, 4 + kv.Key * 12 + 4, 1);   /* requested; o reset fica 0 */
            }
            return ADL2_Overdrive8_Setting_Set(ctx, pl.indice, set, atual);
        }
        finally { Marshal.FreeHGlobal(set); Marshal.FreeHGlobal(atual); }
    }

    static int Inteiro(object v, string nome)
    {
        if (!(v is double)) throw new Recusa("pedido", "valor que não é número em " + nome);
        double d = (double)v;
        if (d != Math.Floor(d) || Math.Abs(d) > 1e6) throw new Recusa("pedido", "valor que não é inteiro em " + nome);
        return (int)d;
    }
    static void NaFaixa(Od8 o, int i, int v, string nome)
    {
        if (v < o.min[i] || v > o.max[i]) throw new Recusa("fora-da-faixa", nome + " " + N(v) + " fora da faixa (de " + N(o.min[i]) + " a " + N(o.max[i]) + ")");
    }
    static void PorNumero(Od8 o, Dictionary<int, int> alvo, bool tem, int i, object v, string nome)
    {
        if (!tem) throw new Recusa("sem-ajuste", "a placa não tem " + nome);
        int x = Inteiro(v, nome);
        NaFaixa(o, i, x, nome);
        alvo[i] = x;
    }

    static void VentoinhaAlvo(Od8 o, Dictionary<int, int> alvo, Dictionary<string, object> v)
    {
        if (!TemCurva(o)) throw new Recusa("sem-ajuste", "a placa não tem a curva da ventoinha");
        if (v == null || !v.ContainsKey("modo") || !(v["modo"] is string)) throw new Recusa("pedido", "a ventoinha sem o modo");
        string modo = (string)v["modo"];
        bool zero = Tem(o, C_ZERO_RPM, ZERO_RPM);
        if (modo == "auto")
        {
            for (int i = CURVA; i < CURVA + 10; i++) alvo[i] = o.padrao[i];
            if (zero) alvo[ZERO_RPM] = o.padrao[ZERO_RPM];
        }
        else if (modo == "fixa")
        {
            if (!v.ContainsKey("pct")) throw new Recusa("pedido", "a ventoinha fixa sem o pct");
            int pct = Inteiro(v["pct"], "ventoinha");
            for (int p = 0; p < 5; p++) { NaFaixa(o, CURVA + 2 * p + 1, pct, "ventoinha"); alvo[CURVA + 2 * p + 1] = pct; }
            if (zero) alvo[ZERO_RPM] = 0;
        }
        else if (modo == "curva")
        {
            List<object> c = v.ContainsKey("curva") ? v["curva"] as List<object> : null;
            if (c == null || c.Count != 5) throw new Recusa("pedido", "a curva da ventoinha precisa de 5 pontos");
            for (int p = 0; p < 5; p++)
            {
                List<object> par = c[p] as List<object>;
                if (par == null || par.Count != 2) throw new Recusa("pedido", "cada ponto da curva é [°C, %]");
                int t = Inteiro(par[0], "temperatura da curva"), s = Inteiro(par[1], "ventoinha");
                NaFaixa(o, CURVA + 2 * p, t, "temperatura da curva");
                NaFaixa(o, CURVA + 2 * p + 1, s, "ventoinha");
                alvo[CURVA + 2 * p] = t;
                alvo[CURVA + 2 * p + 1] = s;
            }
            if (zero && v.ContainsKey("zeroRpm"))
            {
                int z = Inteiro(v["zeroRpm"], "zero rpm");
                NaFaixa(o, ZERO_RPM, z, "zero rpm");
                alvo[ZERO_RPM] = z;
            }
        }
        else throw new Recusa("pedido", "modo da ventoinha desconhecido: " + modo);
    }

    /* o ajuste completo: o que veio no pedido e, no resto, o valor de agora */
    static void Completar(Od8 o, Dictionary<string, object> ajuste, Dictionary<int, int> alvo)
    {
        foreach (KeyValuePair<string, object> kv in ajuste)
        {
            if (kv.Key == "potencia") PorNumero(o, alvo, Tem(o, C_POTENCIA, POTENCIA), POTENCIA, kv.Value, "potência");
            else if (kv.Key == "tensao") PorNumero(o, alvo, Tem(o, C_TENSAO, TENSAO), TENSAO, kv.Value, "tensão");
            else if (kv.Key == "clock") PorNumero(o, alvo, TemClock(o), CLK_MAX, kv.Value, "clock máximo");
            else if (kv.Key == "memoria") PorNumero(o, alvo, Tem(o, C_MEMORIA, MEM_MAX), MEM_MAX, kv.Value, "memória");
            else if (kv.Key == "temporizacao") PorNumero(o, alvo, Tem(o, C_TEMPORIZACAO, TEMPORIZACAO), TEMPORIZACAO, kv.Value, "temporização");
            else if (kv.Key == "ventoinha") VentoinhaAlvo(o, alvo, kv.Value as Dictionary<string, object>);
            else throw new Recusa("pedido", "campo desconhecido: " + kv.Key);
        }
        if (TemCurva(o))
            for (int p = 1; p < 5; p++)
                if (alvo[CURVA + 2 * p] <= alvo[CURVA + 2 * (p - 1)])
                    throw new Recusa("fora-da-faixa", "as temperaturas da curva da ventoinha têm de subir de um ponto para o outro");
    }

    /* o pedido e o lido de cada ajuste */
    static J Itens(Dictionary<int, int> alvo, Od8 depois)
    {
        J j = new J();
        string[] nomes = { "potencia", "tensao", "clock", "memoria", "temporizacao" };
        int[] ids = { POTENCIA, TENSAO, CLK_MAX, MEM_MAX, TEMPORIZACAO };
        for (int k = 0; k < ids.Length; k++)
            if (alvo.ContainsKey(ids[k]))
                j.Put(nomes[k], new J().Put("pedido", alvo[ids[k]]).Put("lido", ids[k] < depois.n ? (object)depois.atual[ids[k]] : null));
        if (alvo.ContainsKey(CURVA))
        {
            List<object> pedido = new List<object>(), lido = new List<object>();
            for (int p = 0; p < 5; p++)
            {
                pedido.Add(Par(alvo[CURVA + 2 * p], alvo[CURVA + 2 * p + 1]));
                if (TemCurva(depois)) lido.Add(Par(depois.atual[CURVA + 2 * p], depois.atual[CURVA + 2 * p + 1]));
            }
            j.Put("curva", new J().Put("pedido", pedido).Put("lido", lido));
        }
        if (alvo.ContainsKey(ZERO_RPM)) j.Put("zeroRpm", new J().Put("pedido", alvo[ZERO_RPM]).Put("lido", ZERO_RPM < depois.n ? (object)depois.atual[ZERO_RPM] : null));
        return j;
    }

    static string Recusou(object id, int r)
    {
        int k = Array.IndexOf(CODIGOS, r);
        return Erro(id, "recusou", "o driver recusou a gravação (" + N(r) + ": " + (k >= 0 ? NOMES_CODIGO[k] : "código") + ")");
    }

    /* aplicar: completa o ajuste com os valores de agora, confere, grava o modo (se não for o manual), grava tudo numa
       chamada só e lê de novo. fabrica: o mesmo, com o padrão de cada ajuste. */
    static string Aplicar(object id, Dictionary<string, object> d, bool fabrica)
    {
        string chave = d.ContainsKey("chave") ? d["chave"] as string : null;
        Dictionary<string, object> ajuste = null;
        if (!fabrica)
        {
            ajuste = d.ContainsKey("ajuste") ? d["ajuste"] as Dictionary<string, object> : null;
            if (ajuste == null) return Erro(id, "pedido", "o pedido não traz o ajuste");
        }
        if (string.IsNullOrEmpty(chave)) return Erro(id, "pedido", "o pedido não traz a chave da placa");
        return ComAdl(id, delegate
        {
            Placa pl = null;
            foreach (Placa x in Placas()) if (x.chave == chave) { pl = x; break; }
            if (pl == null) return Erro(id, "sem-placa", "a placa " + chave + " não foi encontrada");
            int sup, lig, ver;
            int r = ADL2_Overdrive_Caps(ctx, pl.indice, out sup, out lig, out ver);
            if (r != 0) throw new FalhaAdl("ADL2_Overdrive_Caps", r);
            if (ver != 8) return Erro(id, "sem-placa", "a placa " + chave + " não tem o Overdrive8");
            Od8 o = LerOd8(pl);
            Dictionary<int, int> alvo = new Dictionary<int, int>();
            foreach (int i in Cuidados(o)) alvo[i] = fabrica ? o.padrao[i] : o.atual[i];
            try { if (!fabrica) Completar(o, ajuste, alvo); }
            catch (Recusa e) { return Erro(id, e.erro, e.Message); }
            if (Tem(o, C_MODO, MODO) && o.atual[MODO] != 3)
            {
                Dictionary<int, int> modo = new Dictionary<int, int>();
                modo[MODO] = 3;
                r = Gravar(pl, o.n, modo);
                if (r != 0) return Recusou(id, r);
            }
            r = Gravar(pl, o.n, alvo);
            if (r != 0) return Recusou(id, r);
            Od8 depois = LerOd8(pl);
            return Json(new J().Put("id", id).Put("ok", true).Put("itens", Itens(alvo, depois)).Put("placa", PlacaJson(pl, depois)));
        });
    }

    /* ---------------- os pedidos ---------------- */
    static string Erro(object id, string erro, string msg)
    {
        return Json(new J().Put("id", id).Put("ok", false).Put("erro", erro).Put("msg", msg));
    }

    static bool Afterburner()
    {
        try { return Process.GetProcessesByName("MSIAfterburner").Length > 0; }
        catch (Exception) { return false; }
    }

    /* todas as placas AMD com Overdrive8 */
    static List<object> LerPlacas(bool[] algumaAmd)
    {
        List<object> lista = new List<object>();
        List<Placa> placas = Placas();
        algumaAmd[0] = placas.Count > 0;
        foreach (Placa pl in placas)
        {
            int sup, lig, ver;
            int r = ADL2_Overdrive_Caps(ctx, pl.indice, out sup, out lig, out ver);
            if (r != 0) throw new FalhaAdl("ADL2_Overdrive_Caps", r);
            if (ver != 8) continue;
            lista.Add(PlacaJson(pl, LerOd8(pl)));
        }
        return lista;
    }

    /* roda uma leitura; se o ADL falhar no meio (o driver reiniciou), abre o ADL de novo e tenta mais uma vez */
    delegate string Acao();
    static string ComAdl(object id, Acao acao)
    {
        try
        {
            Abrir();
            try { return acao(); }
            catch (FalhaAdl) { Fechar(); Abrir(); return acao(); }
        }
        catch (SemAdl e) { return Erro(id, "sem-adl", e.Message); }
        catch (FalhaAdl e) { return Erro(id, "falhou", e.Message); }
        catch (EntryPointNotFoundException e) { return Erro(id, "sem-adl", "o ADL deste driver não tem " + e.Message); }
    }

    static string Ler(object id)
    {
        return ComAdl(id, delegate
        {
            bool[] algumaAmd = new bool[1];
            List<object> placas = LerPlacas(algumaAmd);
            if (!algumaAmd[0]) return Erro(id, "sem-amd", "nenhuma placa AMD");
            return Json(new J().Put("id", id).Put("ok", true).Put("afterburner", Afterburner()).Put("placas", placas));
        });
    }

    public static string Responder(string linha)
    {
        Dictionary<string, object> d;
        try { d = LeitorJson.Ler(linha) as Dictionary<string, object>; }
        catch (Exception) { return Erro(null, "pedido", "o pedido não é JSON"); }
        if (d == null) return Erro(null, "pedido", "o pedido não é um objeto JSON");
        object id = d.ContainsKey("id") ? d["id"] : null;
        string op = d.ContainsKey("op") ? d["op"] as string : null;
        try
        {
            if (op == "ler") return Ler(id);
            if (op == "aplicar") return Aplicar(id, d, false);
            if (op == "fabrica") return Aplicar(id, d, true);
            return Erro(id, "pedido", "pedido desconhecido: " + (op ?? "(sem op)"));
        }
        catch (Exception e) { return Erro(id, "falhou", e.GetType().Name + ": " + e.Message); }
    }

    /* a vigia do processo pai: quando ele acaba, este também */
    static void VigiaPai(object o)
    {
        int pai = (int)o;
        while (true)
        {
            bool vivo;
            try { vivo = !Process.GetProcessById(pai).HasExited; }
            catch (Exception) { vivo = false; }
            if (!vivo) Environment.Exit(0);
            Thread.Sleep(5000);
        }
    }

    public static void Rodar(TextReader entrada, TextWriter saida, int pai)
    {
        if (pai > 0)
        {
            Thread t = new Thread(new ParameterizedThreadStart(VigiaPai));
            t.IsBackground = true;
            t.Start(pai);
        }
        try
        {
            string linha;
            while ((linha = entrada.ReadLine()) != null)
            {
                if (linha.Trim().Length == 0) continue;
                string r = Responder(linha);
                saida.WriteLine(r);
                saida.Flush();
            }
        }
        finally { Fechar(); }
    }
}
'@

function Json([string]$s) {
    $b = New-Object System.Text.StringBuilder
    foreach ($c in $s.ToCharArray()) {
        $n = [int]$c
        if ($c -eq '"' -or $c -eq '\') { [void]$b.Append('\').Append($c) }
        elseif ($n -lt 32 -or $n -gt 126) { [void]$b.Append('\u' + $n.ToString('x4')) }
        else { [void]$b.Append($c) }
    }
    '"' + $b.ToString() + '"'
}

try { Add-Type -TypeDefinition $codigo -Language CSharp -IgnoreWarnings }
catch { [Console]::Out.WriteLine('{"id":null,"ok":false,"erro":"falhou","msg":' + (Json ("o leitor nao compilou: " + $_.Exception.Message)) + '}'); exit 2 }

[PlacaAmd]::Rodar([Console]::In, [Console]::Out, $Pai)
