# Deployment de la App en Azure

> **Proyecto:** Generador de Aventuras de Texto con IA
> **Suscripción:** Azure for Students
> **Prerequisito:** tener todos los recursos provisionados según `setup_azure.md`

Esta guía cubre el hosting del backend (FastAPI) y el frontend (Next.js) en Azure para que sean accesibles públicamente.

## Arquitectura

```
GitHub Repo
  frontend/ ──────────────────────────→ Azure Static Web Apps (swa-ata)
  backend/  → GitHub Actions → GHCR → Azure Container Apps (ca-backend-ata)
    (push a main)   (build+push)          ↓ Managed Identity (sin API keys)
                               foundry-ata | cosmos-ata-XYZ | stataimgsXYZ
```

**Recursos nuevos que crea esta guía:**

| Recurso | Nombre | SKU | Costo ~mensual |
|---|---|---|---|
| Container Apps Environment | `cae-ata` | Consumption | pay-per-use |
| Container App (backend) | `ca-backend-ata` | min=0 réplicas | ~$0 idle |
| Static Web App (frontend) | `swa-ata` | Free | $0 |

> **¿Por qué no ACR?** GitHub Container Registry (GHCR) cumple el mismo rol de forma gratuita y sin necesidad de permisos especiales en Azure. El workflow de GitHub Actions construye y sube la imagen automáticamente en cada push.

---

## Variables de sesión

Definir al inicio de la sesión PowerShell. Reemplazar `XYZ` con el sufijo real de tus recursos y `<tu-usuario-github>` con tu usuario de GitHub:

```powershell
$RG           = "rg-ata-dev"
$LOC          = "eastus2"
$GHCR_USER    = "<tu-usuario-github>"    # ej: "sad-ko"
# $GHCR_PAT  solo necesario si el repositorio es privado (ver Paso 1.1)
$CAE_NAME     = "cae-ata"
$CA_NAME      = "ca-backend-ata"
$SWA_NAME     = "swa-ata"
$COSMOS_NAME  = "cosmos-ata-XYZ"
$STORAGE_NAME = "stataimgsXYZ"

$FOUNDRY_ENDPOINT = "https://foundry-ata.cognitiveservices.azure.com/"
$PROJECT_ENDPOINT = "https://foundry-ata.services.ai.azure.com/api/projects/proj-ata"
$COSMOS_ENDPOINT  = "https://cosmos-ata-XYZ.documents.azure.com:443/"
$APPI_CONN        = "<connection_string_de_appi-ata>"  # desde setup_azure.md paso 8
```

---

## Paso 1: Preparar GHCR y GitHub Secrets

### 1.1 Visibilidad de la imagen en GHCR

El workflow usa `GITHUB_TOKEN` (automático) para **pushear** la imagen — no necesitás ningún PAT para eso.

Para el **pull** que hace Azure Container Apps en runtime:

- **Repo público** → la imagen en GHCR es pública por defecto. Container Apps puede pullearla **sin credenciales**. No hace falta ningún PAT.
- **Repo privado** → la imagen es privada. En ese caso creá un Fine-grained PAT con permiso `read:packages` y guardalo como `$GHCR_PAT`:
  - GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
  - Repository access: solo este repo | Permissions → Packages: Read-only

### 1.2 Deploy del Container App (sin Service Principal)

> **Azure for Students** no permite crear Service Principals (`az ad sp create-for-rbac` requiere permisos de Azure AD que la suscripción estudiantil no otorga).

El workflow de GitHub Actions se encarga únicamente del **build y push a GHCR** — no necesita ninguna credencial de Azure para eso. El deploy al Container App se hace manualmente desde la máquina local con el script `scripts/deploy-backend.ps1`:

```powershell
# Ejecutar desde la raíz del repo, después de que el workflow haya subido la imagen
.\scripts\deploy-backend.ps1
```

El script asume que ya tenés `az login` activo en tu sesión. Los valores por defecto (`rg-ata-dev`, `ca-backend-ata`, `sad-ko`) se pueden sobrescribir:

```powershell
.\scripts\deploy-backend.ps1 -GhcrUser "tu-usuario"
```

**No hay secrets de Azure que configurar en el repositorio de GitHub.**

---

## Paso 2: Dockerfile del backend

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

## Paso 3: Primer build y push de la imagen

El workflow `.github/workflows/deploy-backend.yml` construye y sube la imagen automáticamente en cada push a `main` que modifique `backend/`. Para el primer deploy, hacer un push vacío o disparar el workflow manualmente:

```powershell
# Opción A: disparar desde GitHub UI
# → Actions → "Deploy Backend" → Run workflow

# Opción B: push vacío desde la terminal
git commit --allow-empty -m "chore: trigger initial backend deploy"
git push origin main
```

Verificar que la imagen quedó en GHCR:

```
https://github.com/<tu-usuario-github>?tab=packages
```

Debe aparecer el package `backend` con el tag `latest`.

---

## Paso 4: Azure Container Apps

```powershell
# 4.1 Instalar extensión (si no está instalada)
az extension add --name containerapp --upgrade

# 4.2 Crear environment
az containerapp env create `
  --name $CAE_NAME `
  --resource-group $RG `
  --location $LOC

# Esperar ~2 minutos hasta Succeeded
az containerapp env show --name $CAE_NAME --resource-group $RG `
  --query "properties.provisioningState" --output tsv

# 4.3 Crear Container App
# CORS_ORIGINS usa localhost como placeholder; se actualiza en el Paso 7 cuando
# se conozca la URL del Static Web App.
az containerapp create `
  --name $CA_NAME `
  --resource-group $RG `
  --environment $CAE_NAME `
  --image "ghcr.io/${GHCR_USER}/backend:latest" `
  --system-assigned `
  # Si el repo es privado, agregar también:
  # --registry-server "ghcr.io" `
  # --registry-username $GHCR_USER `
  # --registry-password $GHCR_PAT `
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

## Paso 5: RBAC para la Managed Identity

El Container App tiene una system-assigned Managed Identity. Darle acceso a los tres servicios:

```powershell
$CA_IDENTITY = $(az containerapp show `
  --name $CA_NAME --resource-group $RG `
  --query "identity.principalId" --output tsv)

# 5.1 Cognitive Services User → Foundry
$FOUNDRY_ID = $(az cognitiveservices account show `
  --name "foundry-ata" --resource-group $RG --query id --output tsv)
az role assignment create `
  --role "Cognitive Services User" `
  --assignee $CA_IDENTITY `
  --scope $FOUNDRY_ID

# 5.2 Cosmos DB Built-in Data Contributor (role ID es fijo en todos los tenants)
$COSMOS_ID = $(az cosmosdb show `
  --name $COSMOS_NAME --resource-group $RG --query id --output tsv)
az cosmosdb sql role assignment create `
  --account-name $COSMOS_NAME `
  --resource-group $RG `
  --scope $COSMOS_ID `
  --principal-id $CA_IDENTITY `
  --role-definition-id "00000000-0000-0000-0000-000000000002"

# 5.3 Storage Blob Data Contributor
$STORAGE_ID = $(az storage account show `
  --name $STORAGE_NAME --resource-group $RG --query id --output tsv)
az role assignment create `
  --role "Storage Blob Data Contributor" `
  --assignee $CA_IDENTITY `
  --scope $STORAGE_ID
```

> **Nota:** los role assignments de Azure pueden tardar hasta 5 minutos en propagarse. Si el Container App falla con errores de autenticación inmediatamente después de asignar, esperar y reiniciar la revisión activa:
>
> ```powershell
> az containerapp revision restart --name $CA_NAME --resource-group $RG `
>   --revision $(az containerapp revision list --name $CA_NAME --resource-group $RG `
>     --query "[0].name" --output tsv)
> ```

---

## Paso 6: Frontend en Azure Static Web Apps

### 6.1 Modificar `frontend/next.config.mjs`

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.blob.core.windows.net",
      },
    ],
    unoptimized: true,
  },
};

export default nextConfig;
```

`output: 'export'` genera el sitio estático en `out/`. `unoptimized: true` es requerido porque el Image Optimization API de Next.js no existe en sitios estáticos — las imágenes de Blob Storage se siguen cargando igual (son URLs directas).

Verificar el build localmente antes de continuar:

```powershell
cd frontend
npm run build
# Debe generar la carpeta out/ sin errores
cd ..
```

### 6.2 Crear `frontend/staticwebapp.config.json`

```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/images/*", "/*.{js,css,ico,png,svg,json,map}"]
  }
}
```

Este archivo le dice al SWA que redirija cualquier ruta no encontrada a `index.html`, necesario para que el routing de React funcione.

### 6.3 Crear el Static Web App

Reemplazar `<tu-usuario>/<tu-repo>` con el path real del repo en GitHub:

```powershell
az extension add --name staticwebapp --upgrade

az staticwebapp create `
  --name $SWA_NAME `
  --resource-group $RG `
  --location "eastus2" `
  --source "https://github.com/<tu-usuario>/<tu-repo>" `
  --branch "main" `
  --app-location "frontend" `
  --output-location "out" `
  --login-with-github

$SWA_URL = $(az staticwebapp show `
  --name $SWA_NAME --resource-group $RG `
  --query "defaultHostname" --output tsv)
Write-Host "Frontend: https://$SWA_URL"
```

El comando crea un workflow en `.github/workflows/` que hace `npm run build` + deploy automáticamente en cada push a `main`.

### 6.4 Configurar `NEXT_PUBLIC_API_URL`

```powershell
az staticwebapp appsettings set `
  --name $SWA_NAME `
  --resource-group $RG `
  --setting-names "NEXT_PUBLIC_API_URL=https://$CA_URL"
```

Esta es una variable de build-time: el workflow de GitHub Actions la inyecta durante `npm run build`. Después de setearla, disparar un nuevo deploy haciendo cualquier push a `main`, o forzar uno desde la UI de GitHub Actions.

---

## Paso 7: Actualizar CORS en el Container App

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

## Solución de problemas comunes

### Container App falla con `CredentialUnavailableError` o `AuthorizationError`

Los role assignments tardaron más de lo esperado en propagarse. Esperar 5 minutos y reiniciar la revisión activa:

```powershell
az containerapp revision restart --name $CA_NAME --resource-group $RG `
  --revision $(az containerapp revision list --name $CA_NAME --resource-group $RG `
    --query "[0].name" --output tsv)
```

### Container App falla con `ImagePullBackoff` o `401 Unauthorized` al pulllear de GHCR

Solo ocurre si el repositorio es **privado** y el PAT expiró o le faltan permisos. Regenerar un PAT con `read:packages` y actualizar las credenciales:

```powershell
az containerapp registry set `
  --name $CA_NAME `
  --resource-group $RG `
  --server "ghcr.io" `
  --username $GHCR_USER `
  --password $GHCR_PAT
```

Si el repositorio es público este error no debería ocurrir — verificar que la imagen en GHCR no fue marcada manualmente como privada.

### El workflow de GitHub Actions falla en "Log in to Azure"

Verificar que los cuatro secrets (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`) están configurados correctamente en el repo.

### Las env vars no aparecen en el Container App

Verificar con:

```powershell
az containerapp show --name $CA_NAME --resource-group $RG `
  --query "properties.template.containers[0].env" --output table
```

### El build de GitHub Actions falla o el frontend no usa la URL correcta del backend

La variable `NEXT_PUBLIC_API_URL` se inyecta durante `npm run build` en el workflow. Si se configuró después de crear el SWA, disparar un redeploy:

```powershell
az staticwebapp environment redeploy `
  --name $SWA_NAME `
  --resource-group $RG `
  --environment-name Production
```

### `npm run build` falla con `output: 'export'` y error en `next/image`

Verificar que `unoptimized: true` está en la configuración de `images` en `next.config.mjs`.

### El frontend carga pero las llamadas al backend dan error de CORS

Verificar que `CORS_ORIGINS` en el Container App incluye el dominio exacto del SWA:
- Con `https://` al principio
- Sin trailing slash al final
- El dominio tiene la forma `<random>.azurestaticapps.net`

---

## Actualizar la imagen del backend (redeploy)

Cualquier push a `main` que modifique archivos dentro de `backend/` dispara automáticamente el workflow `.github/workflows/deploy-backend.yml`, que:
1. Construye la imagen Docker
2. La sube a GHCR con el tag `latest`
3. Actualiza el Container App para usar la nueva imagen

Para forzar un redeploy sin cambios de código, correr el script local directamente:

```powershell
.\scripts\deploy-backend.ps1
```

O desde GitHub UI disparar el workflow (sólo hace push de la imagen, el deploy sigue siendo local):

```powershell
# Actions → "Deploy Backend" → Run workflow
# luego: .\scripts\deploy-backend.ps1
```

El frontend se redeploya automáticamente en cada push a `main` via el workflow que crea Azure Static Web Apps.
