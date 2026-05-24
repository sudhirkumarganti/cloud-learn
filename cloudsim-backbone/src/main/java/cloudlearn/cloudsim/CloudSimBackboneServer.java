package cloudlearn.cloudsim;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public final class CloudSimBackboneServer {
    private static final ObjectMapper MAPPER = new ObjectMapper().registerModule(new JavaTimeModule());

    public static void main(String[] args) throws Exception {
        final String host = System.getenv().getOrDefault("CLOUDLEARN_CLOUDSIM_HOST", "127.0.0.1");
        final int port = Integer.parseInt(System.getenv().getOrDefault("CLOUDLEARN_CLOUDSIM_PORT", "9010"));
        final String stateFile = System.getenv().getOrDefault("CLOUDLEARN_CLOUDSIM_STATE_FILE", "").trim();
        final CloudSimRegistry registry = stateFile.isBlank() ? new CloudSimRegistry() : new CloudSimRegistry(Path.of(stateFile));

        HttpServer server = HttpServer.create(new InetSocketAddress(host, port), 0);
        server.createContext("/health", exchange -> sendJson(exchange, 200, Map.of(
                "status", "ok",
                "service", "cloudsim-backbone",
                "timestamp", Instant.now().toString(),
                "spaces", registry.spaceCount()
        )));
        server.createContext("/spaces", exchange -> handleSpaces(exchange, registry));
        server.createContext("/summary", exchange -> sendJson(exchange, 200, registry.summary()));
        server.createContext("/events", exchange -> sendJson(exchange, 200, registry.eventsPayload()));
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        System.out.println("CloudLearn CloudSim backbone listening on " + host + ":" + port);
    }

    private static void handleSpaces(HttpExchange exchange, CloudSimRegistry registry) throws IOException {
        final String method = exchange.getRequestMethod().toUpperCase();
        final String path = exchange.getRequestURI().getPath();
        if ("/spaces".equals(path)) {
            if ("GET".equals(method)) {
                sendJson(exchange, 200, registry.listSpaces());
                return;
            }
            if ("POST".equals(method)) {
                Map<String, Object> payload = readJson(exchange);
                sendJson(exchange, 200, registry.upsertSpace(payload));
                return;
            }
            sendMethodNotAllowed(exchange, List.of("GET", "POST"));
            return;
        }

        if (!path.startsWith("/spaces/")) {
            sendNotFound(exchange);
            return;
        }

        final String[] parts = path.substring("/spaces/".length()).split("/");
        final String spaceId = decodePathSegment(parts[0]);
        if (spaceId.isBlank()) {
            sendNotFound(exchange);
            return;
        }
        if (parts.length == 1) {
            if ("GET".equals(method)) {
                sendJson(exchange, 200, registry.getSpace(spaceId));
                return;
            }
            if ("DELETE".equals(method)) {
                sendJson(exchange, 200, registry.deleteSpace(spaceId));
                return;
            }
            sendMethodNotAllowed(exchange, List.of("GET", "DELETE"));
            return;
        }

        final String action = parts[1];
        if ("switch".equals(action) && "POST".equals(method)) {
            sendJson(exchange, 200, registry.switchSpace(spaceId));
            return;
        }
        if ("pause".equals(action) && "POST".equals(method)) {
            sendJson(exchange, 200, registry.changeStatus(spaceId, "paused"));
            return;
        }
        if ("resume".equals(action) && "POST".equals(method)) {
            sendJson(exchange, 200, registry.changeStatus(spaceId, "running"));
            return;
        }
        if ("archive".equals(action) && "POST".equals(method)) {
            sendJson(exchange, 200, registry.changeStatus(spaceId, "archived"));
            return;
        }
        if ("reconcile".equals(action) && "POST".equals(method)) {
            sendJson(exchange, 200, registry.reconcile(spaceId));
            return;
        }
        if ("events".equals(action)) {
            if ("GET".equals(method)) {
                sendJson(exchange, 200, registry.spaceEvents(spaceId));
                return;
            }
            if ("POST".equals(method)) {
                sendJson(exchange, 200, registry.recordEvent(spaceId, readJson(exchange)));
                return;
            }
            sendMethodNotAllowed(exchange, List.of("GET", "POST"));
            return;
        }

        sendNotFound(exchange);
    }

    private static Map<String, Object> readJson(HttpExchange exchange) throws IOException {
        try (InputStream in = exchange.getRequestBody()) {
            byte[] bytes = in.readAllBytes();
            if (bytes.length == 0) {
                return new LinkedHashMap<>();
            }
            return MAPPER.readValue(new String(bytes, StandardCharsets.UTF_8), new TypeReference<>() {});
        }
    }

    private static void sendJson(HttpExchange exchange, int status, Object payload) throws IOException {
        byte[] body = MAPPER.writeValueAsBytes(payload);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(body);
        }
    }

    private static void sendNotFound(HttpExchange exchange) throws IOException {
        sendJson(exchange, 404, Map.of("detail", "NotFound"));
    }

    private static void sendMethodNotAllowed(HttpExchange exchange, List<String> allowed) throws IOException {
        exchange.getResponseHeaders().set("Allow", String.join(", ", allowed));
        sendJson(exchange, 405, Map.of("detail", "MethodNotAllowed", "allowed", allowed));
    }

    private static String decodePathSegment(String segment) {
        return URLDecoder.decode(segment, StandardCharsets.UTF_8);
    }
}
