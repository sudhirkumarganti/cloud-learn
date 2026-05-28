package cloudlearn.cloudsim;

import org.cloudsimplus.brokers.DatacenterBrokerSimple;
import org.cloudsimplus.cloudlets.CloudletSimple;
import org.cloudsimplus.core.CloudSimPlus;
import org.cloudsimplus.datacenters.DatacenterSimple;
import org.cloudsimplus.hosts.HostSimple;
import org.cloudsimplus.resources.PeSimple;
import org.cloudsimplus.utilizationmodels.UtilizationModelDynamic;
import org.cloudsimplus.vms.VmSimple;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class CloudSimSpace {
    private final String spaceId;
    private final Map<String, Object> spec = new LinkedHashMap<>();
    private final List<Map<String, Object>> events = new ArrayList<>();
    private Map<String, Object> lastSummary = new LinkedHashMap<>();
    private String status = "running";
    private String createdAt = Instant.now().toString();
    private String updatedAt = createdAt;

    public CloudSimSpace(String spaceId) {
        this.spaceId = spaceId;
        this.spec.put("space_id", spaceId);
        this.spec.put("provider", "aws");
        this.spec.put("name", spaceId);
        this.spec.put("region", "us-east-1");
        this.spec.put("runtime_count", 0);
        this.spec.put("ec2_count", 0);
        this.spec.put("lambda_count", 0);
        this.spec.put("rds_count", 0);
        this.spec.put("sqs_count", 0);
        this.spec.put("dynamodb_count", 0);
    }

    public synchronized void apply(Map<String, Object> payload) {
        if (payload == null) {
            return;
        }
        for (Map.Entry<String, Object> entry : payload.entrySet()) {
            spec.put(entry.getKey(), entry.getValue());
        }
        if (payload.containsKey("status")) {
            this.status = stringValue(payload.get("status"), this.status).toLowerCase(Locale.ROOT);
        }
        this.updatedAt = Instant.now().toString();
    }

    public synchronized void setStatus(String status) {
        this.status = stringValue(status, this.status).toLowerCase(Locale.ROOT);
        this.updatedAt = Instant.now().toString();
    }

    public synchronized String getStatus() {
        return status;
    }

    public synchronized void touch(String field) {
        if (field != null && !field.isBlank()) {
            spec.put(field, Instant.now().toString());
        }
        this.updatedAt = Instant.now().toString();
    }

    public synchronized Map<String, Object> reconcile() {
        if ("archived".equals(status)) {
            return snapshot();
        }

        final int runtimeCount = intValue(spec.get("runtime_count"));
        final int ec2Count = intValue(spec.get("ec2_count"));
        final int lambdaCount = intValue(spec.get("lambda_count"));
        final int rdsCount = intValue(spec.get("rds_count"));
        final int sqsCount = intValue(spec.get("sqs_count"));
        final int ddbCount = intValue(spec.get("dynamodb_count"));

        // Per-provider aggregate counts (Python pushes these via CloudSimBridge
        // .sync_counts, pulled from THIS space's DB-derived inventory summary
        // — space-isolated by construction; licensing relies on this isolation).
        final int awsCountField = intValue(spec.get("aws_count"));
        final int gcpCount = intValue(spec.get("gcp_count"));
        final int azureCount = intValue(spec.get("azure_count"));
        final int gcpFunctionsCount = intValue(spec.get("gcp_functions_count"));
        final int azureFunctionappCount = intValue(spec.get("azure_functionapp_count"));
        // Backward-compat: if aws_count not provided, derive from legacy fields.
        final int awsCount = awsCountField > 0
                ? awsCountField
                : (ec2Count + lambdaCount + rdsCount + sqsCount + ddbCount);

        // Heterogeneous VM shapes — every real instance type (t3.micro, m5.large,
        // e2-medium, Standard_D8s_v5, …) becomes a CloudSim Plus Vm with the
        // RIGHT mips/PE/RAM via the Python catalog. Falls back to uniform
        // sizing when the bridge didn't send shapes (legacy clients).
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> vmShapes = spec.get("vm_shapes") instanceof List
                ? (List<Map<String, Object>>) spec.get("vm_shapes")
                : Collections.emptyList();

        List<org.cloudsimplus.vms.Vm> heteroVms = new ArrayList<>();
        int totalVcpus = 0;
        long totalRamMb = 0L;
        int maxVmPes = 1;
        long maxVmRam = 1024L;
        for (Map<String, Object> shape : vmShapes) {
            int count = Math.max(1, intValue(shape.get("count")));
            int vcpu = Math.max(1, intValue(shape.get("vcpu")));
            long ramMb = Math.max(512L, longValue(shape.get("ram_mb"), 1024L));
            int mips = Math.max(500, intValue(shape.get("mips_per_vcpu")));
            maxVmPes = Math.max(maxVmPes, vcpu);
            maxVmRam = Math.max(maxVmRam, ramMb);
            for (int i = 0; i < count; i++) {
                VmSimple vm = new VmSimple(mips, vcpu);
                vm.setRam(ramMb).setBw(1000).setSize(10000);
                heteroVms.add(vm);
            }
            totalVcpus += vcpu * count;
            totalRamMb += ramMb * count;
        }

        // Legacy/uniform fill: any non-compute resources in the per-cloud counts
        // (s3 buckets, dbs, queues, …) still contribute a small uniform VM so
        // they're represented in the capacity sim. Subtract the compute VMs we
        // already built from each provider's aggregate count.
        int legacyVmCount = Math.max(0,
                runtimeCount + awsCount + gcpCount + azureCount - heteroVms.size());
        int vmCount = Math.max(1, heteroVms.size() + legacyVmCount);

        // Hosts sized GENEROUSLY so VmAllocationPolicySimple's first-fit never
        // wedges. PEs must fit the largest VM; RAM is over-provisioned per host
        // and we add enough hosts that total capacity = ~2× the demand.
        int hostPes = Math.max(8, Math.min(128, maxVmPes * 2));
        long hostRam = Math.max(65536L, maxVmRam * 2 + 16384L);  // ≥64 GB or 2× largest
        long demandRamMb = totalRamMb + (long) legacyVmCount * 2048L;
        int hostCount = Math.max(1, Math.max(
                (int) Math.ceil((double) (totalVcpus + legacyVmCount) * 2 / hostPes),
                (int) Math.ceil((double) demandRamMb * 2 / hostRam)
        ));
        int cloudletCount = Math.max(1,
                vmCount + runtimeCount + lambdaCount + gcpFunctionsCount + azureFunctionappCount);

        CloudSimPlus simulation = new CloudSimPlus();
        // Safety: cap sim time so an unplaceable VM can't hang the engine.
        simulation.terminateAt(60.0);
        DatacenterBrokerSimple broker = new DatacenterBrokerSimple(simulation);
        List<org.cloudsimplus.hosts.Host> hosts = buildHosts(hostCount, hostPes, hostRam);
        new DatacenterSimple(simulation, hosts);
        // Compose VMs: heterogeneous compute VMs first, then uniform legacy fill.
        List<org.cloudsimplus.vms.Vm> vms = new ArrayList<>(heteroVms);
        if (legacyVmCount > 0) {
            vms.addAll(buildVms(legacyVmCount));
        }
        List<org.cloudsimplus.cloudlets.Cloudlet> cloudlets = buildCloudlets(cloudletCount);

        broker.submitVmList(vms);
        broker.submitCloudletList(cloudlets);
        simulation.start();

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("space_id", spaceId);
        summary.put("name", stringValue(spec.get("name"), spaceId));
        summary.put("provider", stringValue(spec.get("provider"), "aws").toLowerCase(Locale.ROOT));
        summary.put("status", status);
        summary.put("active_region", stringValue(spec.get("region"), "us-east-1"));
        summary.put("cloudsim_engine", "CloudSim Plus 8.5.7");
        summary.put("cloudsim_runtime_id", stringValue(spec.getOrDefault("cloudsim_runtime_id", "cloudsim-" + spaceId), "cloudsim-" + spaceId));
        summary.put("datacenters", 1);
        summary.put("hosts", hostCount);
        summary.put("vms", vms.size());
        summary.put("cloudlets", cloudlets.size());
        summary.put("finished_cloudlets", broker.getCloudletFinishedList().size());
        summary.put("runtime_count", runtimeCount);
        summary.put("ec2_count", ec2Count);
        summary.put("lambda_count", lambdaCount);
        summary.put("rds_count", rdsCount);
        summary.put("sqs_count", sqsCount);
        summary.put("dynamodb_count", ddbCount);
        // Per-cloud aggregates that drove the sizing — surfaced so consumers
        // (and licensing) can audit which cloud's resources contributed.
        summary.put("aws_count", awsCount);
        summary.put("gcp_count", gcpCount);
        summary.put("azure_count", azureCount);
        summary.put("gcp_functions_count", gcpFunctionsCount);
        summary.put("azure_functionapp_count", azureFunctionappCount);
        // Heterogeneous-VM facts: total CPU / RAM derived from REAL instance
        // shapes (m5.large, e2-medium, Standard_D8s_v5, …). Plus the shape
        // distribution echoed back so consumers can audit what was simulated.
        summary.put("total_vcpus", totalVcpus + legacyVmCount);
        summary.put("total_ram_mb", totalRamMb + (long) legacyVmCount * 1024L);
        summary.put("vm_shapes", vmShapes);
        summary.put("host_pes", hostPes);
        summary.put("host_ram_mb", hostRam);
        summary.put("last_tick", Instant.now().toString());
        summary.put("updated_at", updatedAt);
        summary.put("created_at", createdAt);
        summary.put("simulation_state", "completed");
        lastSummary = summary;
        events.add(event("cloudsim.reconcile", summary));
        return summary;
    }

    public synchronized Map<String, Object> recordEvent(Map<String, Object> payload) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        if (payload != null) {
            normalized.putAll(payload);
        }
        normalized.putIfAbsent("event", "cloudlearn.event");
        normalized.putIfAbsent("at", Instant.now().toString());
        normalized.putIfAbsent("space_id", spaceId);
        events.add(normalized);
        updatedAt = Instant.now().toString();
        return Map.of(
                "message", "Event recorded",
                "space_id", spaceId,
                "event", normalized
        );
    }

    public synchronized Map<String, Object> snapshot() {
        Map<String, Object> payload = new LinkedHashMap<>(spec);
        payload.put("space_id", spaceId);
        payload.put("status", status);
        payload.put("created_at", createdAt);
        payload.put("updated_at", updatedAt);
        payload.put("cloudsim_runtime_id", stringValue(spec.getOrDefault("cloudsim_runtime_id", "cloudsim-" + spaceId), "cloudsim-" + spaceId));
        payload.put("cloudsim", new LinkedHashMap<>(Map.of(
                "summary", new LinkedHashMap<>(lastSummary),
                "events", new ArrayList<>(events),
                "last_tick", stringValue(lastSummary.getOrDefault("last_tick", ""), "")
        )));
        payload.put("hosts", intValue(lastSummary.getOrDefault("hosts", 0)));
        payload.put("vms", intValue(lastSummary.getOrDefault("vms", 0)));
        payload.put("cloudlets", intValue(lastSummary.getOrDefault("cloudlets", 0)));
        payload.put("finished_cloudlets", intValue(lastSummary.getOrDefault("finished_cloudlets", 0)));
        payload.put("events", new ArrayList<>(events));
        return payload;
    }

    public synchronized Map<String, Object> persistedState() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("snapshot", snapshot());
        payload.put("last_summary", new LinkedHashMap<>(lastSummary));
        payload.put("events", new ArrayList<>(events));
        payload.put("status", status);
        payload.put("created_at", createdAt);
        payload.put("updated_at", updatedAt);
        return payload;
    }

    @SuppressWarnings("unchecked")
    public synchronized void restoreState(Map<String, Object> payload) {
        if (payload == null) {
            return;
        }
        Map<String, Object> snapshot = payload.get("snapshot") instanceof Map
                ? new LinkedHashMap<>((Map<String, Object>) payload.get("snapshot"))
                : new LinkedHashMap<>();
        if (snapshot.isEmpty()) {
            snapshot.putAll(payload);
        }
        spec.clear();
        spec.putAll(snapshot);
        spec.putIfAbsent("space_id", spaceId);
        status = stringValue(payload.getOrDefault("status", snapshot.getOrDefault("status", status)), status).toLowerCase(Locale.ROOT);
        createdAt = stringValue(payload.getOrDefault("created_at", snapshot.getOrDefault("created_at", createdAt)), createdAt);
        updatedAt = stringValue(payload.getOrDefault("updated_at", snapshot.getOrDefault("updated_at", updatedAt)), updatedAt);

        lastSummary = new LinkedHashMap<>();
        Object summary = payload.get("last_summary");
        if (summary instanceof Map<?, ?> summaryMap) {
            for (Map.Entry<?, ?> entry : summaryMap.entrySet()) {
                if (entry.getKey() != null) {
                    lastSummary.put(String.valueOf(entry.getKey()), entry.getValue());
                }
            }
        } else {
            Object cloudsim = snapshot.get("cloudsim");
            if (cloudsim instanceof Map<?, ?> cloudsimMap) {
                Object nestedSummary = cloudsimMap.get("summary");
                if (nestedSummary instanceof Map<?, ?> nestedSummaryMap) {
                    for (Map.Entry<?, ?> entry : nestedSummaryMap.entrySet()) {
                        if (entry.getKey() != null) {
                            lastSummary.put(String.valueOf(entry.getKey()), entry.getValue());
                        }
                    }
                }
            }
        }

        events.clear();
        Object eventsPayload = payload.get("events");
        if (eventsPayload instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> itemMap) {
                    Map<String, Object> event = new LinkedHashMap<>();
                    for (Map.Entry<?, ?> entry : itemMap.entrySet()) {
                        if (entry.getKey() != null) {
                            event.put(String.valueOf(entry.getKey()), entry.getValue());
                        }
                    }
                    events.add(event);
                }
            }
        } else {
            Object cloudsim = snapshot.get("cloudsim");
            if (cloudsim instanceof Map<?, ?> cloudsimMap) {
                Object nestedEvents = cloudsimMap.get("events");
                if (nestedEvents instanceof List<?> list) {
                    for (Object item : list) {
                        if (item instanceof Map<?, ?> itemMap) {
                            Map<String, Object> event = new LinkedHashMap<>();
                            for (Map.Entry<?, ?> entry : itemMap.entrySet()) {
                                if (entry.getKey() != null) {
                                    event.put(String.valueOf(entry.getKey()), entry.getValue());
                                }
                            }
                            events.add(event);
                        }
                    }
                }
            }
        }
    }

    public synchronized Map<String, Object> eventsPayload() {
        return Map.of(
                "space_id", spaceId,
                "events", new ArrayList<>(events),
                "count", events.size()
        );
    }

    private List<org.cloudsimplus.hosts.Host> buildHosts(int hostCount, int hostPes, long hostRamMb) {
        List<org.cloudsimplus.hosts.Host> hosts = new ArrayList<>();
        long bw = 100000L;
        long storage = 1_000_000L;  // 1 TB local storage
        for (int i = 0; i < hostCount; i++) {
            List<org.cloudsimplus.resources.Pe> pes = new ArrayList<>();
            for (int j = 0; j < hostPes; j++) {
                pes.add(new PeSimple(10000));
            }
            hosts.add(new HostSimple(hostRamMb, bw, storage, pes));
        }
        return hosts;
    }

    private List<org.cloudsimplus.vms.Vm> buildVms(int vmCount) {
        List<org.cloudsimplus.vms.Vm> vms = new ArrayList<>();
        for (int i = 0; i < vmCount; i++) {
            VmSimple vm = new VmSimple(1000 + ((i % 4) * 250), 1 + (i % 2));
            vm.setRam(1024 + ((i % 4) * 256L)).setBw(1000).setSize(10000);
            vms.add(vm);
        }
        return vms;
    }

    private List<org.cloudsimplus.cloudlets.Cloudlet> buildCloudlets(int cloudletCount) {
        List<org.cloudsimplus.cloudlets.Cloudlet> cloudlets = new ArrayList<>();
        UtilizationModelDynamic util = new UtilizationModelDynamic(0.5);
        for (int i = 0; i < cloudletCount; i++) {
            cloudlets.add(new CloudletSimple(5000 + (i * 250L), 1, util));
        }
        return cloudlets;
    }

    private Map<String, Object> event(String type, Map<String, Object> detail) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event", type);
        payload.put("space_id", spaceId);
        payload.put("at", Instant.now().toString());
        payload.put("detail", detail);
        return payload;
    }

    private static String stringValue(Object value, String fallback) {
        return value == null ? fallback : String.valueOf(value);
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (Exception e) {
            return 0;
        }
    }

    private static long longValue(Object value, long fallback) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (Exception e) {
            return fallback;
        }
    }
}
