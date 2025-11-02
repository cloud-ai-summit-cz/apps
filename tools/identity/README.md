# Identity Management Tools

Scripts for managing Entra ID app registrations and authentication tokens for ToyTrips application.

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Python 3.11+
- Permissions to create/delete app registrations in your Entra ID tenant

## Scripts

### 1. create_app_registration.py

Creates an Entra ID app registration with proper configuration for ToyTrips:

- OAuth2 permission scope: `App.Access`
- App roles: `Toy.ReadWrite`, `System.Service`
- Redirect URIs for local development
- Service principal

**Usage:**
```bash
cd tools/identity
python create_app_registration.py --name "ToyTrips-Dev"
```

**Output:** `app_registration.json` with app details

### 2. get_auth_token.py

Obtains an authentication token using InteractiveBrowserCredential for local testing.

**Usage:**
```bash
cd tools/identity
python get_auth_token.py
```

This will:
1. Open a browser window for interactive login
2. Prompt you to sign in with your Azure account
3. Request consent for the `App.Access` scope (first time only)
4. Save the token to `auth_token.json`

**Output:** `auth_token.json` with token and claims

**Note:** Uses **user-delegated authentication** (not service principal), so you get a token with your user's `oid` claim. This is perfect for testing user-owned resources.

### 3. cleanup_app_registration.py

Deletes the app registration and service principal.

**Usage:**
```bash
cd tools/identity
python cleanup_app_registration.py
```

**With confirmation:**
```bash
python cleanup_app_registration.py --yes
```

## Workflow

### Initial Setup

1. Create app registration:
   ```bash
   python create_app_registration.py --name "ToyTrips-Dev"
   ```

2. Update service configuration with values from `app_registration.json`:
   ```bash
   # In src/services/toy/.env
   TENANT_ID=<tenant_id>
   APP_ID_URI=<identifier_uri>
   ```

3. Get authentication token:
   ```bash
   python get_auth_token.py
   ```

4. Use token in integration tests or manual API testing:
   ```python
   import json
   with open("tools/identity/auth_token.json") as f:
       token_data = json.load(f)
   
   headers = {"Authorization": f"Bearer {token_data['token']}"}
   response = requests.get("http://localhost:8000/toy", headers=headers)
   ```

### Cleanup

Remove app registration when no longer needed:
```bash
python cleanup_app_registration.py --yes
```

## Files

- `app_registration.json` - App registration details (created by setup script)
- `auth_token.json` - Authentication token for testing (created by token script)
- `.gitignore` - Excludes JSON files with sensitive data

## Security Notes

- Never commit `app_registration.json` or `auth_token.json` to version control
- Tokens expire after 1 hour by default - re-run `get_auth_token.py` to refresh
- For production, use managed identities and Key Vault for secrets
- These scripts are for development/testing only

## Troubleshooting

### "Insufficient privileges to complete the operation"

You need Application Administrator or Global Administrator role in Entra ID.

### "No subscription found"

Ensure Azure CLI is authenticated: `az login`

### Token expired

Tokens typically expire after 1 hour. Re-run:
```bash
python get_auth_token.py
```

### "AADSTS50105: The signed in user is not assigned to a role"

After creating the app registration, assign users in Azure Portal:
1. Go to Enterprise Applications
2. Find your app (ToyTrips-Dev)
3. Users and groups → Add user/group
4. Assign the Toy.ReadWrite role

**Or use admin consent to allow all users:**
1. Go to App registrations → Your app → API permissions
2. Click "Grant admin consent for [Tenant]"
