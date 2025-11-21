# Service Deployment Plan – toy

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Pipelines
- CI build and publish Docker image to ACR.
- GitOps via ArgoCD using Helm chart `helm-charts/toy/` and environment values.

## Environments
Fill in mapping from staging/production to image tags and configuration.

## Release Steps
Summarize how toy service is rolled out, verified, and rolled back.
