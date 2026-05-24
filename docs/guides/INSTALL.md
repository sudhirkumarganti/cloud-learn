# CloudLearn Installation

## Single Launcher

CloudLearn now ships as a single appliance launcher.

Start the platform with:

```bash
bash ./scripts/cloud-learn up
```

Or on Windows:

```powershell
.\scripts\cloud-learn.ps1 up
```

This launches one Multipass VM appliance and starts the full CloudLearn stack inside that VM.

## Install Matrix

| Distribution | Install command | Runtime boundary | Host dependency |
|---|---|---|---|
| Homebrew | `brew install cloud-learn` | Multipass VM appliance | Multipass |
| Snap | Install the snap package | Multipass VM appliance | Multipass |
| MSI / winget | Install the Windows package | Multipass VM appliance | Multipass |
| Source checkout | `bash ./scripts/cloud-learn up` | Multipass VM appliance | Multipass |

## What Runs Inside the VM

- simulator UI/API
- CloudSim backbone
- provider emulators
- runtime bridge
- persistent state
- EC2-like sandboxes

## Notes

- There is no separate developer launcher path anymore.
- The appliance stack is isolated in [`docker-compose.appliance.yml`](/Users/sudhirganti/Applications/simulator/cloud-learn/docker-compose.appliance.yml).
- Use `stop` for a clean shutdown, `force-stop` for a hard stop, and `kill` as the shortcut alias for hard stop.
- On `up`, the launcher will try to start Multipass automatically if the host daemon/socket is not reachable yet.
- The recommended workflow is:
  1. Install.
  2. Run the single launcher.
  3. Open the browser.
  4. Build resources locally.
  5. Export Terraform.
  6. Deploy when ready.
