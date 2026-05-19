package cloudlearn.cloudsim;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;

public final class CloudSimRegistry {
    private final Map<String, CloudSimSpace> spaces = new ConcurrentHashMap<>();
    private final AtomicReference<String> activeSpaceId = new AtomicReference<>("");
    private final List<Map<String, Object>> events = new ArrayList<>();

    public synchronized int spaceCount() {
        return spaces.size();
    }

    public synchronized Map<String, Object> upsertSpace(Map<String, Object> payload) {
        final String spaceId = stringValue(payload.getOrDefault("space_id", payload.getOrDefault("id", "")));
        if (spaceId.isBlank()) {
            throw new IllegalArgumentException("space_id is required");
        }
        CloudSimSpace space = spaces.computeIfAbsent(spaceId, CloudSimSpace::new);
        space.apply(payload);
        if (activeSpaceId.get().isBlank()) {
            activeSpaceId.set(spaceId);
        }
        Map<String, Object> summary = space.reconcile();
        events.add(event("space.upsert", spaceId, summary));
        return response(space, summary);
    }

    public synchronized Map<String, Object> getSpace(String spaceId) {
        CloudSimSpace space = spaces.get(spaceId);
        if (space == null) {
            throw new IllegalArgumentException("SimulationSpaceNotFound");
        }
        return response(space, space.snapshot());
    }

    public synchronized Map<String, Object> listSpaces() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (CloudSimSpace space : spaces.values()) {
            items.add(space.snapshot());
        }
        items.sort((a, b) -> {
            int cmp = stringValue(a.getOrDefault("created_at", "")).compareTo(stringValue(b.getOrDefault("created_at", "")));
            if (cmp != 0) return cmp;
            return stringValue(a.getOrDefault("name", "")).compareTo(stringValue(b.getOrDefault("name", "")));
        });
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("spaces", items);
        payload.put("count", items.size());
        payload.put("active_space_id", activeSpaceId.get());
        if (!activeSpaceId.get().isBlank()) {
            CloudSimSpace active = spaces.get(activeSpaceId.get());
            payload.put("active_space", active == null ? null : response(active, active.snapshot()));
        } else {
            payload.put("active_space", null);
        }
        payload.put("summary", summary());
        return payload;
    }

    public synchronized Map<String, Object> switchSpace(String spaceId) {
        CloudSimSpace space = requireSpace(spaceId);
        activeSpaceId.set(spaceId);
        space.touch("selected_at");
        events.add(event("space.switch", spaceId, Map.of("space_id", spaceId)));
        return response(space, space.snapshot());
    }

    public synchronized Map<String, Object> changeStatus(String spaceId, String status) {
        CloudSimSpace space = requireSpace(spaceId);
        space.setStatus(status);
        events.add(event("space.status", spaceId, Map.of("space_id", spaceId, "status", status)));
        return response(space, space.snapshot());
    }

    public synchronized Map<String, Object> deleteSpace(String spaceId) {
        CloudSimSpace removed = spaces.remove(spaceId);
        if (removed == null) {
            throw new IllegalArgumentException("SimulationSpaceNotFound");
        }
        if (spaceId.equals(activeSpaceId.get())) {
            activeSpaceId.set(spaces.keySet().stream().findFirst().orElse(""));
        }
        events.add(event("space.delete", spaceId, Map.of("space_id", spaceId)));
        return Map.of("message", "Simulation space deleted", "space_id", spaceId, "active_space_id", activeSpaceId.get());
    }

    public synchronized Map<String, Object> reconcile(String spaceId) {
        if (spaceId != null && !spaceId.isBlank()) {
            CloudSimSpace space = requireSpace(spaceId);
            Map<String, Object> summary = space.reconcile();
            events.add(event("space.reconcile", spaceId, summary));
            return response(space, summary);
        }
        return reconcileAll();
    }

    public synchronized Map<String, Object> reconcileAll() {
        List<Map<String, Object>> summaries = new ArrayList<>();
        for (CloudSimSpace space : spaces.values()) {
            if (!"archived".equals(space.getStatus())) {
                summaries.add(space.reconcile());
            } else {
                summaries.add(space.snapshot());
            }
        }
        Map<String, Object> payload = summary();
        payload.put("reconciled_spaces", summaries);
        payload.put("last_reconcile_at", Instant.now().toString());
        events.add(event("cloudsim.reconcile", null, Map.of("spaces", spaces.size())));
        return Map.of(
                "message", "CloudSim reconcile complete",
                "summary", payload,
                "spaces", listSpaces().get("spaces"),
                "events_count", events.size()
        );
    }

    public synchronized Map<String, Object> recordEvent(String spaceId, Map<String, Object> payload) {
        CloudSimSpace space = requireSpace(spaceId);
        Map<String, Object> result = space.recordEvent(payload);
        events.add(event(
                stringValue(payload == null ? null : payload.get("event")),
                spaceId,
                payload == null ? Map.of() : payload
        ));
        return result;
    }

    public synchronized Map<String, Object> summary() {
        Map<String, Integer> providerCounts = new LinkedHashMap<>();
        Map<String, Integer> statusCounts = new LinkedHashMap<>();
        int totalHosts = 0;
        int totalVms = 0;
        int totalCloudlets = 0;
        for (CloudSimSpace space : spaces.values()) {
            Map<String, Object> snap = space.snapshot();
            String provider = stringValue(snap.getOrDefault("provider", "aws"));
            providerCounts.put(provider, providerCounts.getOrDefault(provider, 0) + 1);
            String status = stringValue(snap.getOrDefault("status", "running"));
            statusCounts.put(status, statusCounts.getOrDefault(status, 0) + 1);
            totalHosts += intValue(snap.getOrDefault("hosts", 0));
            totalVms += intValue(snap.getOrDefault("vms", 0));
            totalCloudlets += intValue(snap.getOrDefault("cloudlets", 0));
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("spaces", spaces.size());
        payload.put("active_space_id", activeSpaceId.get());
        payload.put("active_space", activeSpaceId.get().isBlank() ? null : activeSpaceSnapshot());
        payload.put("provider_counts", providerCounts);
        payload.put("status_counts", statusCounts);
        payload.put("total_hosts", totalHosts);
        payload.put("total_vms", totalVms);
        payload.put("total_cloudlets", totalCloudlets);
        payload.put("max_spaces", 6);
        payload.put("last_reconcile_at", events.isEmpty() ? "" : stringValue(events.get(events.size() - 1).getOrDefault("at", "")));
        payload.put("cloudsim_engine", "CloudSim Plus 8.5.7");
        return payload;
    }

    public synchronized Map<String, Object> eventsPayload() {
        return Map.of(
                "events", new ArrayList<>(events),
                "count", events.size()
        );
    }

    public synchronized Map<String, Object> spaceEvents(String spaceId) {
        return requireSpace(spaceId).eventsPayload();
    }

    private Map<String, Object> activeSpaceSnapshot() {
        CloudSimSpace space = spaces.get(activeSpaceId.get());
        return space == null ? null : space.snapshot();
    }

    private CloudSimSpace requireSpace(String spaceId) {
        CloudSimSpace space = spaces.get(spaceId);
        if (space == null) {
            throw new IllegalArgumentException("SimulationSpaceNotFound");
        }
        return space;
    }

    private Map<String, Object> response(CloudSimSpace space, Map<String, Object> summary) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("space", space.snapshot());
        payload.put("summary", summary);
        payload.put("active_space_id", activeSpaceId.get());
        return payload;
    }

    private Map<String, Object> event(String type, String spaceId, Map<String, Object> detail) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event", type);
        payload.put("space_id", spaceId);
        payload.put("at", Instant.now().toString());
        payload.put("detail", detail == null ? Map.of() : detail);
        return payload;
    }

    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(stringValue(value));
        } catch (Exception e) {
            return 0;
        }
    }
}
