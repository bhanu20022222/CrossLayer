param(
    [string]$Kubeconfig = (Join-Path $HOME ".kube\microk8s-config")
)

$ErrorActionPreference = "Stop"
$kubectl = (Get-Command kubectl -ErrorAction Stop).Source
$namespace = "crosslayer-experiments"
$probeNamespace = "crosslayer-system"
$serviceScript = Join-Path $PSScriptRoot "..\..\dashboard\backend\app\experiment_service.py"
$probeMain = Join-Path $PSScriptRoot "..\..\network-prober\src\network_prober\__main__.py"
$probeInit = Join-Path $PSScriptRoot "..\..\network-prober\src\network_prober\__init__.py"
$microservicesManifest = Join-Path $PSScriptRoot "microservices.yaml"
$probeManifest = Join-Path $PSScriptRoot "..\..\network-prober\kubernetes.yaml"

foreach ($path in @($serviceScript, $probeMain, $probeInit, $microservicesManifest, $probeManifest)) {
    if (-not (Test-Path $path)) {
        throw "Required experiment deployment file not found: $path"
    }
}
if (-not (Test-Path $Kubeconfig)) {
    throw "Kubeconfig not found: $Kubeconfig"
}

& $kubectl --kubeconfig $Kubeconfig get namespace $namespace | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Namespace $namespace does not exist; no cluster resources were applied."
}

$serviceConfig = & $kubectl --kubeconfig $Kubeconfig create configmap crosslayer-experiment-service-code `
    --namespace $namespace `
    "--from-file=experiment_service.py=$serviceScript" `
    --dry-run=client -o yaml
if ($LASTEXITCODE -ne 0) {
    throw "Could not render the experiment service ConfigMap."
}
$serviceConfig | & $kubectl --kubeconfig $Kubeconfig apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply the experiment service ConfigMap."
}

$probeConfig = & $kubectl --kubeconfig $Kubeconfig create configmap crosslayer-network-prober-v2-code `
    --namespace $probeNamespace `
    "--from-file=__main__.py=$probeMain" `
    "--from-file=__init__.py=$probeInit" `
    --dry-run=client -o yaml
if ($LASTEXITCODE -ne 0) {
    throw "Could not render the network-prober ConfigMap."
}
$probeConfig | & $kubectl --kubeconfig $Kubeconfig apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply the network-prober ConfigMap."
}

& $kubectl --kubeconfig $Kubeconfig apply --dry-run=server -f $microservicesManifest
if ($LASTEXITCODE -ne 0) {
    throw "Experiment microservice server-side validation failed."
}
& $kubectl --kubeconfig $Kubeconfig apply --dry-run=server -f $probeManifest
if ($LASTEXITCODE -ne 0) {
    throw "Network-prober server-side validation failed."
}

& $kubectl --kubeconfig $Kubeconfig apply -f $microservicesManifest
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply the experiment microservices."
}
& $kubectl --kubeconfig $Kubeconfig apply -f $probeManifest
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply the inter-node probe."
}

foreach ($deployment in @("experiment-api", "experiment-worker", "experiment-store")) {
    & $kubectl --kubeconfig $Kubeconfig rollout status "deployment/$deployment" `
        --namespace $namespace --timeout=180s
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment did not become ready: $deployment"
    }
}
& $kubectl --kubeconfig $Kubeconfig rollout status daemonset/crosslayer-network-prober-v2 `
    --namespace crosslayer-system --timeout=300s
if ($LASTEXITCODE -ne 0) {
    throw "The inter-node probe DaemonSet did not become ready."
}

& $kubectl --kubeconfig $Kubeconfig get pods,services -n $namespace -o wide
& $kubectl --kubeconfig $Kubeconfig get pods -n $probeNamespace -l app=network-prober-v2 -o wide
Write-Output "Deployment complete. No load test was started."
