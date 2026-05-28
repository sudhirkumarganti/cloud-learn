// Real Azure SDK conformance harness against the CloudLearn simulator.
//
// Proves unmodified azure-sdk-for-go clients talk to the sim:
//   - custom cloud.Configuration points ResourceManager at the sim base
//   - a fake TokenCredential + InsecureAllowCredentialWithHTTP allow the
//     bearer-token policy to run over plain HTTP (the sim ignores the token)
//   - armstorage BeginCreate exercises the real Azure-AsyncOperation LRO poller
//   - azblob (SharedKey) exercises the real Blob data plane (containers + bytes)
//
// Run (dockerized, on the appliance):
//   docker run --rm --network host -e ENDPOINT=http://127.0.0.1:9000 \
//     -e SUB=00000000-0000-0000-0000-cloudlearn01 -e GOFLAGS=-mod=mod \
//     -v $PWD:/app -w /app golang:1.22 sh -c "go mod tidy && go run ."
package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/arm"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/cloud"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/to"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/compute/armcompute/v5"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/resources/armresources"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/storage/armstorage"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
)

type fakeCred struct{}

func (fakeCred) GetToken(_ context.Context, _ policy.TokenRequestOptions) (azcore.AccessToken, error) {
	return azcore.AccessToken{Token: "fake-token", ExpiresOn: time.Now().Add(time.Hour)}, nil
}

var pass, fail int

func check(name string, err error) {
	if err != nil {
		fail++
		fmt.Printf("FAIL  %s: %v\n", name, err)
	} else {
		pass++
		fmt.Printf("PASS  %s\n", name)
	}
}

func main() {
	ep := os.Getenv("ENDPOINT")
	sub := os.Getenv("SUB")
	if ep == "" {
		ep = "http://127.0.0.1:9000"
	}
	if sub == "" {
		sub = "00000000-0000-0000-0000-cloudlearn01"
	}
	rg := "cloudlearn-rg"
	ctx := context.Background()

	cloudCfg := cloud.Configuration{
		ActiveDirectoryAuthorityHost: ep,
		Services: map[cloud.ServiceName]cloud.ServiceConfiguration{
			cloud.ResourceManager: {Endpoint: ep, Audience: ep},
		},
	}
	opts := &arm.ClientOptions{ClientOptions: azcore.ClientOptions{
		Cloud:                           cloudCfg,
		InsecureAllowCredentialWithHTTP: true,
	}}
	cred := fakeCred{}

	// 1. Resource groups (control plane + auth-over-HTTP).
	if rgc, err := armresources.NewResourceGroupsClient(sub, cred, opts); err == nil {
		_, err = rgc.NewListPager(nil).NextPage(ctx)
		check("armresources list resource groups", err)
	} else {
		check("armresources client", err)
	}

	acct := "stgoconf01"
	sac, err := armstorage.NewAccountsClient(sub, cred, opts)
	check("armstorage client", err)
	if err == nil {
		// 2. Storage account create — exercises the Azure-AsyncOperation LRO poller.
		poller, perr := sac.BeginCreate(ctx, rg, acct, armstorage.AccountCreateParameters{
			Location: to.Ptr("eastus"),
			SKU:      &armstorage.SKU{Name: to.Ptr(armstorage.SKUNameStandardLRS)},
			Kind:     to.Ptr(armstorage.KindStorageV2),
		}, nil)
		if perr == nil {
			_, perr = poller.PollUntilDone(ctx, nil)
		}
		check("armstorage BeginCreate + LRO poll", perr)

		// 3. Get + List.
		_, gerr := sac.GetProperties(ctx, rg, acct, nil)
		check("armstorage GetProperties", gerr)
		_, lerr := sac.NewListByResourceGroupPager(rg, nil).NextPage(ctx)
		check("armstorage list by resource group", lerr)

		// 4. Keys (POST action) — needed for the data-plane SharedKey.
		key := ""
		keys, kerr := sac.ListKeys(ctx, rg, acct, nil)
		if kerr == nil && len(keys.Keys) > 0 && keys.Keys[0].Value != nil {
			key = *keys.Keys[0].Value
		}
		check("armstorage ListKeys", kerr)

		// 5. Blob data plane (real bytes) via SharedKey over HTTP.
		if key != "" {
			runBlob(ctx, ep, acct, key)
		}

		// 6. Delete (sync or poller — header-less terminal status).
		_, derr := sac.Delete(ctx, rg, acct, nil)
		check("armstorage Delete", derr)
	}

	// 7. Compute list.
	if vmc, err := armcompute.NewVirtualMachinesClient(sub, cred, opts); err == nil {
		_, err = vmc.NewListPager(rg, nil).NextPage(ctx)
		check("armcompute list virtual machines", err)
	} else {
		check("armcompute client", err)
	}

	fmt.Printf("\nRESULT  pass=%d fail=%d\n", pass, fail)
	if fail > 0 {
		os.Exit(1)
	}
}

func runBlob(ctx context.Context, ep, acct, key string) {
	skc, err := azblob.NewSharedKeyCredential(acct, key)
	check("azblob shared-key credential", err)
	if err != nil {
		return
	}
	svc, err := azblob.NewClientWithSharedKeyCredential(ep+"/azure-data/blob/"+acct+"/", skc, nil)
	check("azblob client", err)
	if err != nil {
		return
	}
	_, err = svc.CreateContainer(ctx, "data", nil)
	if err != nil && strings.Contains(err.Error(), "ContainerAlreadyExists") {
		err = nil // idempotent re-run
	}
	check("azblob create container", err)
	defer func() { _, _ = svc.DeleteContainer(ctx, "data", nil) }()

	payload := []byte("hello from the real azure go sdk")
	_, err = svc.UploadBuffer(ctx, "data", "greeting.txt", payload, nil)
	check("azblob upload blob", err)

	dl, err := svc.DownloadStream(ctx, "data", "greeting.txt", nil)
	if err == nil {
		var buf bytes.Buffer
		_, _ = io.Copy(&buf, dl.Body)
		_ = dl.Body.Close()
		if !bytes.Equal(buf.Bytes(), payload) {
			err = fmt.Errorf("round-trip mismatch: got %q", buf.String())
		}
	}
	check("azblob download + verify bytes", err)

	_, err = svc.DeleteBlob(ctx, "data", "greeting.txt", nil)
	check("azblob delete blob", err)
}
