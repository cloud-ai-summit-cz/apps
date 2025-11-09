using './main.bicep'

param prefix = 'appdemo'
param enablePrivateEndpoints = true
param enablePublicAccess = true

// Retrieve with: az ad signed-in-user show --query id -o tsv
param userObjectId = 'f390dcd0-2062-4542-9a0b-a773bcb0bc81'
param gitHubWorkflowIdentityObjectId = '485658eb-9a3b-4a7c-9f73-2cd78a8865bc'
