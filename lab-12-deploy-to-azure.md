# Lab 12 — Deploy to Azure

## Objective

Deploy the Lab 11 multi-agent web app backend to **Azure Container Apps** — making it publicly accessible with **Managed Identity** for secure, passwordless authentication to Azure OpenAI.

---

## Concepts

### Deployment Architecture

```
┌──────────────────┐         ┌────────────────────────────────┐
│  Frontend        │  HTTPS  │  Azure Container Apps          │
│  (Vercel/local)  │◄───────►│                                │
│  CopilotKit      │         │  ┌────────────────────────┐    │
│                  │         │  │  FastAPI + AG-UI         │    │
└──────────────────┘         │  │  agent-framework         │    │
                             │  └──────────┬─────────────┘    │
                             │             │                   │
                             │   Managed Identity              │
                             │             │                   │
                             │  ┌──────────▼─────────────┐    │
                             │  │  Azure OpenAI (Foundry) │    │
                             │  │  gpt-5.2                │    │
                             │  └────────────────────────┘    │
                             └────────────────────────────────┘
```

### Why Azure Container Apps?

- **Serverless containers** — no infrastructure to manage
- **Built-in scaling** — scales to zero when not in use
- **Managed Identity** — `DefaultAzureCredential` works automatically
- **HTTPS by default** — production-ready out of the box

### How DefaultAzureCredential Works in Azure

Locally, it used your Azure CLI session. In Azure Container Apps, it uses **Managed Identity** — same code, zero changes:

```
Local:    DefaultAzureCredential() → AzureCliCredential (az login)
Azure:    DefaultAzureCredential() → ManagedIdentityCredential (automatic)
```

---

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- An Azure subscription with permissions to create resources
- The Lab 11 backend code (`lab11/server.py` and `lab11/requirements.txt`)

---

## Step 1: Create the Dockerfile

Create `lab12/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY .env .

# Expose port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Copy the server files:

```bash
mkdir -p lab12
cp lab11/server.py lab12/
cp lab11/requirements.txt lab12/
cp lab11/.env lab12/
```

---

## Step 2: Set Up Azure Resources

Create `lab12/deploy.sh`:

```bash
#!/bin/bash
set -e

# ──────────────────────────────────────────
# Configuration — customize these values
# ──────────────────────────────────────────
RESOURCE_GROUP="rg-maf-workshop"
LOCATION="eastus2"
ACR_NAME="mafworkshopacr$(openssl rand -hex 3)"
APP_NAME="ai-advisory-board"
ENVIRONMENT_NAME="maf-workshop-env"

# Azure OpenAI endpoint (from your Foundry deployment)
AZURE_OPENAI_ENDPOINT="https://letsaifoundryprj-resource.openai.azure.com"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5.2"

echo "🚀 Deploying AI Advisory Board to Azure Container Apps"
echo "=================================================="

# ── Step 1: Create Resource Group ──
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# ── Step 2: Create Azure Container Registry ──
echo "🏗️  Creating Azure Container Registry: $ACR_NAME"
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none

# ── Step 3: Build and push the Docker image ──
echo "🐳 Building and pushing Docker image..."
az acr build \
    --registry "$ACR_NAME" \
    --image "$APP_NAME:latest" \
    --file Dockerfile \
    . \
    --output none

# ── Step 4: Create Container Apps Environment ──
echo "🌐 Creating Container Apps environment: $ENVIRONMENT_NAME"
az containerapp env create \
    --name "$ENVIRONMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# ── Step 5: Deploy to Container Apps with Managed Identity ──
echo "🚢 Deploying container app: $APP_NAME"
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_NAME" \
    --image "$ACR_LOGIN_SERVER/$APP_NAME:latest" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_NAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 3 \
    --env-vars \
        "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
        "AZURE_OPENAI_DEPLOYMENT_NAME=$AZURE_OPENAI_DEPLOYMENT_NAME" \
    --system-assigned \
    --output none

# ── Step 6: Get the app URL ──
APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv)

echo ""
echo "=================================================="
echo "✅ Deployment complete!"
echo "=================================================="
echo ""
echo "🌐 App URL: https://$APP_URL"
echo "🏥 Health:  https://$APP_URL/health"
echo ""

# ── Step 7: Assign Azure OpenAI role to Managed Identity ──
echo "🔐 Assigning Cognitive Services OpenAI User role..."

# Get the managed identity principal ID
PRINCIPAL_ID=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "identity.principalId" \
    --output tsv)

# Get the Azure OpenAI resource ID
# Adjust the resource group name if your OpenAI resource is in a different RG
OPENAI_RESOURCE_ID=$(az cognitiveservices account show \
    --name "letsaifoundryprj-resource" \
    --resource-group "$RESOURCE_GROUP" \
    --query id \
    --output tsv 2>/dev/null || echo "MANUAL_STEP_NEEDED")

if [ "$OPENAI_RESOURCE_ID" != "MANUAL_STEP_NEEDED" ]; then
    az role assignment create \
        --assignee "$PRINCIPAL_ID" \
        --role "Cognitive Services OpenAI User" \
        --scope "$OPENAI_RESOURCE_ID" \
        --output none
    echo "   ✅ Role assigned successfully"
else
    echo "   ⚠️  Could not find OpenAI resource automatically."
    echo "   Please manually assign 'Cognitive Services OpenAI User' role to:"
    echo "   Principal ID: $PRINCIPAL_ID"
    echo ""
    echo "   Run:"
    echo "   az role assignment create \\"
    echo "     --assignee $PRINCIPAL_ID \\"
    echo "     --role 'Cognitive Services OpenAI User' \\"
    echo "     --scope <your-openai-resource-id>"
fi

echo ""
echo "=================================================="
echo "📋 Next Steps:"
echo "=================================================="
echo "1. Test the health endpoint:"
echo "   curl https://$APP_URL/health"
echo ""
echo "2. Update your CopilotKit frontend to use the deployed URL:"
echo "   Change runtimeUrl to: https://$APP_URL/api/copilotkit"
echo ""
echo "3. To update the frontend, edit lab11/frontend/src/app/page.tsx:"
echo "   runtimeUrl=\"https://$APP_URL/api/copilotkit\""
echo ""
echo "4. To clean up resources when done:"
echo "   az group delete --name $RESOURCE_GROUP --yes --no-wait"
echo "=================================================="
```

---

## Step 3: Deploy

```bash
cd lab12
chmod +x deploy.sh
./deploy.sh
```

---

## Step 4: Verify the Deployment

```bash
# Health check
curl https://<your-app>.azurecontainerapps.io/health

# Expected: {"status": "healthy", "service": "AI Advisory Board"}
```

---

## Step 5: Connect the Frontend

Update your CopilotKit frontend to point at the deployed backend:

In `lab11/frontend/src/app/page.tsx`, change:

```tsx
// Before (local development):
<CopilotKit runtimeUrl="http://localhost:8000/api/copilotkit">

// After (Azure deployment):
<CopilotKit runtimeUrl="https://<your-app>.azurecontainerapps.io/api/copilotkit">
```

You'll also need to update the CORS configuration in `server.py` to allow your frontend's production domain.

---

## Step 6: Clean Up (when done)

```bash
# Delete all resources created by this lab
az group delete --name rg-maf-workshop --yes --no-wait
```

---

## Key Takeaways

1. **Azure Container Apps** provides serverless container hosting with built-in scaling and HTTPS.
2. **Managed Identity** enables `DefaultAzureCredential` to work automatically — no secrets to manage.
3. The **same code** runs locally and in Azure — `DefaultAzureCredential` handles the auth difference.
4. **`az acr build`** builds and pushes Docker images without needing Docker installed locally.
5. Assign the **Cognitive Services OpenAI User** role to the managed identity for Azure OpenAI access.
6. The AG-UI endpoint just needs the URL updated in the CopilotKit frontend — everything else works unchanged.

---

## Workshop Complete! 🎉

Congratulations! You've completed the entire Microsoft Agent Framework workshop. Here's what you've built:

| Lab | What You Built |
|-----|---------------|
| 01 | Your first agent with streaming |
| 02 | Agent with custom function tools |
| 03 | Agent with MCP tools (Microsoft Learn) |
| 04 | Multi-turn conversations with sessions |
| 05 | Hierarchical agent composition |
| 06 | Sequential pipeline (blog post creator) |
| 07 | Concurrent analysis (investment analyzer) |
| 08 | Handoff routing (customer support) |
| 09 | Group chat debate (product review) |
| 10 | Magentic planning (research automation) |
| 11 | Web app with CopilotKit + AG-UI |
| 12 | Azure Container Apps deployment |

### Resources for Further Learning

- [Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/overview/?pivots=programming-language-python)
- [Agent Framework GitHub](https://github.com/microsoft/agent-framework)
- [AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [AG-UI Protocol](https://docs.ag-ui.com/introduction)
- [CopilotKit Docs](https://docs.copilotkit.ai/)
