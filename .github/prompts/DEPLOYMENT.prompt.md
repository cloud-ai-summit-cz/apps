---
agent: agent
---
We have done a lot of changes with deployment and want to make sure our #file:DEPLOYMENT.md is up to date. Make document short and sweet, not too much of text, rather structured well and to the point, pretty short.

Go to our env folder to understand various stages of deployments into AKS using argo - infra_config/azure.yaml as bridge between infra (Bicep) and layers on top, bootstrap with app of apps for applications (our services) and kubernetes platform (cert manager, gateway), than platform and apps folders.

Analyze and understand all helm-charts in that folder to understand what is there we are deploying.

Also look into infra/bicep to understand how we deploy underlying infrastructure, RBAC and so on.

Then analyze out .gihub/workflows so you know how we build containers (and fill in values about registry and image tag into our git repo) and deploy infra (together with bootstrapping argo).

Work extensively, but you must change only ONE file and that is our `docs/DEPLOYMENT.md`. Again - remember to keep document structured, short, easy to navigate. Do not copy and paste information from deployment files, we can read this ourselves. Focus on architecture, process, layers, non-obvious things.