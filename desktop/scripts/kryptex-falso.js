"use strict";
/* App da Kryptex de mentira para os testes: as mesmas rotas e o mesmo formato do serviço do app da Kryptex do Windows
   (KryptexService.exe, em http://localhost:8107). Modos: "minerando", "pausado" (ainda mostra o hashrate de antes, como o
   app de verdade nos primeiros segundos), "quente" (86 °C), "parado" (sem minerar e sem pausa) e "fechado" (não responde).
   Guarda cada pedido em `pedidos` ({metodo, caminho, corpo}). */
module.exports = function criar() {
  const estado = { modo: "minerando", saldo: 0.0001, temp: 63, tempMem: 78, watts: 286, pausaAte: null };
  const pedidos = [];

  function dispositivos() {
    const quente = estado.modo === "quente", minerando = estado.modo === "minerando" || quente, pausado = estado.modo === "pausado";
    const hash = minerando ? 1.13e14 : pausado ? 1.12e14 : 0;
    return [
      { id: "d-gpu-1", device: { id: "gpu-1", type: "gpu", vendor: "amd", name: "AMD Radeon RX 9070 XT", memory_size: 17095983104, integrated: false, configuration: { disabled: false } },
        reading: { id: "r-1", pci_address: "0000:03:00.0", core_temperature: quente ? 86 : estado.temp, memory_temperature: estado.tempMem, power_usage: minerando ? estado.watts : 18,
          core_clock: 2400, memory_clock: 1258, fan_speed: 54, rebar: true, driver_version: "25.9.1", campo_novo_qualquer: 7, dono: "alex.teste@example.com" },
        algorithm_combinations: [
          { id: "c-1", algorithms: [{ id: "a-1", coin: "prl", algorithm: "pearlhash" }],
            miners: [{ id: "m-1", name: "srbminer", stats: { coin_algorithms: [{ hashrate: hash, local_hashrate: hash, server_hashrate: hash * 0.97, profitability: 2.965 }],
              reading_count: 12, process_count: minerando ? 1 : 0, error_count: 0, error_count_1h: 0, benchmark_success: true, profitability: 2.965 }, configuration: { token: "7f3a9c2e1b4d5f60718293a4b5c6d7e8" } }],
            configuration: { disabled: false, core_clock_locked: false, power_limit: 0, fan_speed: 0 } },
          { id: "c-2", algorithms: [{ id: "a-2", coin: "etc", algorithm: "etchash" }],
            miners: [{ id: "m-2", name: "lolminer", stats: { coin_algorithms: [{ hashrate: 0, local_hashrate: 0, server_hashrate: 0, profitability: 1.1 }],
              reading_count: 0, process_count: 0, error_count: 0, error_count_1h: 0, benchmark_success: true, profitability: 1.1 }, configuration: {} }],
            configuration: { disabled: false } }] },
      { id: "d-cpu-1", device: { id: "cpu-1", type: "cpu", vendor: "intel", name: "13th Gen Intel(R) Core(TM) i7-13700", memory_size: 0, integrated: false, configuration: { disabled: false } },
        reading: { id: "r-2", core_temperature: 52, core_clock: 3400 },
        algorithm_combinations: [{ id: "c-3", algorithms: [{ id: "a-3", coin: "xmr", algorithm: "randomx" }],
          miners: [{ id: "m-3", name: "xmrig", stats: { coin_algorithms: [{ hashrate: 0, local_hashrate: 0, profitability: 0.31 }], process_count: 0, error_count_1h: 0, profitability: 0.31 }, configuration: {} }],
          configuration: { disabled: false } }] }
    ];
  }

  function responder(res, status, obj) {
    const corpo = JSON.stringify(obj);
    res.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(corpo), "Cache-Control": "no-store" });
    res.end(corpo);
  }

  function tratar(req, res, caminho) {
    let corpo = "";
    req.on("data", (c) => { corpo += c; });
    req.on("end", () => {
      pedidos.push({ metodo: req.method, caminho, corpo });
      if (estado.modo === "fechado") return;   /* não responde: quem pede desiste pelo limite de tempo */
      if (req.method === "GET" && caminho === "/devices") return responder(res, 200, dispositivos());
      if (req.method === "GET" && caminho === "/balance") return responder(res, 200, { total: estado.saldo, withdrawable: 0 });
      if (req.method === "GET" && caminho === "/pause") return responder(res, 200, estado.modo === "pausado" ? { pause: true, pause_until: estado.pausaAte } : { pause: false });
      if (req.method === "GET" && caminho === "/currency-rates") return responder(res, 200, { brl: 4.965204, btc: 0.00001237, eur: 0.89267, usd: 1 });
      if (req.method === "GET" && caminho === "/configuration") return responder(res, 200, { currency: "brl", language: "pt-BR", os_startup: true, user_active_pause: false, computer_name: "PC-TESTE" });
      if (req.method === "GET" && caminho === "/user") return responder(res, 200, { username: "alex.teste@example.com" });
      if (req.method === "PUT" && caminho === "/pause") {
        let o = {}; try { o = JSON.parse(corpo || "{}"); } catch (e) { return responder(res, 400, { error: "json" }); }
        if (o.pause === false) { estado.modo = "minerando"; estado.pausaAte = null; }
        else if (o.pause_for > 0) { estado.modo = "pausado"; estado.pausaAte = new Date(Date.now() + o.pause_for).toISOString(); }
        return responder(res, 200, {});
      }
      responder(res, 404, { error: "not found" });
    });
  }

  return { estado, pedidos, tratar };
};
