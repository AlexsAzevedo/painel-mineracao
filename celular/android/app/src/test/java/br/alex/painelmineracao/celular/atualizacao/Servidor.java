package br.alex.painelmineracao.celular.atualizacao;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Servidor HTTP local, mínimo, para os testes de download (o com.sun.net.httpserver não está no classpath dos testes do
 * Android): uma resposta por caminho e a lista dos pedidos. Cada conexão atende um pedido e fecha.
 */
final class Servidor implements AutoCloseable {
    interface Resposta { void responder(OutputStream o) throws IOException; }

    private final ServerSocket socket;
    private final Map<String, Resposta> rotas = new ConcurrentHashMap<>();
    final List<String> pedidos = Collections.synchronizedList(new ArrayList<>());

    Servidor() throws IOException {
        socket = new ServerSocket(0, 50, InetAddress.getByName("127.0.0.1"));
        Thread t = new Thread(this::atender, "servidor-teste");
        t.setDaemon(true);
        t.start();
    }

    private void atender() {
        while (!socket.isClosed()) {
            try (Socket c = socket.accept()) {
                BufferedReader in = new BufferedReader(new InputStreamReader(c.getInputStream(), StandardCharsets.ISO_8859_1));
                String linha = in.readLine();
                if (linha == null) continue;
                String caminho = linha.split(" ")[1];
                for (String h = in.readLine(); h != null && !h.isEmpty(); h = in.readLine()) { /* cabeçalhos: não interessam */ }
                pedidos.add(caminho);
                Resposta r = rotas.get(caminho);
                OutputStream o = c.getOutputStream();
                if (r == null) codigo(404).responder(o); else r.responder(o);
                o.flush();
            } catch (IOException e) {
                /* conexão que caiu ou servidor fechado */
            }
        }
    }

    String url(String caminho) { return "http://127.0.0.1:" + socket.getLocalPort() + caminho; }

    Servidor em(String caminho, Resposta r) { rotas.put(caminho, r); return this; }

    private static void cabecalho(OutputStream o, String status, String... extras) throws IOException {
        StringBuilder b = new StringBuilder("HTTP/1.1 ").append(status).append("\r\nConnection: close\r\n");
        for (String e : extras) b.append(e).append("\r\n");
        o.write(b.append("\r\n").toString().getBytes(StandardCharsets.ISO_8859_1));
    }

    static Resposta bytes(byte[] corpo) {
        return o -> { cabecalho(o, "200 OK", "Content-Length: " + corpo.length); o.write(corpo); };
    }

    /** sem Content-Length: o corpo acaba quando a conexão fecha */
    static Resposta emPartes(byte[] corpo) {
        return o -> { cabecalho(o, "200 OK"); o.write(corpo); };
    }

    static Resposta redireciona(int codigo, String para) {
        return o -> cabecalho(o, codigo + " Redirecionando", "Location: " + para, "Content-Length: 0");
    }

    static Resposta codigo(int codigo) {
        return o -> cabecalho(o, codigo + " Resposta", "Content-Length: 0");
    }

    @Override public void close() {
        try { socket.close(); } catch (IOException e) { /* já fechado */ }
    }
}
