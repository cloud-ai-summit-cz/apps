# Platform NGINX Ingress Controller

This Helm chart is a wrapper around the official [ingress-nginx](https://github.com/kubernetes/ingress-nginx) chart, configured for Azure Kubernetes Service (AKS) with static public IP integration.

## Features

- **Static Public IP**: Uses pre-created Azure public IP with DNS label
- **High Availability**: 2 replicas with proper resource limits
- **Azure Load Balancer Integration**: Configured with health probes
- **Monitoring Ready**: Metrics endpoint enabled

## Configuration

The chart accepts Azure infrastructure outputs via ArgoCD's multi-source pattern in `azure.yaml`:

```yaml
ingress-nginx:
  controller:
    service:
      annotations:
        service.beta.kubernetes.io/azure-pip-name: "pip-myapp-abc123-ingress"
        service.beta.kubernetes.io/azure-load-balancer-resource-group: "rg-myapp-abc123"
```

These values are automatically injected from the infrastructure deployment.

## Deployment

This chart is deployed via ArgoCD as part of the platform infrastructure. See `env/staging/platform/ingress-controller-app.yaml`.

## Ingress Class

The chart creates an ingress class named `nginx` which is set as the default for the cluster.
