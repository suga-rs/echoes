# Deployment de la App en Azure

> **Proyecto:** Generador de Aventuras de Texto con IA
> **Suscripción:** Azure for Students
> **Prerequisito:** tener todos los recursos provisionados según `setup_azure.md`

Esta guía cubre el hosting del backend (FastAPI) y el frontend (Next.js) en Azure para que sean accesibles públicamente.

## Arquitectura

```
GitHub Repo
  frontend/ ──────────────────────────→ Azure Static Web Apps (swa-ata)
  backend/  → GitHub Actions → GHCR → Azure Container Apps (ca-backend-ia-aplicada)
    (push a main)   (build+push)          ↓ Managed Identity (sin API keys)
                               foundry-ata | cosmos-ata-XYZ | stataimgsXYZ
```

**Recursos nuevos que crea esta guía:**

| Recurso | Nombre | SKU | Costo ~mensual |
|---|---|---|---|
| Container Apps Environment | `cae-ata` | Consumption | pay-per-use |
| Container App (backend) | `ca-backend-ia-aplicada` | min=0 réplicas | ~$0 idle |
| Static Web App (frontend) | `swa-ata` | Free | $0 |

> **¿Por qué no ACR?** GitHub Container Registry (GHCR) cumple el mismo rol de forma gratuita y sin necesidad de permisos especiales en Azure. El workflow de GitHub Actions construye y sube la imagen automáticamente en cada push.

---

## Variables de sesión

Definir al inicio de la sesión PowerShell. Reemplazar `XYZ` con el sufijo real de tus recursos:

```powershell
$RG           = "rg-ia-aplicada"
$LOC          = "eastus2"
$GHCR_USER    = "sad-ko"              # usuario de GitHub (dueño del repo)
$CAE_NAME     = "cae-ata"
$CA_NAME      = "ca-backend-ia-aplicada"
$SWA_NAME     = "swa-ata"
$COSMOS_NAME  = "cosmos-ata-XYZ"
$STORAGE_NAME = "stataimgsXYZ"

$FOUNDRY_ENDPOINT = "https://foundry-ata.cognitiveservices.azure.com/"
$PROJECT_ENDPOINT = "https://foundry-ata.services.ai.azure.com/api/projects/proj-ata"
$COSMOS_ENDPOINT  = "https://cosmos-ata-XYZ.documents.azure.com:443/"
$APPI_CONN        = "<connection_string_de_appi-ata>"  # desde setup_azure.md paso 8
```

---

## Secrets en GitHub

El repositorio necesita estos secrets (Settings → Secrets and variables → Actions):

| Secret | Quién lo usa | Valor |
|---|---|---|
| `AZURE_STATIC_WEB_APPS_API_TOKEN_POLITE_PEBBLE_023B85A0F` | Workflow SWA | Token generado por Azure al crear el SWA |
| `BACKEND_URL` | Workflow SWA | URL completa del Container App, ej: `https://ca-backend-ia-aplicada.xxx.eastus2.azurecontainerapps.io` |

> `GITHUB_TOKEN` es automático — no hay que configurarlo. El backend workflow no necesita ninguna credencial de Azure: solo hace push a GHCR.

---

## Paso 1: Dockerfile del backend

El archivo `backend/Dockerfile` ya existe en el repositorio:

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN pip install --upgrade pip && pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --no-create-home app
COPY --from=builder /venv /venv
WORKDIR /app
ENV PATH="/venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
```

Notas:
- El venv se copia completo al runtime stage — evita conflictos con el Python del sistema.
- `--workers 1` es intencional: Container Apps escala con réplicas, no con procesos worker. Múltiples workers romperían el `@lru_cache` de `get_settings()`.

---

## Paso 2: Workflow de backend (build + push a GHCR)

El archivo `.github/workflows/deploy-backend.yml` se dispara en cada push a `main` que modifique `backend/`. Solo construye y sube la imagen a GHCR — **no hay ningún paso de Azure**:

```yaml
name: Deploy Backend
on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/deploy-backend.yml"
  workflow_dispatch:

env:
  IMAGE_NAME: ${{ github.repository_owner }}/backend

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v6
      - name: Log in to GHCR
        uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push image
        uses: docker/build-push-action@v7
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: ghcr.io/${{ env.IMAGE_NAME }}:latest
```

Para disparar el primer build:

```powershell
# Opción A: desde GitHub UI
# → Actions → "Deploy Backend" → Run workflow

# Opción B: push vacío
git commit --allow-empty -m "chore: trigger initial backend build"
git push origin main
```

Verificar que la imagen quedó en GHCR:

```
https://github.com/sad-ko?tab=packages
```

Debe aparecer el package `backend` con el tag `latest`.

---

## Paso 3: Azure Container Apps

```powershell
# 3.1 Instalar extensión (si no está instalada)
az extension add --name containerapp --upgrade

# 3.2 Crear environment
az containerapp env create `
  --name $CAE_NAME `
  --resource-group $RG `
  --location $LOC

# Esperar ~2 minutos hasta Succeeded
az containerapp env show --name $CAE_NAME --resource-group $RG `
  --query "properties.provisioningState" --output tsv

# 3.3 Crear Container App
# CORS_ORIGINS usa localhost como placeholder; se actualiza en el Paso 6 cuando
# se conozca la URL del Static Web App.
az containerapp create `
  --name $CA_NAME `
  --resource-group $RG `
  --environment $CAE_NAME `
  --image "ghcr.io/${GHCR_USER}/backend:latest" `
  --system-assigned `
  --target-port 8000 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 3 `
  --cpu 0.5 `
  --memory 1.0Gi `
  --env-vars `
    "FOUNDRY_ENDPOINT=${FOUNDRY_ENDPOINT}" `
    "PROJECT_ENDPOINT=${PROJECT_ENDPOINT}" `
    "FOUNDRY_API_KEY=" `
    "LLM_DEPLOYMENT=gpt-41-mini-ata" `
    "IMAGE_DEPLOYMENT=gpt-image-2-ata" `
    "API_VERSION=2026-05-11-preview" `
    "COSMOS_ENDPOINT=${COSMOS_ENDPOINT}" `
    "COSMOS_KEY=" `
    "COSMOS_DATABASE=aventuras" `
    "COSMOS_CONTAINER=partidas" `
    "STORAGE_ACCOUNT_NAME=${STORAGE_NAME}" `
    "STORAGE_CONTAINER=imagenes-aventuras" `
    "STORAGE_CONNECTION_STRING=" `
    "APPLICATIONINSIGHTS_CONNECTION_STRING=${APPI_CONN}" `
    "LOG_LEVEL=INFO" `
    "MAX_TURNOS_POR_PARTIDA=25" `
    "MAX_IMAGENES_POR_PARTIDA=5" `
    "CORS_ORIGINS=http://localhost:3000"

# Guardar URL del backend
$CA_URL = $(az containerapp show `
  --name $CA_NAME --resource-group $RG `
  --query "properties.configuration.ingress.fqdn" --output tsv)
Write-Host "Backend: https://$CA_URL"
```

Las vars `FOUNDRY_API_KEY=`, `COSMOS_KEY=`, `STORAGE_CONNECTION_STRING=` se pasan vacías a propósito: el código de `config.py` activa `DefaultAzureCredential` cuando son string vacío.

---

## Paso 4: RBAC para la Managed Identity

El Container App tiene una system-assigned Managed Identity. Darle acceso a los tres servicios:

```powershell
$CA_IDENTITY = $(az containerapp show `
  --name $CA_NAME --resource-group $RG `
  --query "identity.principalId" --output tsv)

# 4.1 Cognitive Services User → Foundry
$FOUNDRY_ID = $(az cognitiveservices account show `
  --name "foundry-ata" --resource-group $RG --query id --output tsv)
az role assignment create `
  --role "Cognitive Services User" `
  --assignee $CA_IDENTITY `
  --scope $FOUNDRY_ID

# 4.2 Cosmos DB Built-in Data Contributor (role ID es fijo en todos los tenants)
$COSMOS_ID = $(az cosmosdb show `
  --name $COSMOS_NAME --resource-group $RG --query id --output tsv)
az cosmosdb sql role assignment create `
  --account-name $COSMOS_NAME `
  --resource-group $RG `
  --scope $COSMOS_ID `
  --principal-id $CA_IDENTITY `
  --role-definition-id "00000000-0000-0000-0000-000000000002"

# 4.3 Storage Blob Data Contributor
$STORAGE_ID = $(az storage account show `
  --name $STORAGE_NAME --resource-group $RG --query id --output tsv)
az role assignment create `
  --role "Storage Blob Data Contributor" `
  --assignee $CA_IDENTITY `
  --scope $STORAGE_ID
```

> **Nota:** los role assignments pueden tardar hasta 5 minutos en propagarse. Si el Container App falla con errores de autenticación inmediatamente después de asignar, esperar y reiniciar la revisión activa:
>
> ```powershell
> az containerapp revision restart --name $CA_NAME --resource-group $RG `
>   --revision $(az containerapp revision list --name $CA_NAME --resource-group $RG `
>     --query "[0].name" --output tsv)
> ```

---

## Paso 5: Frontend en Azure Static Web Apps

### 5.1 Archivos ya presentes en el repositorio

`frontend/next.config.mjs` — ya tiene `output: 'export'` y `unoptimized: true`:

```js
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "*.blob.core.windows.net" }],
    unoptimized: true,
  },
};
export default nextConfig;
```

`frontend/staticwebapp.config.json` — ya presente, redirige rutas al SPA:

```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/images/*", "/*.{js,css,ico,png,svg,json,map}"]
  }
}
```

Verificar el build localmente antes de continuar:

```powershell
cd frontend
npm run build   # debe generar out/ sin errores
cd ..
```

### 5.2 Crear el Static Web App

```powershell
az extension add --name staticwebapp --upgrade

az staticwebapp create `
  --name $SWA_NAME `
  --resource-group $RG `
  --location "eastus2" `
  --source "https://github.com/sad-ko/generador-de-aventuras" `
  --branch "main" `
  --app-location "frontend" `
  --output-location "out" `
  --login-with-github

$SWA_URL = $(az staticwebapp show `
  --name $SWA_NAME --resource-group $RG `
  --query "defaultHostname" --output tsv)
Write-Host "Frontend: https://$SWA_URL"
```

Azure crea automáticamente el workflow `.github/workflows/azure-static-web-apps-polite-pebble-023b85a0f.yml` y agrega el secret `AZURE_STATIC_WEB_APPS_API_TOKEN_POLITE_PEBBLE_023B85A0F` al repositorio.

### 5.3 Configurar el secret `BACKEND_URL`

El workflow inyecta `NEXT_PUBLIC_API_URL` durante `npm run build` leyendo el secret `BACKEND_URL`. Crearlo en GitHub:

```
GitHub → Settings → Secrets and variables → Actions → New repository secret
  Name:  BACKEND_URL
  Value: https://<fqdn-del-container-app>
```

Después de crearlo, disparar un redeploy desde GitHub Actions o hacer cualquier push a `main`.

---

## Paso 6: Actualizar CORS en el Container App

```powershell
az containerapp update `
  --name $CA_NAME `
  --resource-group $RG `
  --set-env-vars "CORS_ORIGINS=https://$SWA_URL,http://localhost:3000"
```

Container Apps crea una nueva revisión automáticamente, lo que reinicia el proceso y vacía el `@lru_cache` de `get_settings()`. El nuevo valor de `CORS_ORIGINS` se lee en el próximo startup del proceso.

---

## Verificación final

```powershell
# 1. Backend responde
Invoke-RestMethod -Uri "https://$CA_URL/healthz"
# Esperado: @{ status = "ok" }

# 2. CORS correcto (el header Access-Control-Allow-Origin debe estar presente)
Invoke-WebRequest -Uri "https://$CA_URL/healthz" `
  -Headers @{ "Origin" = "https://$SWA_URL" } `
  -Method OPTIONS

# 3. Ver logs en tiempo real (útil para diagnosticar errores de auth)
az containerapp logs show --name $CA_NAME --resource-group $RG --follow --tail 50

# 4. Abrir el frontend
Start-Process "https://$SWA_URL"

# 5. Ver estado de las réplicas
az containerapp revision list `
  --name $CA_NAME --resource-group $RG `
  --query "[].{revision:name, replicas:properties.replicas, weight:properties.trafficWeight}" `
  --output table
```

Test end-to-end manual:
1. Iniciar una partida desde el frontend — verifica Foundry via Managed Identity.
2. Refrescar la página — verifica que el estado persiste (Cosmos DB via Managed Identity).
3. Avanzar hasta que se genere una imagen — verifica que la URL apunta a `stataimgsXYZ.blob.core.windows.net` y carga.
4. Abrir `appi-ata` en el portal de Azure → Application Insights → Live Metrics — puede tardar 2-3 minutos en aparecer el primer trace.

---

## Actualizar la imagen del backend (redeploy)

Cualquier push a `main` que modifique archivos dentro de `backend/` dispara automáticamente el workflow, que construye y sube la nueva imagen a GHCR. El deploy al Container App es siempre manual:

```powershell
# Ejecutar desde la raíz del repo (requiere az login activo)
.\scripts\deploy-backend.ps1
```

El script tiene como defaults `rg-ia-aplicada` / `ca-backend-ia-aplicada` / `sad-ko`. Sobrescribir si es necesario:

```powershell
.\scripts\deploy-backend.ps1 -GhcrUser "otro-usuario" -ResourceGroup "otro-rg"
```

El frontend se redeploya automáticamente en cada push a `main` via el workflow que creó Azure Static Web Apps.

---

## Solución de problemas comunes

### Container App falla con `CredentialUnavailableError` o `AuthorizationError`

Los role assignments tardaron más de lo esperado en propagarse. Esperar 5 minutos y reiniciar la revisión activa:

```powershell
az containerapp revision restart --name $CA_NAME --resource-group $RG `
  --revision $(az containerapp revision list --name $CA_NAME --resource-group $RG `
    --query "[0].name" --output tsv)
```

### Container App falla con `ImagePullBackoff` o `401 Unauthorized` al pulllear de GHCR

Solo ocurre si el repositorio es **privado**. Verificar que la imagen en GHCR no fue marcada manualmente como privada. Si es privada, agregar credenciales al Container App:

```powershell
az containerapp registry set `
  --name $CA_NAME `
  --resource-group $RG `
  --server "ghcr.io" `
  --username $GHCR_USER `
  --password $GHCR_PAT   # PAT con permiso read:packages
```

### Las env vars no aparecen en el Container App

```powershell
az containerapp show --name $CA_NAME --resource-group $RG `
  --query "properties.template.containers[0].env" --output table
```

### El frontend carga pero las llamadas al backend dan error de CORS

Verificar que `CORS_ORIGINS` en el Container App incluye el dominio exacto del SWA:
- Con `https://` al principio
- Sin trailing slash al final
- Formato: `<nombre>.azurestaticapps.net`

### El frontend no usa la URL correcta del backend

La variable `NEXT_PUBLIC_API_URL` se inyecta desde el secret `BACKEND_URL` durante `npm run build` en el workflow del SWA. Si se configuró después del último deploy, forzar un redeploy desde GitHub Actions.

### `npm run build` falla con `output: 'export'` y error en `next/image`

Verificar que `unoptimized: true` está en la configuración de `images` en `next.config.mjs`.
