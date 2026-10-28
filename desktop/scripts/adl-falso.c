/* ADL de mentira (atiadlxx.dll), para testar o leitor da placa (placa-amd.ps1) no Linux, com o Mono.
   - FALSO_CENARIO escolhe a placa: 9070xt (o padrão), od7, sem-amd, sem-adl, duas, reinicia, modo-1 (o modo de energia em 1),
     sem-tensao (sem o ajuste de tensão), sem-admin (a gravação devolve -23);
   - FALSO_LOG recebe o nome de cada função chamada, uma por linha, e as gravações ("SET:placa=i", "SET:i=v", "SET:fim");
   - compilado com -DSO_X2, não tem as funções antigas do Overdrive8 (só as X2).
   A tabela da 9070 XT é a dos testes no PC do Alex (28/10/2026). Uma chamada fora do esperado escreve "ERRADA" na saída de
   erro; uma função que muda a placa escreve "PROIBIDO" e aborta. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void* (*Aloca)(int);

#define OD8_COUNT 77
#define TAM_INFO 1572

static Aloca aloca = 0;
static int geracao = 0, vivo = 0;
static void* ctx_atual(void) { return (void*)(long)(0x1000 + geracao); }

static const char* cen(void) { const char* c = getenv("FALSO_CENARIO"); return c && *c ? c : "9070xt"; }
static int eh(const char* c) { return strcmp(cen(), c) == 0; }
static void anota(const char* linha)
{
    const char* f = getenv("FALSO_LOG");
    if (!f) return;
    FILE* a = fopen(f, "a");
    if (a) { fprintf(a, "%s\n", linha); fclose(a); }
}
static void errada(const char* msg) { fprintf(stderr, "ERRADA: %s\n", msg); fflush(stderr); }
static void proibido(const char* fn) { anota(fn); fprintf(stderr, "PROIBIDO: %s\n", fn); fflush(stderr); abort(); }
static int confere(void* ctx, const char* fn)
{
    anota(fn);
    if (!vivo || ctx != ctx_atual()) { errada(fn); return 0; }
    return 1;
}

/* ---------- a tabela do Overdrive8 ---------- */
typedef struct { int id, min, max, padrao, atual; } Item;
static Item tab[OD8_COUNT + 8];
static int n_driver = OD8_COUNT - 1;   /* o driver de 10/2026 conhece 76 ajustes */
static int caps = 0, montada = 0;

static void poe(int i, int min, int max, int padrao, int atual) { tab[i].min = min; tab[i].max = max; tab[i].padrao = padrao; tab[i].atual = atual; }
static void monta(void)
{
    if (montada) return;
    montada = 1;
    for (int i = 0; i < OD8_COUNT + 8; i++) { tab[i].id = i; tab[i].min = tab[i].max = tab[i].padrao = tab[i].atual = 0; }
    /* clock, memória, potência, temporização, zero rpm, auto UV/OC, curva, modo, tensão, interface, auto UV 2 */
    caps = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11) | (1 << 12) | (1 << 13) | (1 << 16) | (1 << 17) | (1 << 26) | (1 << 27);
    if (eh("sem-tensao")) caps &= ~(1 << 17);
    poe(0, -500, 1000, 0, 0);          /* clock máximo (offset) */
    poe(8, 2518, 3000, 2518, 2518);    /* memória máxima */
    poe(9, -30, 10, 0, -20);           /* potência % */
    poe(14, 0, 1, 0, 0);               /* temporização */
    poe(15, 0, 1, 1, 0);               /* zero rpm */
    int tc[5] = { 30, 50, 61, 72, 80 }, sp[5] = { 15, 32, 49, 66, 100 };
    for (int p = 0; p < 5; p++) { poe(19 + 2 * p, 25, 100, tc[p], tc[p]); poe(20 + 2 * p, 15, 100, sp[p], 74); }
    poe(35, 0, 0, 0, 50);
    poe(36, 0, 3, 3, eh("modo-1") ? 1 : 3);   /* modo de energia: 3 é o manual */
    poe(37, -200, 0, 0, -75);          /* tensão (offset, mV) */
    poe(74, 1, 3, 1, 1);
}

/* ---------- contexto ---------- */
static int falhando = 0;

int ADL2_Main_Control_Create(Aloca cb, int conectados, void** ctx)
{
    anota("ADL2_Main_Control_Create");
    if (eh("sem-adl")) return -1;
    if (!cb || conectados != 1) { errada("Main_Control_Create"); return -3; }
    aloca = cb; geracao++; vivo = 1; falhando = 0; *ctx = ctx_atual();
    monta();
    return 0;
}
int ADL2_Main_Control_Destroy(void* ctx)
{
    if (!confere(ctx, "ADL2_Main_Control_Destroy")) return -2;
    vivo = 0;
    return 0;
}

/* ---------- placas ---------- */
static int n_adaptadores(void) { return eh("duas") ? 5 : eh("sem-amd") ? 2 : 3; }
static void adaptador(char* p, int indice, int bus, int vendor, const char* nome, const char* pnp)
{
    memset(p, 0, TAM_INFO);
    *(int*)(p + 0) = TAM_INFO; *(int*)(p + 4) = indice; *(int*)(p + 264) = bus; *(int*)(p + 276) = vendor;
    strncpy(p + 280, nome, 255); *(int*)(p + 792) = 1; *(int*)(p + 796) = 1;
    strncpy(p + 1312, pnp, 255);
}
#define PNP1 "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019"
#define PNP2 "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&1A0C77E2&0&00080019"
int ADL2_Adapter_NumberOfAdapters_Get(void* ctx, int* n)
{
    if (!confere(ctx, "ADL2_Adapter_NumberOfAdapters_Get")) return -2;
    *n = n_adaptadores();
    return 0;
}
int ADL2_Adapter_AdapterInfo_Get(void* ctx, char* info, int tam)
{
    if (!confere(ctx, "ADL2_Adapter_AdapterInfo_Get")) return -2;
    if (tam != TAM_INFO * n_adaptadores()) { errada("AdapterInfo com outro tamanho"); return -4; }
    if (eh("sem-amd")) {
        adaptador(info, 0, 0, 8086, "Intel(R) UHD Graphics 770", "PCI\\VEN_8086&DEV_4680");
        adaptador(info + TAM_INFO, 1, 0, 8086, "Intel(R) UHD Graphics 770", "PCI\\VEN_8086&DEV_4680");
        return 0;
    }
    for (int i = 0; i < 3; i++) adaptador(info + TAM_INFO * i, i, 3, 1002, "AMD Radeon RX 9070 XT", PNP1);
    if (eh("duas")) {
        adaptador(info + TAM_INFO * 3, 3, 0, 8086, "Intel(R) UHD Graphics 770", "PCI\\VEN_8086&DEV_4680");
        adaptador(info + TAM_INFO * 4, 4, 7, 1002, "AMD Radeon RX 9070 XT", PNP2);
    }
    return 0;
}
static int placa_ok(int idx) { return idx == 0 || idx == 1 || idx == 2 || (eh("duas") && idx == 4); }
int ADL2_Overdrive_Caps(void* ctx, int idx, int* s, int* l, int* v)
{
    if (!confere(ctx, "ADL2_Overdrive_Caps")) return -2;
    if (!placa_ok(idx)) { errada("Overdrive_Caps de placa que não é AMD"); return -5; }
    *s = 1; *l = 1; *v = eh("od7") ? 7 : 8;
    return 0;
}

/* ---------- Overdrive8 ---------- */
#ifndef SO_X2
static int leituras_atuais = 0;
int ADL2_Overdrive8_Init_Setting_Get(void* ctx, int idx, int* init)
{
    if (!confere(ctx, "ADL2_Overdrive8_Init_Setting_Get")) return -2;
    if (eh("od7")) return -8;
    if (!placa_ok(idx)) { errada("Init_Setting_Get de placa que não é AMD"); return -5; }
    if (init[0] != OD8_COUNT) { errada("Init_Setting_Get com count diferente de 77"); return -4; }
    int m = init[0] < n_driver ? init[0] : n_driver;
    init[1] = caps;
    for (int i = 0; i < m; i++) { int* e = init + 2 + 4 * i; e[0] = tab[i].id; e[1] = tab[i].min; e[2] = tab[i].max; e[3] = tab[i].padrao; }
    init[0] = m;
    return 0;
}
int ADL2_Overdrive8_Current_Setting_Get(void* ctx, int idx, int* atual)
{
    if (!confere(ctx, "ADL2_Overdrive8_Current_Setting_Get")) return -2;
    if (eh("od7")) return -8;
    if (!placa_ok(idx)) { errada("Current_Setting_Get de placa que não é AMD"); return -5; }
    if (eh("reinicia") && ++leituras_atuais == 2) falhando = 1;   /* o driver reiniciou: até um Create novo, falha */
    if (falhando) return -10;
    if (atual[0] != OD8_COUNT) { errada("Current_Setting_Get com count diferente de 77"); return -4; }
    int m = atual[0] < n_driver ? atual[0] : n_driver;
    for (int i = 0; i < m; i++) atual[1 + i] = tab[i].atual;
    atual[0] = m;
    return 0;
}
#endif
int ADL2_Overdrive8_Init_SettingX2_Get(void* ctx, int idx, int* c, int* n, void** lista)
{
    if (!confere(ctx, "ADL2_Overdrive8_Init_SettingX2_Get")) return -2;
    if (eh("od7")) return -8;
    if (*n != OD8_COUNT) return -9;   /* como o driver de verdade: sem o número de entrada, -9 */
    int* l = (int*)aloca(n_driver * 16);
    for (int i = 0; i < n_driver; i++) { l[4 * i] = tab[i].id; l[4 * i + 1] = tab[i].min; l[4 * i + 2] = tab[i].max; l[4 * i + 3] = tab[i].padrao; }
    *c = caps; *n = n_driver; *lista = l;
    return 0;
}
int ADL2_Overdrive8_Current_SettingX2_Get(void* ctx, int idx, int* n, void** lista)
{
    if (!confere(ctx, "ADL2_Overdrive8_Current_SettingX2_Get")) return -2;
    if (eh("od7")) return -8;
    if (*n != OD8_COUNT) return -9;
    int* l = (int*)aloca(n_driver * 4);
    for (int i = 0; i < n_driver; i++) l[i] = tab[i].atual;
    *n = n_driver; *lista = l;
    return 0;
}

/* ---------- sensores ---------- */
static int manual = 1;   /* a ventoinha na curva gravada (2552 rpm) ou no automático (1500 rpm) */
int ADL2_New_QueryPMLogData_Get(void* ctx, int idx, int* saida)
{
    if (!confere(ctx, "ADL2_New_QueryPMLogData_Get")) return -2;
    int ids[10] = { 1, 2, 8, 9, 14, 15, 19, 21, 27, 73 }, val[10] = { 2950, 2518, 44, 60, manual ? 2552 : 1500, manual ? 74 : 40, 99, 850, 61, 301 };
    for (int k = 0; k < 10; k++) { saida[1 + 2 * ids[k]] = 1; saida[2 + 2 * ids[k]] = val[k]; }
    return 0;
}

/* ---------- o que muda a placa ---------- */
int ADL2_Adapter_RegValueInt_Set(void* ctx, int idx, int opcao, const char* sub, const char* nome, int v) { proibido("ADL2_Adapter_RegValueInt_Set"); return -8; }
/* grava: só os ajustes que o painel pode gravar, sem reset, o modo só em 3; anota "SET:i=v" de cada um e "SET:fim".
   Como a placa de verdade, uma gravação sem a curva põe a ventoinha no automático. */
static int pode_gravar(int i) { return i == 0 || i == 8 || i == 9 || i == 14 || i == 15 || (i >= 19 && i <= 28) || i == 36 || i == 37; }
int ADL2_Overdrive8_Setting_Set(void* ctx, int idx, int* set, int* atual)
{
    if (!confere(ctx, "ADL2_Overdrive8_Setting_Set")) return -2;
    if (!placa_ok(idx)) { errada("Setting_Set de placa que não é AMD"); return -5; }
    char linha[64];
    snprintf(linha, sizeof linha, "SET:placa=%d", idx); anota(linha);
    int count = set[0];
    if (count != n_driver) { errada("Setting_Set com count diferente do que o driver conhece"); return -3; }
    int novo[OD8_COUNT + 8], tem_curva = 0;
    for (int i = 0; i < count; i++) novo[i] = tab[i].atual;
    for (int i = 0; i < count; i++)
    {
        int* e = set + 1 + 3 * i;   /* value, requested, reset */
        if (e[2]) proibido("Setting_Set com reset");
        if (!e[1]) { if (e[0]) { errada("valor num ajuste sem requested"); return -3; } continue; }
        if (!pode_gravar(i)) proibido("Setting_Set de um ajuste fora da lista");
        if (i == 36 && e[0] != 3) proibido("Setting_Set do modo diferente de 3");
        if (e[0] < tab[i].min || e[0] > tab[i].max) { errada("Setting_Set fora da faixa"); return -3; }
        snprintf(linha, sizeof linha, "SET:%d=%d", i, e[0]); anota(linha);
        if (i >= 19 && i <= 28) tem_curva = 1;
        novo[i] = e[0];
    }
    if (eh("sem-admin")) { anota("SET:recusou"); return -23; }   /* confere o pedido inteiro, mas não grava */
    anota("SET:fim");
    for (int i = 0; i < count; i++) tab[i].atual = novo[i];
    manual = tem_curva;
    int m = atual[0] < n_driver ? atual[0] : n_driver;
    for (int i = 0; i < m; i++) atual[1 + i] = tab[i].atual;
    atual[0] = m;
    return 0;
}
