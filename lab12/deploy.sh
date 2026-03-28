#!/bin/bash
set -e

# Configuration
RESOURCE_GROUP="rg-maf-workshop"
LOCATION="eastus2"
ACR_NAME="mafworkshopacr$(openssl rand -hex 3)"
APP_NAME="ai-advisory-board"
ENVIRONMENT_NAME="maf-workshop-env"
AZURE_OPENAI_ENDPOINT="https://letsaifoundryprj-resource.openai.azure.com"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5.2"

echo "🚀 Deploying AI Advisory Board to Azure Container Apps"
echo "=================================================="

# Step 1: Create Resource Group
echo "📦 Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Step 2: Create ACR
echo "🏗️  Creating Container Registry..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true --output none

# Step 3: Build and push image
echo "🐳 Building Docker image..."
az acr build --registry "$ACR_NAME" --image "$APP_NAME:latest" --file Dockerfile . --output none

# Step 4: Create Container Apps Environment
echo "🌐 Creating Container Apps environment..."
az containerapp env create --name "$ENVIRONMENT_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Step 5: Deploy
echo "🚢 Deploying container app..."
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

# Step 6: Get URL
APP_URL=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "=================================================="
echo "✅ Deployment complete!"
echo "🌐 App URL: https://$APP_URL"
echo "🏥 Health:  https://$APP_URL/health"
echo ""
echo "📋 Next: Assign 'Cognitive Services OpenAI User' role to managed identity"

PRINCIPAL_ID=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "identity.principalId" -o tsv)
echo "   Principal ID: $PRINCIPAL_ID"
echo ""
echo "🧹 Cleanup: az group delete --name $RESOURCE_GROUP --yes --no-wait"
echo "=================================================="
