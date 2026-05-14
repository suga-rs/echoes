param(
    [string]$ResourceGroup = "rg-ia-aplicada",
    [string]$ContainerApp  = "ca-backend-ia-aplicada",
    [string]$GhcrUser      = "suga-rs"
)

az containerapp update `
  --name $ContainerApp `
  --resource-group $ResourceGroup `
  --image "ghcr.io/${GhcrUser}/backend:latest"
