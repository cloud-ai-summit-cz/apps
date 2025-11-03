# Admin Role Setup Guide

This guide explains how to configure and assign the `Admin.FullAccess` role in Entra ID.

## Overview

The `Admin.FullAccess` role grants full administrative access to all toys in the system, regardless of ownership. This is useful for:
- Admin users managing the system
- Support team troubleshooting issues
- Cleanup/maintenance scripts
- Testing scenarios

## Option 1: Automated Setup (Recommended)

### If creating a NEW app registration:

```powershell
cd tools/identity
uv run python create_app_registration.py --name "ToyTrips-Dev"
```

The script automatically creates three app roles:
- `Toy.ReadWrite` - For regular users
- `Admin.FullAccess` - For administrators (NEW)
- `System.Service` - For system/background services

### If you ALREADY have an app registration:

You need to add the `Admin.FullAccess` role manually (see Option 2 below).

## Option 2: Manual Setup via Azure Portal

### Step 1: Navigate to App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Entra ID** (formerly Azure AD)
3. Click **App registrations** in the left menu
4. Find and click your ToyTrips app (e.g., "ToyTrips-Dev")

### Step 2: Add App Role

1. In the left menu, click **App roles**
2. Click **+ Create app role**
3. Fill in the details:

   | Field | Value |
   |-------|-------|
   | Display name | `Admin - Full Access` |
   | Allowed member types | **Users/Groups** |
   | Value | `Admin.FullAccess` |
   | Description | `Full administrative access to all toys regardless of ownership` |
   | Do you want to enable this app role? | ✅ Checked |

4. Click **Apply**

### Step 3: Verify Role Created

You should now see three app roles:
- ✅ Toy Read/Write (`Toy.ReadWrite`) - Users/Groups
- ✅ Admin - Full Access (`Admin.FullAccess`) - Users/Groups
- ✅ System Service (`System.Service`) - Applications

## Assigning the Admin Role to Users

### Via Azure Portal (Recommended):

1. Go to **Entra ID** → **Enterprise applications**
2. Find your ToyTrips app in the list
3. Click **Users and groups** in the left menu
4. Click **+ Add user/group**
5. Click **Users** - select the user(s) who should be admins
6. Click **Select a role**
7. Choose **Admin - Full Access**
8. Click **Assign**

### Via Azure CLI:

```powershell
# Get the app's service principal ID
$spId = az ad sp list --display-name "ToyTrips-Dev" --query "[0].id" -o tsv

# Get the admin role ID
$roleId = az ad sp show --id $spId --query "appRoles[?value=='Admin.FullAccess'].id" -o tsv

# Get the user's object ID
$userId = az ad user show --id "user@domain.com" --query "id" -o tsv

# Assign the role
az rest --method POST --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignments" --headers "Content-Type=application/json" --body "{`"principalId`": `"$userId`", `"resourceId`": `"$spId`", `"appRoleId`": `"$roleId`"}"
```

## Verifying Role Assignment

### Check Token Claims:

After assigning the role, get a new token and check the claims:

```powershell
cd tools/identity
uv run python get_auth_token.py
```

Look at the `auth_token.json` file - you should see in the claims:
```json
{
  "claims": {
    "roles": ["Admin.FullAccess"],
    ...
  }
}
```

### Test with Cleanup Script:

```powershell
cd tools/data
uv run python clean-toy-profiles.py
```

With the admin role, you should be able to delete ALL toys (not just your own).

## How It Works

### In the Code:

The `require_owner()` function in `src/shared/auth/permissions.py` checks:

1. **First**: Does the user have `Admin.FullAccess` role? → Allow access
2. **Second**: Does the user own the resource? → Allow access
3. **Otherwise**: Return 403 Forbidden

Example:
```python
def require_owner(auth_ctx: AuthContext, owner_oid: str) -> None:
    # Admins bypass ownership check
    if "Admin.FullAccess" in auth_ctx.principal.roles:
        return
    
    # Regular users must own the resource
    if auth_ctx.principal.oid != owner_oid:
        raise HTTPException(status_code=403, detail="Access denied")
```

### In the Token:

When a user with the admin role authenticates, their JWT token includes:
```json
{
  "roles": ["Admin.FullAccess"],
  "oid": "user-object-id",
  "scp": "App.Access"
}
```

The token validation automatically extracts roles, no additional configuration needed.

## Security Best Practices

1. **Assign sparingly**: Only give admin role to trusted users
2. **Audit regularly**: Review who has admin access
3. **Use groups**: Assign role to a group (e.g., "ToyTrips Admins") for easier management
4. **Monitor usage**: Log admin actions for audit trails
5. **Rotate regularly**: Review and remove access for users who no longer need it

## Troubleshooting

### "I assigned the role but it's not in the token"

- Wait 5-10 minutes for changes to propagate
- Get a NEW token (old tokens don't update)
- Check you assigned to the correct app (Enterprise Application, not App Registration)
- Verify role assignment in Portal: Enterprise Apps → Your App → Users and groups

### "Scripts still show 403 errors"

- Verify token has the role: `cat tools/identity/auth_token.json`
- Check `require_owner()` function has admin check
- Ensure token isn't expired: `uv run python get_auth_token.py`

### "Can't find Admin.FullAccess role"

- Check App Registration → App roles (role definition)
- Check Enterprise Application → App roles (same list)
- Recreate the app registration if needed

## Alternative: Using a Security Group

If you prefer using a security group instead:

**Pros:**
- Centralized group management
- Works across multiple apps

**Cons:**
- Requires enabling group claims in app registration
- Adds group IDs to every token (token bloat)
- OR requires Graph API calls to check membership (slower, more complex)
- Not the recommended Azure pattern for app permissions

**Verdict:** Stick with App Roles - they're designed for this exact scenario.

## References

- [Azure AD App Roles](https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps)
- [Assign users to app roles](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/add-application-portal-assign-users)
- [Role-based access control](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
