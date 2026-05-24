#!/usr/bin/env pwsh
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$RemainingArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = if ($env:CLOUD_LEARN_HOME) { (Resolve-Path $env:CLOUD_LEARN_HOME).Path } else { (Resolve-Path (Join-Path $ScriptPath '..')).Path }
$ProjectName = if ($env:CLOUD_LEARN_PROJECT_NAME) { $env:CLOUD_LEARN_PROJECT_NAME } else { 'cloud-learn' }
$ComposeFile = if ($env:CLOUD_LEARN_COMPOSE_FILE) { $env:CLOUD_LEARN_COMPOSE_FILE } else { Join-Path $RootDir 'docker-compose.appliance.yml' }
$ParentOs = 'windows'
$DistributionMode = 'appliance'
$RuntimeContext = if ($env:CLOUD_LEARN_RUNTIME_CONTEXT) { $env:CLOUD_LEARN_RUNTIME_CONTEXT } else { 'outer' }
$ApplianceName = if ($env:CLOUD_LEARN_APPLIANCE_NAME) { $env:CLOUD_LEARN_APPLIANCE_NAME } else { 'cloudlearn-appliance' }
$ApplianceDir = if ($env:CLOUD_LEARN_APPLIANCE_DIR) { $env:CLOUD_LEARN_APPLIANCE_DIR } else { Join-Path $RootDir '.cloudlearn-appliance' }
$ApplianceImage = if ($env:CLOUD_LEARN_APPLIANCE_IMAGE) { $env:CLOUD_LEARN_APPLIANCE_IMAGE } else { '24.04' }
$ApplianceCpus = if ($env:CLOUD_LEARN_APPLIANCE_CPUS) { [int]$env:CLOUD_LEARN_APPLIANCE_CPUS } else { 4 }
$ApplianceMemory = if ($env:CLOUD_LEARN_APPLIANCE_MEMORY) { $env:CLOUD_LEARN_APPLIANCE_MEMORY } else { '8G' }
$ApplianceDisk = if ($env:CLOUD_LEARN_APPLIANCE_DISK) { $env:CLOUD_LEARN_APPLIANCE_DISK } else { '32G' }
$ApplianceWorkspace = if ($env:CLOUD_LEARN_APPLIANCE_WORKSPACE) { $env:CLOUD_LEARN_APPLIANCE_WORKSPACE } else { '/workspace/cloud-learn' }
$HostSizingFileName = 'host-sizing-report.json'

switch ($RuntimeContext.ToLowerInvariant()) {
  'outer' { $RuntimeContext = 'outer' }
  'inner' { $RuntimeContext = 'inner' }
  default { $RuntimeContext = 'outer' }
}

if ($RuntimeContext -eq 'inner' -and -not $env:CLOUD_LEARN_COMPOSE_FILE) {
  $ComposeFile = Join-Path $RootDir 'docker-compose.appliance.yml'
}

$env:CLOUDLEARN_DISTRIBUTION_MODE = $DistributionMode
if ($RuntimeContext -eq 'inner') {
  $env:CLOUD_LEARN_RUNTIME_CONTEXT = 'inner'
} else {
  $env:CLOUD_LEARN_RUNTIME_CONTEXT = 'outer'
}

function Write-ApplianceManifest {
  if (-not (Test-Path $ApplianceDir)) {
    New-Item -ItemType Directory -Force -Path $ApplianceDir | Out-Null
  }
  $payload = [ordered]@{
    name = $ApplianceName
    image = $ApplianceImage
    cpus = $ApplianceCpus
    memory = $ApplianceMemory
    disk = $ApplianceDisk
    workspace = $ApplianceWorkspace
    host_os = $ParentOs
    distribution_mode = $DistributionMode
    created_at = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.000Z")
  }
  $json = $payload | ConvertTo-Json -Depth 6
  Set-Content -Path (Join-Path $ApplianceDir 'appliance-bootstrap.json') -Value ($json + [Environment]::NewLine) -Encoding utf8
}

function Get-ApplianceSshPublicKey {
  $privateKey = Join-Path $env:USERPROFILE '.ssh/cloudlearn_multipass_ed25519'
  $publicKey = "$privateKey.pub"
  if (-not (Test-Path $privateKey) -or -not (Test-Path $publicKey)) {
    $sshDir = Split-Path -Parent $privateKey
    if (-not (Test-Path $sshDir)) {
      New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    }
    try {
      & ssh-keygen -t ed25519 -N '' -f $privateKey -C 'cloudlearn' | Out-Null
    } catch {
    }
  }
  if (Test-Path $publicKey) {
    return (Get-Content -Path $publicKey -Raw).Trim()
  }
  return ''
}

function Write-ApplianceHostSizing {
  if (-not (Test-Path $ApplianceDir)) {
    New-Item -ItemType Directory -Force -Path $ApplianceDir | Out-Null
  }
  $driveRoot = (Get-Item -LiteralPath $RootDir).PSDrive.Root
  $driveInfo = [System.IO.DriveInfo]::new($driveRoot)
  $cpuCount = [Environment]::ProcessorCount
  $memoryBytes = 0
  try {
    $memoryBytes = [int64]((Get-CimInstance -ClassName Win32_ComputerSystem).TotalPhysicalMemory)
  } catch {
    $memoryBytes = 0
  }
  $memoryGib = [Math]::Round($memoryBytes / 1GB, 1)
  $totalBytes = [int64]$driveInfo.TotalSize
  $freeBytes = [int64]$driveInfo.AvailableFreeSpace
  $usedBytes = $totalBytes - $freeBytes
  $totalGib = [Math]::Round($totalBytes / 1GB, 1)
  $freeGib = [Math]::Round($freeBytes / 1GB, 1)
  if ($memoryGib -le 4) {
    $applianceMemory = 2
    $applianceDisk = 24
  } elseif ($memoryGib -le 8) {
    $applianceMemory = 4
    $applianceDisk = 32
  } elseif ($memoryGib -le 16) {
    $applianceMemory = 8
    $applianceDisk = 32
  } elseif ($memoryGib -le 32) {
    $applianceMemory = 12
    $applianceDisk = 48
  } elseif ($memoryGib -le 64) {
    $applianceMemory = 16
    $applianceDisk = 64
  } else {
    $applianceMemory = [Math]::Min(24, [Math]::Max(16, [int][Math]::Round($memoryGib * 0.25)))
    $applianceDisk = [Math]::Min(96, [Math]::Max(64, [int][Math]::Round($totalGib * 0.12)))
  }
  $applianceCpus = [Math]::Max(1, [Math]::Min([Math]::Max($cpuCount - 1, 1), [int][Math]::Round($applianceMemory / 2)))
  $applianceDisk = [int][Math]::Min([Math]::Max($applianceDisk, 24), [Math]::Max(24, [int][Math]::Round($freeGib * 0.25)))
  $reserve = if ($memoryGib -le 8) { 1.5 } elseif ($memoryGib -le 16) { 2.0 } elseif ($memoryGib -le 32) { 2.5 } else { 3.0 }
  $available = [Math]::Max(0.0, [double]$applianceMemory - $reserve)
  $networkInterfaces = @([System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() | Where-Object { $_.Name -and $_.Name.Trim() -ne '' } | ForEach-Object { $_.Name })
  $payload = [ordered]@{
    source = 'launcher'
    host_os = $ParentOs
    cpu_count = $cpuCount
    memory_bytes = $memoryBytes
    memory_gib = $memoryGib
    disk_total_bytes = $totalBytes
    disk_used_bytes = $usedBytes
    disk_free_bytes = $freeBytes
    disk_total_gib = $totalGib
    disk_free_gib = $freeGib
    network_interfaces = $networkInterfaces
    network_interface_count = $networkInterfaces.Count
    recommended = [ordered]@{
      appliance = [ordered]@{
        vcpus = $applianceCpus
        memory_gib = $applianceMemory
        disk_gib = $applianceDisk
      }
      lxd_budget = [ordered]@{
        platform_reserve_gib = $reserve
        small_instances = [int]([Math]::Floor($available / 0.5))
        medium_instances = [int]([Math]::Floor($available / 1.0))
        heavy_instances = [int]([Math]::Floor($available / 2.0))
      }
    }
    warnings = @()
    checked_at = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.000Z")
  }
  if ($cpuCount -lt 4 -or $memoryGib -lt 8) {
    $payload.warnings = @('This host is small for a full appliance. Keep the VM at minimum size and avoid heavy sandboxes.')
  }
  $json = $payload | ConvertTo-Json -Depth 8
  Set-Content -Path (Join-Path $ApplianceDir $HostSizingFileName) -Value ($json + [Environment]::NewLine) -Encoding utf8
}

function Sync-ApplianceHostSizingIntoVm {
  $compose = Get-MultipassCommand
  $sourcePath = Join-Path $ApplianceWorkspace ('.cloudlearn-appliance/' + $HostSizingFileName)
  Write-ProgressLine '==> Appliance: syncing host sizing into VM-local storage'
  & $compose exec $ApplianceName -- /bin/bash -lc "sudo mkdir -p /var/lib/cloudlearn && sudo install -m 644 '$sourcePath' /var/lib/cloudlearn/$HostSizingFileName"
}

function Write-ApplianceCloudInit {
  if (-not (Test-Path $ApplianceDir)) {
    New-Item -ItemType Directory -Force -Path $ApplianceDir | Out-Null
  }
  $publicKey = Get-ApplianceSshPublicKey
  $sshKeys = ''
  if (-not [string]::IsNullOrWhiteSpace($publicKey)) {
    $sshKeys = "ssh_authorized_keys:`n  - $publicKey`n"
  }
  @"
#cloud-config
package_update: true
package_upgrade: true
$sshKeys
packages:
  - python3
  - python3-pip
  - curl
  - ca-certificates
  - docker.io
  - docker-compose-v2
runcmd:
  - [ bash, -lc, "systemctl enable --now docker" ]
  - [ bash, -lc, "usermod -aG docker ubuntu || true" ]
  - [ bash, -lc, "update-alternatives --set docker-compose /usr/libexec/docker/cli-plugins/docker-compose || true" ]
  - [ bash, -lc, "snap install lxd || true" ]
  - [ bash, -lc, "usermod -aG lxd ubuntu || true" ]
  - [ bash, -lc, "cat >/tmp/cloudlearn-lxd-preseed.yaml <<'EOF'\nconfig: {}\nnetworks:\n- name: lxdbr0\n  type: bridge\n  config:\n    ipv4.address: auto\n    ipv4.nat: \"true\"\n    ipv6.address: auto\n    ipv6.nat: \"true\"\nstorage_pools:\n- name: default\n  driver: dir\nprofiles:\n- name: default\n  description: Default LXD profile\n  config: {}\n  devices:\n    root:\n      type: disk\n      pool: default\n      path: /\n    eth0:\n      type: nic\n      network: lxdbr0\n      name: eth0\nEOF\nlxd init --preseed < /tmp/cloudlearn-lxd-preseed.yaml || true" ]
  - [ bash, -lc, "mkdir -p ${ApplianceWorkspace}" ]
  - [ bash, -lc, "sudo mkdir -p /var/lib/cloudlearn/deployments" ]
"@ | Set-Content -Path (Join-Path $ApplianceDir 'cloud-init.yaml') -Encoding utf8
}

function Write-ProgressLine {
  param([Parameter(Mandatory = $true)][string]$Message)
  Write-Output $Message
}

function Get-MultipassCommand {
  if (Get-Command multipass -ErrorAction SilentlyContinue) {
    return 'multipass'
  }
  throw 'Multipass is required for appliance mode'
}

function Start-MultipassHost {
  if ($ParentOs -eq 'windows') {
    try {
      $services = Get-Service -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match 'multipass' -or $_.DisplayName -match 'Multipass'
      }
      foreach ($service in $services) {
        if ($service.Status -ne 'Running') {
          Start-Service -InputObject $service -ErrorAction SilentlyContinue
        }
      }
    } catch {
    }
    try {
      Start-Process -FilePath 'multipass' -ErrorAction SilentlyContinue | Out-Null
    } catch {
    }
  }
}

function Test-MultipassReady {
  param(
    [int]$TimeoutSeconds = 8
  )

  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
  $attempted = $false
  $started = [DateTime]::UtcNow
  while ([DateTime]::UtcNow -lt $deadline) {
    Write-ProgressLine '==> Multipass: probing daemon/socket'
    try {
      $compose = Get-MultipassCommand
      & $compose list --format json | Out-Null
      return $true
    } catch {
      if (-not $attempted) {
        Write-ProgressLine '==> Multipass: daemon/socket not reachable, attempting host auto-start'
        Start-MultipassHost
        $attempted = $true
      }
      Start-Sleep -Seconds 3
      $elapsed = [int](([DateTime]::UtcNow - $started).TotalSeconds)
      Write-ProgressLine ("==> Multipass: waiting for daemon/socket ({0}s)" -f $elapsed)
    }
  }
  return $false
}

function Get-ComposeBackend {
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    try {
      & docker compose version | Out-Null
      return @{ File = 'docker'; Args = @('compose') }
    } catch {
    }
  }
  if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    return @{ File = 'docker-compose'; Args = @() }
  }
  throw 'docker compose is not available'
}

function Test-ComposeEngine {
  try {
    & docker info | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Start-ApplianceRuntimeBridge {
  $compose = Get-MultipassCommand
  $bridgeScript = Join-Path $ApplianceWorkspace 'core/runtime_bridge.py'
  Write-ProgressLine '==> Appliance: starting VM-local runtime bridge'
  & $compose exec $ApplianceName -- /bin/bash -lc "set -e; if curl -fsS http://127.0.0.1:9171/health >/dev/null 2>&1; then exit 0; fi; nohup python3 `"$bridgeScript`" --host 0.0.0.0 --port 9171 >/tmp/cloudlearn-runtime-bridge.log 2>&1 & for i in \$(seq 1 30); do if curl -fsS http://127.0.0.1:9171/health >/dev/null 2>&1; then exit 0; fi; sleep 1; done; echo 'runtime bridge failed to start' >&2; exit 1"
}

function Wait-ComposeBackendReady {
  param(
    [int]$TimeoutSeconds = 180
  )

  $waited = 0
  while ($waited -lt $TimeoutSeconds) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
      try {
        & docker compose version | Out-Null
        & docker info | Out-Null
        return $true
      } catch {
      }
    }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
      try {
        & docker-compose version | Out-Null
        & docker info | Out-Null
        return $true
      } catch {
      }
    }
    Start-Sleep -Seconds 2
    $waited += 2
  }

  throw 'docker compose is not available inside the appliance VM yet'
}

function Write-Doctor {
  Write-Output "cloud-learn root: $RootDir"
  Write-Output "compose file: $ComposeFile"
  Write-Output "runtime context: $RuntimeContext"
  if ($RuntimeContext -eq 'inner') {
    Write-Output ("docker: " + ($(if (Get-Command docker -ErrorAction SilentlyContinue) { 'available' } else { 'missing' })))
    $composeAvailable = 'missing'
    try {
      Get-ComposeBackend | Out-Null
      $composeAvailable = 'available'
    } catch {
    }
    Write-Output ("compose: " + $composeAvailable)
    Write-Output ("engine: " + ($(if (Test-ComposeEngine) { 'reachable' } else { 'unreachable' })))
    Write-Output 'mode: appliance inner stack'
  } else {
    Write-Output ("multipass: " + ($(if (Get-Command multipass -ErrorAction SilentlyContinue) { 'available' } else { 'missing' })))
    Write-Output 'mode: appliance launcher'
  }
  Write-Output "distribution mode: $DistributionMode"
}

function Get-ApplianceState {
  try {
    $compose = Get-MultipassCommand
    $payload = & $compose list --format json | ConvertFrom-Json
    function Find-InstanceState {
      param(
        [Parameter(Mandatory = $true)]$Node
      )
      if ($null -eq $Node) {
        return ''
      }
      if ($Node -is [System.Collections.IDictionary]) {
        if ($Node.Contains('name') -and $Node['name'] -eq $ApplianceName) {
          $stateValue = ''
          if ($Node.Contains('state') -and $null -ne $Node['state'] -and $Node['state'].ToString().Trim() -ne '') {
            $stateValue = $Node['state'].ToString()
          } elseif ($Node.Contains('status') -and $null -ne $Node['status'] -and $Node['status'].ToString().Trim() -ne '') {
            $stateValue = $Node['status'].ToString()
          }
          return $stateValue.ToLowerInvariant()
        }
        foreach ($entry in $Node.GetEnumerator()) {
          $found = Find-InstanceState -Node $entry.Value
          if (-not [string]::IsNullOrWhiteSpace($found)) {
            return $found
          }
        }
      } elseif ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
        foreach ($item in $Node) {
          $found = Find-InstanceState -Node $item
          if (-not [string]::IsNullOrWhiteSpace($found)) {
            return $found
          }
        }
      }
      return ''
    }
    return Find-InstanceState -Node $payload
  } catch {
  }
  return ''
}

function Test-ApplianceExists {
  try {
    $compose = Get-MultipassCommand
    $payload = & $compose list --format json | ConvertFrom-Json
    function Find-Instance {
      param(
        [Parameter(Mandatory = $true)]$Node
      )
      if ($null -eq $Node) {
        return $false
      }
      if ($Node -is [System.Collections.IDictionary]) {
        if ($Node.Contains('name') -and $Node['name'] -eq $ApplianceName) {
          return $true
        }
        foreach ($entry in $Node.GetEnumerator()) {
          if (Find-Instance -Node $entry.Value) {
            return $true
          }
        }
      } elseif ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
        foreach ($item in $Node) {
          if (Find-Instance -Node $item) {
            return $true
          }
        }
      }
      return $false
    }
    return Find-Instance -Node $payload
  } catch {
    return $false
  }
}

function Start-ApplianceVm {
  Write-ApplianceManifest
  Write-ApplianceHostSizing
  Write-ApplianceCloudInit
  $compose = Get-MultipassCommand
  if (-not (Test-MultipassReady)) {
    throw 'Multipass is installed, but the daemon/socket is not reachable. Open or restart Multipass on the host and retry.'
  }
  Write-ProgressLine '==> Appliance: checking VM state'
  $state = Get-ApplianceState
  $exists = Test-ApplianceExists
  if (-not $exists) {
    Write-ProgressLine ("==> Appliance: launching Multipass VM {0}" -f $ApplianceName)
    & $compose launch $ApplianceImage --name $ApplianceName --cpus $ApplianceCpus --memory $ApplianceMemory --disk $ApplianceDisk --cloud-init (Join-Path $ApplianceDir 'cloud-init.yaml')
  } elseif ($state -eq 'running') {
    Write-ProgressLine ("==> Appliance: existing VM detected ({0})" -f $state)
  } elseif ($state -eq 'stopped' -or $state -eq 'suspended') {
    Write-ProgressLine ("==> Appliance: existing VM detected ({0}), starting it" -f $state)
    & $compose start $ApplianceName
  }
  else {
    Write-ProgressLine ("==> Appliance: existing VM detected ({0}), skipping start and continuing" -f ($(if ([string]::IsNullOrWhiteSpace($state)) { 'unknown' } else { $state })))
  }
  try {
    Write-ProgressLine '==> Appliance: mounting workspace into VM'
    & $compose mount $RootDir "$ApplianceName`:$ApplianceWorkspace" | Out-Null
  } catch {
  }
  try {
    Sync-ApplianceHostSizingIntoVm
  } catch {
  }
  try {
    Write-ProgressLine '==> Appliance: waiting for cloud-init'
    & $compose exec $ApplianceName -- /bin/bash -lc "cloud-init status --wait >/dev/null 2>&1 || true" | Out-Null
  } catch {
  }
}

function Invoke-ApplianceLauncher {
  $compose = Get-MultipassCommand
  Write-ProgressLine '==> Appliance: starting inner CloudLearn stack'
  & $compose exec $ApplianceName -- /bin/bash -lc "sudo mkdir -p /var/lib/cloudlearn/deployments && cd $ApplianceWorkspace && CLOUD_LEARN_HOME=$ApplianceWorkspace CLOUD_LEARN_RUNTIME_CONTEXT=inner CLOUD_LEARN_DISTRIBUTION_MODE=appliance CLOUD_LEARN_COMPOSE_FILE=$ApplianceWorkspace/docker-compose.appliance.yml bash ./scripts/cloud-learn up --detach"
}

function Test-ApplianceHealth {
  $compose = Get-MultipassCommand
  $waited = 0
  while ($waited -lt 60) {
    if ($waited % 10 -eq 0) {
      Write-ProgressLine ("==> Appliance: waiting for simulator and CloudSim to become reachable ({0}s)" -f $waited)
    }
    try {
      & $compose exec $ApplianceName -- /bin/bash -lc "curl -fsS http://127.0.0.1:9171/health >/dev/null && curl -fsS http://127.0.0.1:9000/healthz >/dev/null && curl -fsS http://127.0.0.1:9010/health >/dev/null" | Out-Null
      Write-ProgressLine '==> Appliance: runtime bridge, simulator, and CloudSim are healthy'
      return $true
    } catch {
    }
    Start-Sleep -Seconds 2
    $waited++
  }
  throw 'appliance health check failed: runtime bridge, simulator, or CloudSim is not reachable inside the VM'
}

function Invoke-Compose {
  param(
    [Parameter(Mandatory = $true)][string]$Verb,
    [string[]]$ExtraArgs = @()
  )
  Wait-ComposeBackendReady | Out-Null
  $backend = Get-ComposeBackend
  if ($backend.File -eq 'docker') {
    & docker compose --project-name $ProjectName --project-directory $RootDir -f $ComposeFile $Verb @ExtraArgs
    return
  }
  & docker-compose --project-name $ProjectName --project-directory $RootDir -f $ComposeFile $Verb @ExtraArgs
}

function Invoke-ComposeForProject {
  param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$Verb,
    [string[]]$ExtraArgs = @()
  )
  $backend = Get-ComposeBackend
  if ($backend.File -eq 'docker') {
    & docker compose --project-name $Project --project-directory $RootDir -f $ComposeFile $Verb @ExtraArgs
    return
  }
  & docker-compose --project-name $Project --project-directory $RootDir -f $ComposeFile $Verb @ExtraArgs
}

function Cleanup-LegacyProjects {
  $legacyProjects = @('cloudlearn')
  foreach ($legacy in $legacyProjects) {
    if ($legacy -ne $ProjectName) {
      try {
        Invoke-ComposeForProject -Project $legacy -Verb 'down' -ExtraArgs @('--remove-orphans') | Out-Null
      } catch {
      }
    }
  }
}

function Show-Usage {
  @'
cloud-learn - local cloud simulator launcher

Usage:
  .\scripts\cloud-learn.ps1 up
  .\scripts\cloud-learn.ps1 down
  .\scripts\cloud-learn.ps1 stop
  .\scripts\cloud-learn.ps1 force-stop
  .\scripts\cloud-learn.ps1 kill
  .\scripts\cloud-learn.ps1 restart
  .\scripts\cloud-learn.ps1 status
  .\scripts\cloud-learn.ps1 doctor
  .\scripts\cloud-learn.ps1 help

Environment:
  CLOUD_LEARN_HOME         Root directory containing CloudLearn sources
  CLOUD_LEARN_COMPOSE_FILE Alternate compose file path
  CLOUD_LEARN_PROJECT_NAME Compose project name (default: cloud-learn)
  CLOUD_LEARN_RUNTIME_CONTEXT outer=manage appliance VM, inner=start stack in VM
'@ | Write-Output
}

$cmd = if ($RemainingArgs.Count -gt 0) { $RemainingArgs[0] } else { 'help' }
$args = if ($RemainingArgs.Count -gt 1) { $RemainingArgs[1..($RemainingArgs.Count - 1)] } else { @() }

if ($RuntimeContext -eq 'inner') {
  switch ($cmd) {
    'up' {
      Invoke-Compose -Verb 'up' -ExtraArgs (@('--build', '--force-recreate') + $args)
    }
    'down' {
      Invoke-Compose -Verb 'down' -ExtraArgs $args
    }
    'restart' {
      Invoke-Compose -Verb 'restart' -ExtraArgs $args
    }
    'status' {
      Invoke-Compose -Verb 'ps' -ExtraArgs $args
    }
    'doctor' {
      Write-Doctor
    }
    'help' {
      Show-Usage
    }
    default {
      Write-Error "Unknown inner command: $cmd"
      Show-Usage
      exit 2
    }
  }
  } else {
    switch ($cmd) {
    'up' {
      Start-ApplianceVm
      Start-ApplianceRuntimeBridge
      Invoke-ApplianceLauncher
      Test-ApplianceHealth | Out-Null
    }
    'down' {
      $compose = Get-MultipassCommand
      & $compose stop $ApplianceName | Out-Null
    }
    'stop' {
      $compose = Get-MultipassCommand
      & $compose stop $ApplianceName | Out-Null
    }
    'force-stop' {
      $compose = Get-MultipassCommand
      & $compose stop --force $ApplianceName | Out-Null
    }
    'kill' {
      $compose = Get-MultipassCommand
      & $compose stop --force $ApplianceName | Out-Null
    }
    'restart' {
      $compose = Get-MultipassCommand
      & $compose restart $ApplianceName | Out-Null
      Start-ApplianceRuntimeBridge
      Invoke-ApplianceLauncher
      Test-ApplianceHealth | Out-Null
    }
    'status' {
      $compose = Get-MultipassCommand
      & $compose info $ApplianceName
    }
    'doctor' {
      Write-Doctor
    }
    'help' {
      Show-Usage
    }
    default {
      Write-Error "Unknown command: $cmd"
      Show-Usage
      exit 2
    }
  }
}
