package cloudlearn;

import com.azure.core.http.HttpClient;
import com.azure.core.http.HttpPipeline;
import com.azure.core.http.HttpPipelineBuilder;
import com.azure.core.http.policy.HttpLogDetailLevel;
import com.azure.core.http.policy.HttpLoggingPolicy;
import com.azure.core.http.policy.HttpLogOptions;
import com.azure.core.http.policy.RetryPolicy;
import com.azure.core.management.AzureEnvironment;
import com.azure.core.management.profile.AzureProfile;
import com.azure.resourcemanager.storage.StorageManager;
import com.azure.resourcemanager.storage.models.Kind;
import com.azure.resourcemanager.storage.models.SkuName;
import com.azure.resourcemanager.storage.models.StorageAccount;
import com.azure.resourcemanager.storage.models.StorageAccountSkuType;

import java.util.HashMap;
import java.util.Map;

/**
 * Real Azure Java SDK (azure-resourcemanager) conformance against the CloudLearn
 * simulator. The bearer-token policy refuses to run over plain HTTP, so we build
 * a custom HttpPipeline WITHOUT an auth policy (the sim ignores credentials) and
 * authenticate the fluent manager with it + a custom AzureEnvironment whose ARM
 * endpoint points at the simulator. Storage account create exercises the real
 * Java LRO poller.
 *
 * Run on the host (Java 17 + Maven):
 *   ENDPOINT=http://192.168.252.7:9000 SUB=00000000-0000-0000-0000-cloudlearn01 \
 *     mvn -q -B compile exec:java
 */
public class AzureConformance {
    static int pass = 0, fail = 0;

    static void check(String name, Runnable r) {
        try {
            r.run();
            pass++;
            System.out.println("PASS  " + name);
        } catch (Throwable t) {
            fail++;
            System.out.println("FAIL  " + name + ": " + t.getMessage());
        }
    }

    public static void main(String[] args) {
        String endpoint = System.getenv().getOrDefault("ENDPOINT", "http://192.168.252.7:9000");
        String sub = System.getenv().getOrDefault("SUB", "00000000-0000-0000-0000-cloudlearn01");
        String rg = "cloudlearn-rg";
        String account = "stjavaconf01";

        Map<String, String> endpoints = new HashMap<>();
        endpoints.put("resourceManagerEndpointUrl", endpoint + "/");
        endpoints.put("managementEndpointUrl", endpoint + "/");
        endpoints.put("activeDirectoryEndpointUrl", endpoint + "/");
        endpoints.put("activeDirectoryResourceId", endpoint + "/");
        endpoints.put("activeDirectoryGraphResourceId", endpoint + "/");
        endpoints.put("microsoftGraphResourceId", endpoint + "/");
        endpoints.put("galleryEndpointUrl", endpoint + "/");
        endpoints.put("storageEndpointSuffix", "core.windows.net");
        endpoints.put("keyVaultDnsSuffix", "vault.azure.net");
        endpoints.put("sqlServerHostnameSuffix", "database.windows.net");
        endpoints.put("azureDataLakeStoreFileSystemEndpointSuffix", "azuredatalakestore.net");
        endpoints.put("azureDataLakeAnalyticsCatalogAndJobEndpointSuffix", "azuredatalakeanalytics.net");
        AzureEnvironment env = new AzureEnvironment(endpoints);
        AzureProfile profile = new AzureProfile("cloudlearn-tenant", sub, env);

        // No BearerTokenAuthenticationPolicy -> works over http; sim ignores auth.
        HttpPipeline pipeline = new HttpPipelineBuilder()
                .httpClient(HttpClient.createDefault())
                .policies(new RetryPolicy(),
                          new HttpLoggingPolicy(new HttpLogOptions().setLogLevel(HttpLogDetailLevel.NONE)))
                .build();

        StorageManager manager = StorageManager.authenticate(pipeline, profile);

        // 1. Create storage account — exercises the Java LRO poller.
        check("storage account create (LRO)", () -> {
            manager.storageAccounts().define(account)
                    .withRegion("eastus")
                    .withExistingResourceGroup(rg)
                    .withSku(StorageAccountSkuType.STANDARD_LRS)
                    .withGeneralPurposeAccountKindV2()
                    .create();
        });

        // 2. Get by resource group.
        check("storage account get", () -> {
            StorageAccount sa = manager.storageAccounts().getByResourceGroup(rg, account);
            if (sa == null || !account.equals(sa.name())) throw new RuntimeException("unexpected get result");
        });

        // 3. List by resource group.
        check("storage account list", () -> {
            long n = manager.storageAccounts().listByResourceGroup(rg).stream().count();
            if (n < 1) throw new RuntimeException("empty list");
        });

        // 4. Keys (POST action).
        check("storage account list keys", () -> {
            int n = manager.storageAccounts().getByResourceGroup(rg, account).getKeys().size();
            if (n < 1) throw new RuntimeException("no keys");
        });

        // 5. Delete.
        check("storage account delete", () -> {
            manager.storageAccounts().deleteByResourceGroup(rg, account);
        });

        System.out.println("\nRESULT  pass=" + pass + " fail=" + fail);
        if (fail > 0) System.exit(1);
    }
}
