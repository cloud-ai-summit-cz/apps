# ArgoCD Installation

This directory contains the Helm values configuration for installing ArgoCD on AKS Automatic clusters.

## Overview

ArgoCD is installed via the official Helm chart with custom values configured for AKS Automatic's Deployment Safeguards policies.

## Files

- `argocd-values.yaml` - Helm values file with resource limits for all components

## AKS Automatic Compliance

AKS Automatic clusters enforce [Deployment Safeguards](https://learn.microsoft.com/en-us/azure/aks/deployment-safeguards) which require:
- CPU and memory limits on all containers
- CPU and memory limits on all init containers

The `argocd-values.yaml` file configures these limits to satisfy the policies while maintaining ArgoCD functionality.

### Resource Configuration

All ArgoCD components are configured with:

**Init Containers:**
- CPU limit: 100m
- Memory limit: 128Mi
- CPU request: 50m
- Memory request: 64Mi

**Main Containers:**
- CPU limit: 500m
- Memory limit: 512Mi
- CPU request: 100m-250m (varies by component)
- Memory request: 128Mi-256Mi (varies by component)

## Installation

ArgoCD is automatically installed during infrastructure deployment via the `.github/workflows/deploy-infra.yml` workflow.

### Manual Installation

To install ArgoCD manually:

```bash
# Add Helm repository
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install ArgoCD
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --version 7.7.11 \
  --values infra/argocd-values.yaml \
  --wait
```

### Upgrade

To upgrade ArgoCD:

```bash
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --version 7.7.11 \
  --values infra/argocd-values.yaml \
  --wait
```

## Access ArgoCD UI

Get the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Port-forward to access the UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Then access at: https://localhost:8080

Username: `admin`
Password: (from the secret above)

## Configuration

### Repository Access

The GitHub Actions workflow automatically configures repository access using the `ARGOCD_REPO_TOKEN` secret.

To manually add repository credentials:

```bash
kubectl create secret generic repo-apps \
  --namespace argocd \
  --from-literal=type=git \
  --from-literal=url=https://github.com/cloud-ai-summit-cz/apps.git \
  --from-literal=username=git \
  --from-literal=password=<YOUR_TOKEN>
  
kubectl label secret repo-apps -n argocd argocd.argoproj.io/secret-type=repository
```

## Troubleshooting

### Policy Violations

If you encounter policy violations about resource limits:

1. Ensure all containers have resource limits defined
2. Ensure all init containers have resource limits defined
3. Check the Deployment Safeguards compliance:
   ```bash
   az aks safeguards show --resource-group rg-appdemo --name <cluster-name>
   ```

### Exclude Namespace from Policies (Optional)

To exclude the ArgoCD namespace from Deployment Safeguards:

```bash
az aks safeguards update \
  --resource-group rg-appdemo \
  --name <cluster-name> \
  --level Enforce \
  --excluded-ns argocd
```

⚠️ **Note:** Excluding namespaces reduces governance oversight. Only use when necessary.

## Version

Current Helm chart version: `7.7.11`

To check for updates:
```bash
helm search repo argo/argo-cd --versions
```

## References

- [ArgoCD Official Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Helm Chart](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd)
- [AKS Deployment Safeguards](https://learn.microsoft.com/en-us/azure/aks/deployment-safeguards)
