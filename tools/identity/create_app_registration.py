#!/usr/bin/env python3
"""
Create Entra ID App Registration for ToyTrips Application

Creates an app registration with:
- API permissions (app roles: Toy.ReadWrite, System.Service)
- OAuth2 permission scope (App.Access)
- Redirect URIs for local development
- Service principal
- Stores details in app_registration.json for reuse

Requirements:
- Azure CLI authenticated with permissions to create app registrations
- Run from tools/identity directory

Usage:
    python create_app_registration.py --name "ToyTrips-Dev"
"""

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
import platform


def run_az_command(cmd: list[str]) -> dict[str, Any]:
    """Execute Azure CLI command and return JSON result."""
    try:
        # On Windows, use az.cmd explicitly
        if platform.system() == "Windows" and cmd[0] == "az":
            cmd[0] = "az.cmd"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        sys.exit(1)


def create_app_registration(display_name: str) -> dict[str, Any]:
    """
    Create Entra ID app registration with required configuration.
    
    Returns dict with appId, objectId, tenantId, and identifierUris.
    """
    print(f"Creating app registration: {display_name}")
    
    # Generate unique scope ID
    scope_id = str(uuid.uuid4())
    
    # App roles for the API
    app_roles = [
        {
            "allowedMemberTypes": ["User"],
            "description": "Read and write toy data",
            "displayName": "Toy Read/Write",
            "id": str(uuid.uuid4()),
            "isEnabled": True,
            "value": "Toy.ReadWrite"
        },
        {
            "allowedMemberTypes": ["User"],
            "description": "Full administrative access to all toys regardless of ownership",
            "displayName": "Admin - Full Access",
            "id": str(uuid.uuid4()),
            "isEnabled": True,
            "value": "Admin.FullAccess"
        },
        {
            "allowedMemberTypes": ["Application"],
            "description": "System service access for background operations",
            "displayName": "System Service",
            "id": str(uuid.uuid4()),
            "isEnabled": True,
            "value": "System.Service"
        }
    ]
    
    # OAuth2 permission scope
    oauth2_permissions = {
        "oauth2PermissionScopes": [
            {
                "id": scope_id,
                "adminConsentDescription": "Access ToyTrips API",
                "adminConsentDisplayName": "Access ToyTrips API",
                "userConsentDescription": "Access ToyTrips API on your behalf",
                "userConsentDisplayName": "Access ToyTrips API",
                "isEnabled": True,
                "type": "User",
                "value": "App.Access"
            }
        ]
    }
    
    # Redirect URIs for local development (SPA)
    redirect_uris = [
        "http://localhost:3000",
        "http://localhost:3000/auth/callback"
    ]
    
    # Create the app registration (initial creation without platform-specific redirect URIs)
    create_cmd = [
        "az", "ad", "app", "create",
        "--display-name", display_name,
        "--sign-in-audience", "AzureADMyOrg"
    ]
    
    app = run_az_command(create_cmd)
    app_id = app["appId"]
    object_id = app["id"]
    
    print(f"✓ Created app registration (App ID: {app_id})")
    
    # Configure SPA platform with redirect URIs using Graph API
    # Azure CLI doesn't support --spa-redirect-uris, so we use Graph API directly
    print("Configuring SPA platform...")
    spa_config = {
        "spa": {
            "redirectUris": redirect_uris
        }
    }
    
    # Write temp file for Graph API request
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(spa_config, f)
        temp_file = f.name
    
    try:
        run_az_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://graph.microsoft.com/v1.0/applications/{object_id}",
            "--headers", "Content-Type=application/json",
            "--body", f"@{temp_file}"
        ])
        print(f"✓ Configured SPA platform with redirect URIs")
    finally:
        Path(temp_file).unlink()  # Clean up temp file
    
    # Set identifier URI
    identifier_uri = f"api://{app_id}"
    run_az_command([
        "az", "ad", "app", "update",
        "--id", app_id,
        "--identifier-uris", identifier_uri
    ])
    print(f"✓ Set identifier URI: {identifier_uri}")
    
    # Update app roles
    run_az_command([
        "az", "ad", "app", "update",
        "--id", app_id,
        "--app-roles", json.dumps(app_roles)
    ])
    print(f"✓ Added app roles: Toy.ReadWrite, Admin.FullAccess, System.Service")
    
    # Update OAuth2 permissions (exposed API)
    run_az_command([
        "az", "ad", "app", "update",
        "--id", app_id,
        "--set", f"api={json.dumps(oauth2_permissions)}"
    ])
    print(f"✓ Added OAuth2 permission scope: App.Access")
    
    # Get tenant ID
    tenant_info = run_az_command(["az", "account", "show"])
    tenant_id = tenant_info["tenantId"]
    
    # Create service principal
    print("Creating service principal...")
    sp = run_az_command([
        "az", "ad", "sp", "create",
        "--id", app_id
    ])
    print(f"✓ Created service principal")
    
    return {
        "appId": app_id,
        "objectId": object_id,
        "tenantId": tenant_id,
        "identifierUri": identifier_uri,
        "displayName": display_name,
        "scopeId": scope_id,
        "redirectUris": redirect_uris
    }


def save_registration_details(details: dict[str, Any], output_file: Path):
    """Save app registration details to JSON file."""
    with open(output_file, "w") as f:
        json.dump(details, f, indent=2)
    print(f"\n✓ Saved registration details to {output_file}")


def print_summary(details: dict[str, Any]):
    """Print summary of created resources."""
    print("\n" + "="*60)
    print("APP REGISTRATION CREATED SUCCESSFULLY")
    print("="*60)
    print(f"\nDisplay Name:    {details['displayName']}")
    print(f"Application ID:  {details['appId']}")
    print(f"Tenant ID:       {details['tenantId']}")
    print(f"Identifier URI:  {details['identifierUri']}")
    print(f"\nScope:           App.Access")
    print(f"App Roles:       Toy.ReadWrite, Admin.FullAccess, System.Service")
    print(f"\nRedirect URIs:")
    for uri in details['redirectUris']:
        print(f"  - {uri}")
    print(f"\n{'='*60}")
    print("\nNext steps:")
    print("1. Update service configuration with these values:")
    print(f"   TENANT_ID={details['tenantId']}")
    print(f"   APP_ID_URI={details['identifierUri']}")
    print("2. Use get_auth_token.py to obtain a token for testing")
    print("3. Assign users/groups to app roles in Azure Portal if needed")
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Create Entra ID app registration for ToyTrips"
    )
    parser.add_argument(
        "--name",
        default="ToyTrips-Dev",
        help="Display name for the app registration (default: ToyTrips-Dev)"
    )
    parser.add_argument(
        "--output",
        default="app_registration.json",
        help="Output file for registration details (default: app_registration.json)"
    )
    
    args = parser.parse_args()
    output_path = Path(args.output)
    
    # Check if output file already exists
    if output_path.exists():
        response = input(f"Warning: {output_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # Create app registration
    details = create_app_registration(args.name)
    
    # Save details
    save_registration_details(details, output_path)
    
    # Print summary
    print_summary(details)


if __name__ == "__main__":
    main()
