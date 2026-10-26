<#
  Sensores das placas de vídeo AMD para o Painel de Mineração.

  Lê pela biblioteca da própria AMD que vem com o driver (atiadlxx.dll, o ADL): a temperatura da borda, da memória e do
  ponto mais quente, o consumo da placa, a ventoinha, o uso e os clocks. Só lê: não muda nada na placa.

  Uso: sensores-amd.ps1 [-Intervalo 30] [-Vezes 0] [-Pai <pid>] [-Diagnostico]
  - Cada leitura sai numa linha de JSON. -Vezes 0: lê até o processo -Pai acabar (ou para sempre, sem -Pai).
  - -Diagnostico: antes, uma linha com tudo o que o ADL respondeu, pelos dois jeitos de ler (para acertar o painel com
    uma placa de verdade).

  Os números dos sensores (ADLSensorType) e o formato das estruturas vêm do ADL SDK da AMD
  (github.com/GPUOpen-LibrariesAndSDKs/display-library, licença MIT, Copyright (c) Advanced Micro Devices, Inc.).
  O código em C# é compatível com o Windows PowerShell 5.1 (C# 5).
#>
param([int]$Intervalo = 30, [int]$Vezes = 0, [int]$Pai = 0, [switch]$Diagnostico)
$ErrorActionPreference = "Stop"

$codigo = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

public static class SensoresAmd
{
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    public delegate IntPtr Aloca(int tamanho);

    [DllImport("atiadlxx.dll")] static extern int ADL2_Main_Control_Create(Aloca cb, int conectados, out IntPtr ctx);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Main_Control_Destroy(IntPtr ctx);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Adapter_NumberOfAdapters_Get(IntPtr ctx, out int n);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Adapter_AdapterInfo_Get(IntPtr ctx, IntPtr info, int tamanho);
    [DllImport("atiadlxx.dll")] static extern int ADL2_New_QueryPMLogData_Get(IntPtr ctx, int indice, IntPtr saida);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_PMLog_ShareMemory_Support(IntPtr ctx, int indice, out int suporta, int opcao);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Device_PMLog_Device_Create(IntPtr ctx, int indice, out uint disp);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_PMLogSenorType_Support_Get(IntPtr ctx, int indice, out int n, out IntPtr lista);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_PMLog_ShareMemory_Start(IntPtr ctx, int indice, int taxa, int nLista, IntPtr lista, ref uint disp, out IntPtr memoria, int opcao);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_PMLog_ShareMemory_Read(IntPtr ctx, int indice, int n, IntPtr lista, ref IntPtr memoria, IntPtr saida);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Overdrive8_PMLog_ShareMemory_Stop(IntPtr ctx, int indice, ref uint disp);
    [DllImport("atiadlxx.dll")] static extern int ADL2_Device_PMLog_Device_Destroy(IntPtr ctx, uint disp);

    /* AdapterInfo no Windows: 9 ints e 6 textos de 256 bytes; ADLPMLogDataOutput: int size + 256 x (supported, value) */
    /* AMD: o ADL dá o código do fabricante com os dígitos de 0x1002 lidos como decimal (1002; a Intel aparece como 8086) */
    const int TAM_INFO = 1572, MAX_SENSORES = 256, TAM_SAIDA = 4 + MAX_SENSORES * 8, AMD = 1002, AMD_HEX = 0x1002;
    /* ADLSensorType */
    const int CLK_GFX = 1, CLK_MEM = 2, T_BORDA = 8, T_MEMORIA = 9, FAN_RPM = 14, FAN_PCT = 15, USO_GFX = 19,
              V_GFX = 21, P_CHIP = 23, T_QUENTE = 27, P_PLACA = 73;

    static Aloca aloca = new Aloca(AlocaMemoria);   /* guardado: o ADL chama de volta para pedir memória */
    static IntPtr AlocaMemoria(int tamanho) { return Marshal.AllocHGlobal(tamanho); }

    class Placa
    {
        public int indice, bus;
        public string nome;
        public string metodo;          /* "pmlog" (New_QueryPMLogData_Get) ou "compartilhada" */
        public uint disp;
        public IntPtr memoria = IntPtr.Zero, lista = IntPtr.Zero;
        public int nLista;
        public bool iniciada;
    }

    static IntPtr ctx = IntPtr.Zero;
    static List<Placa> placas = null;
    static string erroInicio = null;

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
    static string Erro(string tipo, string msg) { return "{\"ok\":false,\"erro\":" + Texto(tipo) + ",\"msg\":" + Texto(msg) + "}"; }
    static string N(int v) { return v.ToString(CultureInfo.InvariantCulture); }

    /* liga o ADL e acha as placas AMD (uma por barramento PCI) */
    static string Iniciar(StringBuilder diag)
    {
        if (placas != null) return null;
        if (erroInicio != null) return erroInicio;
        try
        {
            int r = ADL2_Main_Control_Create(aloca, 1, out ctx);
            if (diag != null) diag.Append("\"criar\":" + N(r) + ",");
            if (r != 0) return erroInicio = Erro("sem-adl", "o ADL não iniciou (" + N(r) + ")");
            int n;
            r = ADL2_Adapter_NumberOfAdapters_Get(ctx, out n);
            if (r != 0 || n <= 0) return erroInicio = Erro("sem-amd", "nenhuma placa AMD (" + N(r) + ", " + N(n) + ")");
            IntPtr info = Marshal.AllocHGlobal(TAM_INFO * n);
            try
            {
                for (int i = 0; i < TAM_INFO * n; i++) Marshal.WriteByte(info, i, 0);
                r = ADL2_Adapter_AdapterInfo_Get(ctx, info, TAM_INFO * n);
                if (r != 0) return erroInicio = Erro("sem-amd", "o ADL não listou as placas (" + N(r) + ")");
                placas = new List<Placa>();
                List<int> vistos = new List<int>();   /* List e não HashSet: o HashSet fica no System.Core, que o Add-Type do PowerShell 5.1 pode não carregar */
                List<string> lidos = new List<string>();
                for (int i = 0; i < n; i++)
                {
                    IntPtr p = new IntPtr(info.ToInt64() + (long)TAM_INFO * i);
                    int indice = Marshal.ReadInt32(p, 4), bus = Marshal.ReadInt32(p, 264), vendor = Marshal.ReadInt32(p, 276);
                    int presente = Marshal.ReadInt32(p, 792), existe = Marshal.ReadInt32(p, 796);
                    string nome = (Marshal.PtrToStringAnsi(new IntPtr(p.ToInt64() + 280)) ?? "").Trim();
                    lidos.Add("{\"i\":" + N(indice) + ",\"bus\":" + N(bus) + ",\"vendor\":" + N(vendor) + ",\"nome\":" + Texto(nome)
                        + ",\"presente\":" + N(presente) + ",\"existe\":" + N(existe) + "}");
                    if ((vendor != AMD && vendor != AMD_HEX) || vistos.Contains(bus)) continue;
                    vistos.Add(bus);
                    Placa pl = new Placa();
                    pl.indice = indice; pl.bus = bus; pl.nome = nome;
                    placas.Add(pl);
                }
                if (diag != null) diag.Append("\"adaptadores\":[" + string.Join(",", lidos.ToArray()) + "],");
            }
            finally { Marshal.FreeHGlobal(info); }
            if (placas.Count == 0) { placas = null; return erroInicio = Erro("sem-amd", "nenhuma placa AMD"); }
            return null;
        }
        catch (DllNotFoundException) { return erroInicio = Erro("sem-adl", "o driver da AMD não está instalado (atiadlxx.dll)"); }
        catch (EntryPointNotFoundException e) { return erroInicio = Erro("sem-adl", "o ADL deste driver não tem " + e.Message); }
        catch (Exception e) { return erroInicio = Erro("falhou", e.GetType().Name + ": " + e.Message); }
    }

    /* os sensores que o ADL marcou como lidos: índice -> valor */
    static Dictionary<int, int> Sensores(IntPtr saida)
    {
        Dictionary<int, int> s = new Dictionary<int, int>();
        for (int i = 0; i < MAX_SENSORES; i++)
        {
            int sup = Marshal.ReadInt32(saida, 4 + i * 8);
            if (sup != 0) s[i] = Marshal.ReadInt32(saida, 8 + i * 8);
        }
        return s;
    }
    static IntPtr NovaSaida()   /* zerada, como no exemplo da AMD */
    {
        IntPtr saida = Marshal.AllocHGlobal(TAM_SAIDA);
        for (int i = 0; i < TAM_SAIDA; i++) Marshal.WriteByte(saida, i, 0);
        return saida;
    }

    /* jeito 1: New_QueryPMLogData_Get (uma chamada) */
    static Dictionary<int, int> LerPmlog(Placa pl, StringBuilder diag)
    {
        IntPtr saida = NovaSaida();
        try
        {
            int r = ADL2_New_QueryPMLogData_Get(ctx, pl.indice, saida);
            Dictionary<int, int> s = r == 0 ? Sensores(saida) : null;
            if (diag != null) diag.Append("\"pmlog\":{\"r\":" + N(r) + (s != null ? ",\"sensores\":" + Mapa(s) : "") + "},");
            return s != null && s.Count > 0 ? s : null;
        }
        catch (EntryPointNotFoundException) { if (diag != null) diag.Append("\"pmlog\":{\"erro\":\"sem a função\"},"); return null; }
        finally { Marshal.FreeHGlobal(saida); }
    }

    /* jeito 2: a memória compartilhada (Overdrive8 PMLog), como no exemplo da AMD: liga uma vez e lê quando quiser */
    static Dictionary<int, int> LerCompartilhada(Placa pl, StringBuilder diag)
    {
        List<string> d = new List<string>();
        try
        {
            int r;
            if (!pl.iniciada)
            {
                int suporta;
                r = ADL2_Overdrive8_PMLog_ShareMemory_Support(ctx, pl.indice, out suporta, 0);
                d.Add("\"suporte\":[" + N(r) + "," + N(suporta) + "]");
                if (r != 0 || suporta == 0) return null;
                r = ADL2_Device_PMLog_Device_Create(ctx, pl.indice, out pl.disp);
                d.Add("\"dispositivo\":" + N(r));
                if (r != 0) return null;
                r = ADL2_Overdrive8_PMLogSenorType_Support_Get(ctx, pl.indice, out pl.nLista, out pl.lista);
                d.Add("\"lista\":[" + N(r) + "," + N(pl.nLista) + "]");
                IntPtr memoria;
                r = ADL2_Overdrive8_PMLog_ShareMemory_Start(ctx, pl.indice, 1000, -1, IntPtr.Zero, ref pl.disp, out memoria, 0);
                d.Add("\"iniciar\":" + N(r));
                if (r != 0) { ADL2_Device_PMLog_Device_Destroy(ctx, pl.disp); return null; }
                pl.memoria = memoria; pl.iniciada = true;
                Thread.Sleep(1200);   /* a primeira amostra sai depois de 1 segundo */
            }
            IntPtr saida = NovaSaida();
            try
            {
                r = ADL2_Overdrive8_PMLog_ShareMemory_Read(ctx, pl.indice, pl.nLista, pl.lista, ref pl.memoria, saida);
                Dictionary<int, int> s = r == 0 ? Sensores(saida) : null;
                d.Add("\"ler\":" + N(r));
                if (s != null) d.Add("\"sensores\":" + Mapa(s));
                return s != null && s.Count > 0 ? s : null;
            }
            finally { Marshal.FreeHGlobal(saida); }
        }
        catch (EntryPointNotFoundException e) { d.Add("\"erro\":" + Texto("sem a função " + e.Message)); return null; }
        finally { if (diag != null) diag.Append("\"compartilhada\":{" + string.Join(",", d.ToArray()) + "},"); }
    }

    static string Mapa(Dictionary<int, int> s)
    {
        StringBuilder b = new StringBuilder("{");
        bool primeiro = true;
        foreach (KeyValuePair<int, int> kv in s) { b.Append((primeiro ? "" : ",") + "\"" + N(kv.Key) + "\":" + N(kv.Value)); primeiro = false; }
        return b.Append("}").ToString();
    }
    static void Campo(StringBuilder b, string nome, Dictionary<int, int> s, int sensor)
    {
        int v;
        if (s.TryGetValue(sensor, out v)) b.Append(",\"" + nome + "\":" + N(v));
    }

    /* uma leitura de todas as placas AMD: {"ok":true,"quando":..., "placas":[{bus, nome, borda, memoria, quente, placaW, ...}]} */
    public static string Ler(bool diagnostico)
    {
        StringBuilder diag = diagnostico ? new StringBuilder("{\"diagnostico\":true,") : null;
        string e = Iniciar(diag);
        if (e != null) return diag != null ? diag.Append("\"resultado\":" + e + "}").ToString() : e;
        StringBuilder b = new StringBuilder("{\"ok\":true,\"quando\":" + ((long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalMilliseconds).ToString(CultureInfo.InvariantCulture) + ",\"placas\":[");
        if (diag != null) diag.Append("\"placas\":[");
        bool primeira = true, algum = false;
        foreach (Placa pl in placas)
        {
            if (diag != null) diag.Append((primeira ? "" : ",") + "{\"bus\":" + N(pl.bus) + ",");
            Dictionary<int, int> s = null;
            try
            {
                if (diag != null) { s = LerPmlog(pl, diag); Dictionary<int, int> s2 = LerCompartilhada(pl, diag); if (s == null) { s = s2; pl.metodo = s2 != null ? "compartilhada" : null; } else pl.metodo = "pmlog"; }
                else if (pl.metodo == "compartilhada") s = LerCompartilhada(pl, null);
                else if (pl.metodo == "pmlog") s = LerPmlog(pl, null);
                else { s = LerPmlog(pl, null); if (s != null) pl.metodo = "pmlog"; else { s = LerCompartilhada(pl, null); if (s != null) pl.metodo = "compartilhada"; } }
            }
            catch (Exception ex) { if (diag != null) diag.Append("\"erro\":" + Texto(ex.GetType().Name + ": " + ex.Message) + ","); s = null; }
            if (diag != null) diag.Append("\"metodo\":" + Texto(pl.metodo ?? "") + "}");
            b.Append((primeira ? "" : ",") + "{\"bus\":" + N(pl.bus) + ",\"nome\":" + Texto(pl.nome) + ",\"metodo\":" + Texto(pl.metodo ?? ""));
            if (s != null)
            {
                algum = true;
                Campo(b, "borda", s, T_BORDA); Campo(b, "memoria", s, T_MEMORIA); Campo(b, "quente", s, T_QUENTE);
                Campo(b, "placaW", s, P_PLACA); Campo(b, "chipW", s, P_CHIP); Campo(b, "rpm", s, FAN_RPM); Campo(b, "vent", s, FAN_PCT);
                Campo(b, "uso", s, USO_GFX); Campo(b, "clock", s, CLK_GFX); Campo(b, "clockMem", s, CLK_MEM); Campo(b, "mv", s, V_GFX);
            }
            b.Append("}");
            primeira = false;
        }
        b.Append("]}");
        string leitura = algum ? b.ToString() : Erro("sem-sensores", "o ADL não mandou os sensores das placas AMD");
        return diag != null ? diag.Append("],\"resultado\":" + leitura + "}").ToString() : leitura;
    }

    public static void Encerrar()
    {
        try
        {
            if (placas != null)
                foreach (Placa pl in placas)
                    if (pl.iniciada) { ADL2_Overdrive8_PMLog_ShareMemory_Stop(ctx, pl.indice, ref pl.disp); ADL2_Device_PMLog_Device_Destroy(ctx, pl.disp); pl.iniciada = false; }
            if (ctx != IntPtr.Zero) { ADL2_Main_Control_Destroy(ctx); ctx = IntPtr.Zero; }
        }
        catch (Exception) { }
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

try { Add-Type -TypeDefinition $codigo -Language CSharp }
catch { [Console]::Out.WriteLine('{"ok":false,"erro":"falhou","msg":' + (Json ("o leitor nao compilou: " + $_.Exception.Message)) + '}'); exit 2 }

$i = 0
try {
    if ($Diagnostico) {
        $versao = $PSVersionTable.PSVersion.ToString()
        [Console]::Out.WriteLine('{"powershell":"' + $versao + '","x64":' + ([Environment]::Is64BitProcess.ToString().ToLower()) + '}')
        [Console]::Out.WriteLine([SensoresAmd]::Ler($true))
        [Console]::Out.Flush()
        if ($Vezes -le 0) { return }
        Start-Sleep -Seconds $Intervalo
    }
    while ($true) {
        [Console]::Out.WriteLine([SensoresAmd]::Ler($false))
        [Console]::Out.Flush()
        $i++
        if ($Vezes -gt 0 -and $i -ge $Vezes) { break }
        Start-Sleep -Seconds $Intervalo
        if ($Pai -gt 0 -and -not (Get-Process -Id $Pai -ErrorAction SilentlyContinue)) { break }
    }
}
finally { [SensoresAmd]::Encerrar() }
