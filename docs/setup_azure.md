# Setup de Recursos en Azure y Microsoft Foundry

> **Proyecto:** Generador de Aventuras de Texto con IA
> **Suscripción:** Azure for Students
> **Última actualización:** 2026-05-11

Esta guía describe el procedimiento completo para aprovisionar todos los recursos necesarios en Azure y Microsoft Foundry, desde cero, en una suscripción Azure for Students. El orden importa: cada paso depende de los anteriores.

---

## Índice

1. [Prerrequisitos](#1-prerrequisitos)
2. [Decisiones previas](#2-decisiones-previas)
3. [Estructura de recursos](#3-estructura-de-recursos)
4. [Paso 1: Crear el grupo de recursos](#paso-1-crear-el-grupo-de-recursos)
5. [Paso 2: Crear el recurso de Microsoft Foundry](#paso-2-crear-el-recurso-de-microsoft-foundry)
6. [Paso 3: Crear el proyecto de Foundry](#paso-3-crear-el-proyecto-de-foundry)
7. [Paso 4: Desplegar gpt-4.1-mini](#paso-4-desplegar-gpt-41-mini)
8. [Paso 5: Desplegar gpt-image-2](#paso-5-desplegar-gpt-image-2)
9. [Paso 6: Crear Cosmos DB serverless](#paso-6-crear-cosmos-db-serverless)
10. [Paso 7: Crear Azure Blob Storage](#paso-7-crear-azure-blob-storage)
11. [Paso 8: Crear Application Insights](#paso-8-crear-application-insights)
12. [Paso 9: Configurar Managed Identity y RBAC](#paso-9-configurar-managed-identity-y-rbac)
13. [Paso 10: Configurar variables de entorno](#paso-10-configurar-variables-de-entorno)
14. [Verificación final](#verificación-final)
15. [Solución de problemas comunes](#solución-de-problemas-comunes)
16. [Estimación de cuotas necesarias](#estimación-de-cuotas-necesarias)

---

## 1. Prerrequisitos

Antes de empezar, asegurate de tener:

- Cuenta de Azure for Students activa con crédito disponible. Verificar en [https://azure.microsoft.com/free/students](https://azure.microsoft.com/free/students).
- Azure CLI versión 2.60 o superior instalado localmente. Verificar con:
  ```bash
  az --version
  ```
- Python 3.12 instalado.
- Acceso al portal de Foundry: [https://ai.azure.com](https://ai.azure.com).
- Una terminal en la que se mantenga la sesión durante el setup (idealmente una sola sesión de bash o PowerShell).

Si no tenés Azure CLI, instalalo siguiendo: [https://learn.microsoft.com/cli/azure/install-azure-cli](https://learn.microsoft.com/cli/azure/install-azure-cli).

### Login y selección de suscripción

```bash
az login
az account list --output table
az account set --subscription "Azure for Students"
```

Confirmá la suscripción activa:

```bash
az account show --query "{name:name, id:id}" --output table
```

---

## 2. Decisiones previas

Antes de crear nada, fijá los siguientes valores y mantenelos consistentes durante todo el setup. Si los cambiás a mitad de camino, vas a romper referencias.

### Región

**Recomendación: `eastus2`**

Razones:
- `gpt-4.1-mini` está disponible en deployment Global Standard en eastus2.
- `gpt-image-2` está disponible en eastus2 al momento de redacción.
- Es una de las regiones con mejor disponibilidad de cuota para suscripciones Azure for Students.
- Latencia aceptable desde Argentina (~150ms).

Alternativas viables si eastus2 no tiene cuota disponible: `eastus`, `westus3`, `southcentralus`.

> **Verificación obligatoria:** antes de continuar, abrí el portal de Foundry, andá a **Operate → Quota**, activá el toggle **Show all** y confirmá que tu suscripción tiene cuota disponible para ambos modelos en la región elegida. Si no tiene, solicitá aumento de cuota desde el mismo panel antes de seguir. Sin esto vas a fallar en el paso 4 o 5.

### Nombres de recursos

Adoptá una convención y respetala. Acá uso `ata` (aventuras de texto con IA) como prefijo de proyecto.

| Recurso | Nombre sugerido |
|---|---|
| Resource Group | `rg-ata-dev` |
| Foundry Account | `foundry-ata` |
| Foundry Project | `proj-ata` |
| Deployment LLM | `gpt-41-mini-ata` |
| Deployment imagen | `gpt-image-2-ata` |
| Cosmos DB Account | `cosmos-ata-<sufijo>` (debe ser único globalmente; usá tus iniciales o un número) |
| Blob Storage Account | `stataimgs<sufijo>` (sin guiones, sin mayúsculas, único globalmente, máx 24 chars) |
| App Insights | `appi-ata` |

### Variables para los comandos

Definí estas variables al inicio de la sesión de terminal. Todos los comandos posteriores las usan:

```bash
# Bash / zsh
export RG=rg-ata-dev
export LOC=eastus2
export FOUNDRY_NAME=foundry-ata
export PROJECT_NAME=proj-ata
export LLM_DEPLOY=gpt-41-mini-ata
export IMG_DEPLOY=gpt-image-2-ata
export COSMOS_NAME=cosmos-ata-XYZ        # reemplazar XYZ
export STORAGE_NAME=stataimgsXYZ          # reemplazar XYZ
export APPI_NAME=appi-ata
```

Para PowerShell:

```powershell
$env:RG="rg-ata-dev"
$env:LOC="eastus2"
$env:FOUNDRY_NAME="foundry-ata"
# ... etc
```

---

## 3. Estructura de recursos

Visión general de qué crear y cómo se relacionan:

```
Subscription: Azure for Students
└── Resource Group: rg-ata-dev (eastus2)
    ├── Foundry Account: foundry-ata
    │   └── Foundry Project: proj-ata
    │       ├── Deployment: gpt-41-mini-ata    (texto)
    │       └── Deployment: gpt-image-2-ata    (imagen)
    ├── Cosmos DB Account: cosmos-ata-XYZ (serverless)
    │   └── Database: aventuras
    │       └── Container: partidas (PK: /codigo_partida)
    ├── Storage Account: stataimgsXYZ
    │   └── Blob Container: imagenes-aventuras (acceso público de lectura)
    └── Application Insights: appi-ata
```

Todo en un único grupo de recursos para poder borrarlo de un comando cuando termine el proyecto.

---

## Paso 1: Crear el grupo de recursos

```bash
az group create \
  --name $RG \
  --location $LOC
```

Verificación:

```bash
az group show --name $RG --query "{name:name, location:location, state:properties.provisioningState}" -o table
```

Esperado: `provisioningState` debe ser `Succeeded`.

---

## Paso 2: Crear el recurso de Microsoft Foundry

Foundry expone sus servicios a través de un recurso de tipo `Microsoft.CognitiveServices/accounts` con kind `AIServices`.

```bash
az cognitiveservices account create \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --location $LOC \
  --kind AIServices \
  --sku S0 \
  --custom-domain $FOUNDRY_NAME \
  --yes
```

Notas:
- `--kind AIServices` es lo que indica que es un recurso Foundry (vs Cognitive Services clásico).
- `--custom-domain` es **obligatorio** para autenticación con Entra ID. Sin esto, solo podés usar API keys.
- `S0` es el único SKU disponible para Foundry.

Obtené el endpoint que vas a usar después:

```bash
export FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --query "properties.endpoint" -o tsv)

echo $FOUNDRY_ENDPOINT
```

Salida esperada: algo como `https://foundry-ata.cognitiveservices.azure.com/`.

---

## Paso 3: Crear el proyecto de Foundry

Los proyectos en Foundry permiten agrupar deployments, conexiones e identidades bajo un mismo namespace. Para este proyecto académico alcanza con uno solo.

**Esto se hace mejor desde el portal**, porque hay validaciones de UX que la CLI no siempre cubre:

1. Abrí [https://ai.azure.com](https://ai.azure.com).
2. Inicia sesión con la misma cuenta que activaste para Azure for Students.
3. En la lista de recursos, encontrá `foundry-ata`.
4. Click en **+ Create project**.
5. Nombre: `proj-ata`. Descripción: "Generador de aventuras de texto con IA".
6. Click en **Create**.

Una vez creado, anotá el **Project endpoint** que aparece en la página de overview del proyecto. Tiene la forma:

```
https://foundry-ata.services.ai.azure.com/api/projects/proj-ata
```

Guardalo en una variable:

```bash
export PROJECT_ENDPOINT="https://foundry-ata.services.ai.azure.com/api/projects/proj-ata"
```

---

## Paso 4: Desplegar gpt-4.1-mini

Este deployment es el LLM que genera la narrativa. Lo desplegamos en modo Global Standard, que es el más barato y tiene la mejor disponibilidad de cuota.

```bash
az cognitiveservices account deployment create \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --deployment-name $LLM_DEPLOY \
  --model-name gpt-4.1-mini \
  --model-version "2025-04-14" \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 50
```

Parámetros importantes:
- `--sku-name GlobalStandard`: routing global, mejor disponibilidad de capacidad y menor latencia promedio.
- `--sku-capacity 50`: 50 mil tokens por minuto. Para un TP es más que suficiente. Si Azure for Students no permite 50, bajá a 10. El comando va a fallar con mensaje claro indicando el máximo disponible.
- `--model-version`: verificá la versión actual disponible en tu región con `az cognitiveservices account list-models --name $FOUNDRY_NAME --resource-group $RG -o table` antes de ejecutar, y reemplazá si hay una más nueva.

Verificación:

```bash
az cognitiveservices account deployment show \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --deployment-name $LLM_DEPLOY \
  --query "{state:properties.provisioningState, model:properties.model.name, capacity:sku.capacity}" -o table
```

Esperado: `state: Succeeded`.

### Test rápido del deployment

Antes de seguir, comprobá que el deployment responde:

```bash
API_KEY=$(az cognitiveservices account keys list \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --query "key1" -o tsv)

curl -s "$FOUNDRY_ENDPOINT/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "api-key: $API_KEY" \
  -d '{
    "model": "'$LLM_DEPLOY'",
    "messages": [{"role": "user", "content": "Decí hola en una palabra."}],
    "max_tokens": 10
  }' | python3 -m json.tool
```

Si ves una respuesta con `"choices"`, el LLM está OK.

---

## Paso 5: Desplegar gpt-image-2

```bash
az cognitiveservices account deployment create \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --deployment-name $IMG_DEPLOY \
  --model-name gpt-image-2 \
  --model-version "2025-10-13" \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 1
```

Diferencias clave con DALL·E 3:
- `gpt-image-2` factura por tokens de entrada (texto del prompt), no por imagen. Como nuestros prompts son ~200 tokens, el costo por imagen baja sustancialmente respecto a DALL·E 3.
- Soporta resoluciones flexibles. Para apaisado cinematográfico vamos a pedir 1536×1024 al invocarlo (no se configura acá).
- La capacidad de imagen se mide diferente; `--sku-capacity 1` alcanza para el ritmo de uso del proyecto.

Verificación:

```bash
az cognitiveservices account deployment show \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --deployment-name $IMG_DEPLOY \
  --query "{state:properties.provisioningState, model:properties.model.name}" -o table
```

### Test rápido del deployment de imagen

```bash
curl -s "$FOUNDRY_ENDPOINT/openai/v1/images/generations" \
  -H "Content-Type: application/json" \
  -H "api-key: $API_KEY" \
  -d '{
    "model": "'$IMG_DEPLOY'",
    "prompt": "A simple test illustration of a red apple on a white background, minimalist style",
    "size": "1024x1024",
    "n": 1
  }' | python3 -m json.tool
```

Si la respuesta incluye un campo `data` con un `b64_json` o `url`, el modelo está OK. Guardalo para verificar visualmente.

---

## Paso 6: Crear Cosmos DB serverless

Cosmos en modo serverless cobra solo por uso. Para un TP con 100 sesiones de prueba, el costo va a ser de centavos.

```bash
az cosmosdb create \
  --name $COSMOS_NAME \
  --resource-group $RG \
  --locations regionName=$LOC failoverPriority=0 isZoneRedundant=false \
  --capabilities EnableServerless \
  --default-consistency-level Session
```

Crear base de datos y contenedor:

```bash
az cosmosdb sql database create \
  --account-name $COSMOS_NAME \
  --resource-group $RG \
  --name aventuras

az cosmosdb sql container create \
  --account-name $COSMOS_NAME \
  --resource-group $RG \
  --database-name aventuras \
  --name partidas \
  --partition-key-path "/codigo_partida"
```

Notas:
- `--partition-key-path "/codigo_partida"`: la clave de partición es el código de partida, que es justamente la clave por la que el backend consulta. Esto da lecturas y escrituras de costo mínimo (1 RU).
- Modo serverless no acepta throughput dedicado; paga solo por las RUs consumidas.

Obtené el endpoint y connection string:

```bash
export COSMOS_ENDPOINT=$(az cosmosdb show \
  --name $COSMOS_NAME \
  --resource-group $RG \
  --query "documentEndpoint" -o tsv)

# Para uso inicial; en producción reemplazar por Managed Identity
export COSMOS_KEY=$(az cosmosdb keys list \
  --name $COSMOS_NAME \
  --resource-group $RG \
  --type keys \
  --query "primaryMasterKey" -o tsv)

echo $COSMOS_ENDPOINT
```

---

## Paso 7: Crear Azure Blob Storage

Acá se guardan las imágenes generadas para que el frontend pueda referenciarlas por URL.

```bash
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RG \
  --location $LOC \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access true
```

Crear el container con acceso público de lectura (las imágenes no son sensibles):

```bash
az storage container create \
  --name imagenes-aventuras \
  --account-name $STORAGE_NAME \
  --public-access blob \
  --auth-mode login
```

Obtener connection string (para configuración inicial):

```bash
export STORAGE_CONN=$(az storage account show-connection-string \
  --name $STORAGE_NAME \
  --resource-group $RG \
  --query connectionString -o tsv)
```

---

## Paso 8: Crear Application Insights

Observabilidad básica. Para un TP académico esto es opcional pero suma puntos en la defensa.

```bash
az monitor app-insights component create \
  --app $APPI_NAME \
  --location $LOC \
  --resource-group $RG \
  --application-type web \
  --kind web
```

Obtener la connection string que va a consumir el backend:

```bash
export APPI_CONN=$(az monitor app-insights component show \
  --app $APPI_NAME \
  --resource-group $RG \
  --query connectionString -o tsv)
```

---

## Paso 9: Configurar Managed Identity y RBAC

> **Nota:** este paso es opcional para desarrollo local con API keys, pero es **necesario** cuando despliegues el backend en Azure Container Apps (que es el plan). Lo dejamos preparado.

### 9.1. Asignar tu usuario como Azure AI User en Foundry

Esto te permite invocar los modelos con tu identidad de Entra desde el código durante desarrollo, sin manejar API keys:

```bash
USER_ID=$(az ad signed-in-user show --query id -o tsv)

az role assignment create \
  --role "Cognitive Services User" \
  --assignee $USER_ID \
  --scope $(az cognitiveservices account show --name $FOUNDRY_NAME --resource-group $RG --query id -o tsv)
```

### 9.2. Asignar Cosmos DB Data Contributor

```bash
COSMOS_ID=$(az cosmosdb show --name $COSMOS_NAME --resource-group $RG --query id -o tsv)

az cosmosdb sql role assignment create \
  --account-name $COSMOS_NAME \
  --resource-group $RG \
  --scope "$COSMOS_ID" \
  --principal-id $USER_ID \
  --role-definition-id "00000000-0000-0000-0000-000000000002"
```

### 9.3. Asignar Storage Blob Data Contributor

```bash
STORAGE_ID=$(az storage account show --name $STORAGE_NAME --resource-group $RG --query id -o tsv)

az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $USER_ID \
  --scope $STORAGE_ID
```

Con esto, durante desarrollo local podés usar `DefaultAzureCredential()` y todo funciona sin pegar claves en el código.

---

## Paso 10: Configurar variables de entorno

Creá un archivo `.env` en la raíz del proyecto backend con todos los valores que recogiste. **Este archivo NO va a git**, agregalo al `.gitignore` desde el primer commit.

```bash
# .env

# Foundry
FOUNDRY_ENDPOINT=https://foundry-ata.cognitiveservices.azure.com/
PROJECT_ENDPOINT=https://foundry-ata.services.ai.azure.com/api/projects/proj-ata
FOUNDRY_API_KEY=<tu_api_key>   # solo para desarrollo local; en producción usar Managed Identity
LLM_DEPLOYMENT=gpt-41-mini-ata
IMAGE_DEPLOYMENT=gpt-image-2-ata
API_VERSION=2025-04-01-preview

# Cosmos DB
COSMOS_ENDPOINT=<endpoint>
COSMOS_KEY=<key>               # solo para desarrollo local
COSMOS_DATABASE=aventuras
COSMOS_CONTAINER=partidas

# Storage
STORAGE_ACCOUNT_NAME=<nombre>
STORAGE_CONTAINER=imagenes-aventuras
STORAGE_CONNECTION_STRING=<connection_string>   # solo para desarrollo local

# App Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection_string>

# App config
LOG_LEVEL=INFO
MAX_TURNOS_POR_PARTIDA=25
MAX_IMAGENES_POR_PARTIDA=5
```

Generá un `.env.example` con las claves pero sin valores, ese sí va a git como referencia para el equipo.

---

## Verificación final

Ejecutá este script Python para validar que todos los servicios responden:

```python
# scripts/verify_setup.py
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

load_dotenv()

print("=== Verificación de setup ===\n")

# 1. Foundry / OpenAI
print("1. Probando Foundry (gpt-4.1-mini)...")
try:
    client = AzureOpenAI(
        azure_endpoint=os.environ["FOUNDRY_ENDPOINT"],
        api_key=os.environ["FOUNDRY_API_KEY"],
        api_version=os.environ["API_VERSION"],
    )
    response = client.chat.completions.create(
        model=os.environ["LLM_DEPLOYMENT"],
        messages=[{"role": "user", "content": "Respondé solo: OK"}],
        max_tokens=5,
    )
    print(f"   Respuesta: {response.choices[0].message.content.strip()}")
    print("   OK\n")
except Exception as e:
    print(f"   FALLO: {e}\n")

# 2. Foundry / gpt-image-2
print("2. Probando Foundry (gpt-image-2)...")
try:
    img = client.images.generate(
        model=os.environ["IMAGE_DEPLOYMENT"],
        prompt="A small red apple on white background, minimalist",
        size="1024x1024",
        n=1,
    )
    print(f"   Imagen generada, URL recibida: {bool(img.data[0].url or img.data[0].b64_json)}")
    print("   OK\n")
except Exception as e:
    print(f"   FALLO: {e}\n")

# 3. Cosmos DB
print("3. Probando Cosmos DB...")
try:
    cosmos = CosmosClient(
        os.environ["COSMOS_ENDPOINT"],
        credential=os.environ["COSMOS_KEY"],
    )
    db = cosmos.get_database_client(os.environ["COSMOS_DATABASE"])
    container = db.get_container_client(os.environ["COSMOS_CONTAINER"])
    # write + read
    test_doc = {"id": "verify-test", "codigo_partida": "verify-test", "test": True}
    container.upsert_item(test_doc)
    read = container.read_item("verify-test", "verify-test")
    container.delete_item("verify-test", "verify-test")
    print("   OK (escritura + lectura + borrado verificados)\n")
except Exception as e:
    print(f"   FALLO: {e}\n")

# 4. Blob Storage
print("4. Probando Blob Storage...")
try:
    blob = BlobServiceClient.from_connection_string(
        os.environ["STORAGE_CONNECTION_STRING"]
    )
    container_client = blob.get_container_client(os.environ["STORAGE_CONTAINER"])
    test_blob = container_client.get_blob_client("verify-test.txt")
    test_blob.upload_blob(b"test", overwrite=True)
    test_blob.delete_blob()
    print("   OK\n")
except Exception as e:
    print(f"   FALLO: {e}\n")

print("=== Fin de verificación ===")
```

Ejecutalo:

```bash
pip install python-dotenv openai azure-cosmos azure-storage-blob azure-identity
python scripts/verify_setup.py
```

Los cuatro tests deben pasar. Si alguno falla, ir a la sección de solución de problemas.

---

## Solución de problemas comunes

### "Insufficient quota" al desplegar gpt-4.1-mini o gpt-image-2

**Causa:** las suscripciones Azure for Students tienen cuotas reducidas por defecto.

**Solución:**
1. Portal de Foundry → **Operate → Quota** → activá **Show all**.
2. Encontrá el modelo, click en **Request quota**.
3. Indicá uso académico, justificación breve.
4. La aprobación puede tardar entre algunas horas y un día hábil. Si urge, probá otra región con `--query "properties.locations"` antes de pedir aumento.

### "Model not found" al desplegar

**Causa:** el nombre del modelo o la versión cambió desde la fecha de redacción.

**Solución:**
```bash
az cognitiveservices account list-models \
  --name $FOUNDRY_NAME \
  --resource-group $RG \
  --output table | grep -i "image\|4.1"
```

Buscá la versión vigente y reemplazá `--model-version` en el comando.

### "Custom domain required" al usar Entra ID

**Causa:** olvidaste `--custom-domain` en el paso 2.

**Solución:** borrar y recrear el recurso Foundry. No se puede setear el custom domain después.

### El test de imagen funciona pero el JSON no incluye `b64_json` ni `url`

**Causa:** el response_format de gpt-image-2 puede variar; por defecto devuelve `b64_json`. Comprobá con `python3 -m json.tool` para ver el shape real de la respuesta.

### Latencia muy alta en gpt-image-2

**Causa esperada:** generar una imagen toma entre 8 y 25 segundos. Es normal.

**Mitigación en el backend:** invocar la generación de imagen en paralelo (asyncio) mientras devolvés la narrativa primero al frontend; servir la imagen cuando llegue.

---

## Estimación de cuotas necesarias

Para tener una referencia al pedir aumentos:

| Recurso | Cuota mínima recomendada | Cuota cómoda para demo |
|---|---|---|
| gpt-4.1-mini | 10K TPM | 50K TPM |
| gpt-image-2 | 1 unidad de capacidad | 1 unidad |
| Cosmos DB | (serverless, no aplica) | (serverless, no aplica) |
| Blob Storage | 5000 IOPS (default) | sin cambio |

Para el ritmo de uso del TP (estimado 30-50 sesiones de prueba durante todo el desarrollo, más unas 10 sesiones en vivo durante la demo), 10K TPM en el LLM es holgado. El cuello de botella va a ser la velocidad de respuesta del modelo de imagen, no la cuota.

---

## Cleanup al terminar el proyecto

Cuando ya no necesites los recursos, borrá todo el grupo de un comando:

```bash
az group delete --name $RG --yes --no-wait
```

Esto evita consumir crédito por recursos olvidados. Cosmos serverless y Storage cobran muy poco en reposo, pero "muy poco × varios meses × varios recursos" suma.

---

## Referencias

- [Foundry: get started with SDKs and endpoints](https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview)
- [Foundry: models sold directly by Azure](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure)
- [Introducing GPT-image-2 in Microsoft Foundry](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-openais-gpt-image-2-in-microsoft-foundry/4500571)
- [Azure OpenAI pricing](https://azure.microsoft.com/pricing/details/azure-openai/)
- [Azure for Students FAQ](https://azure.microsoft.com/free/students)
