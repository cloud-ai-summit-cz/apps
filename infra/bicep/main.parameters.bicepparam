using './main.bicep'

param prefix = 'demo'

// Retrieve with: az ad signed-in-user show --query id -o tsv
param userObjectId = 'f390dcd0-2062-4542-9a0b-a773bcb0bc81'
