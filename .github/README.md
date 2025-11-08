# GitHub Configuration

This directory contains GitHub-specific configuration and documentation.

## Contents

### Workflows

- **`workflows/build-toy.yml`** - CI/CD pipeline for toy service
- **`workflows/build-trip.yml`** - CI/CD pipeline for trip service
- **`workflows/build-web.yml`** - CI/CD pipeline for web frontend

Each workflow builds and pushes container images to Azure Container Registry when code changes are detected.

### Documentation

- **`CI_CD.md`** - Comprehensive guide for the CI/CD pipelines including setup, usage, and troubleshooting

## Quick Start

### Setup CI/CD Pipeline

1. **Create Azure Service Principal**:
   ```powershell
   az ad sp create-for-rbac --name "github-actions-acr-push" --role "AcrPush" --scopes "/subscriptions/<subscription-id>/resourceGroups/rg-appdemo" --sdk-auth
   ```

2. **Add GitHub Secret**:
   - Go to repository **Settings > Secrets and variables > Actions**
   - Create secret named `AZURE_CREDENTIALS`
   - Paste the JSON output from step 1

3. **Trigger Workflows**:
   - Push changes to `main` branch in service directories (automatic)
   - Or use **Actions > [Select Workflow] > Run workflow** (manual)

## Workflow Triggers

Each workflow automatically runs when:
- Code is pushed to `main` branch in its service directory
- Changes are made to `src/shared/` (triggers both toy and trip workflows)
- Manually triggered via GitHub Actions UI

| Workflow | Triggers On |
|----------|-------------|
| Build and Push Toy Service | `src/services/toy/**` or `src/shared/**` |
| Build and Push Trip Service | `src/services/trip/**` or `src/shared/**` |
| Build and Push Web Frontend | `src/web/**` |

See [CI_CD.md](CI_CD.md) for detailed documentation.
