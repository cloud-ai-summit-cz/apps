#!/usr/bin/env python3
"""
Get Authentication Token for ToyTrips Local Testing

Authenticates using DefaultAzureCredential and retrieves a token for the ToyTrips API.
Stores the token in auth_token.json for use in integration tests.

Requirements:
- Azure CLI authenticated or other DefaultAzureCredential source (managed identity, etc.)
- app_registration.json with app details (or specify --scope manually)
- azure-identity package installed

Usage:
    python get_auth_token.py
    python get_auth_token.py --scope api://12345678-1234-1234-1234-123456789012/.default
    python get_auth_token.py --output my_token.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from azure.identity import InteractiveBrowserCredential, DefaultAzureCredential
    from azure.core.exceptions import ClientAuthenticationError
except ImportError:
    print("Error: azure-identity package not found", file=sys.stderr)
    print("Install with: uv pip install azure-identity", file=sys.stderr)
    sys.exit(1)


def load_app_registration(file_path: Path) -> dict[str, Any]:
    """Load app registration details to determine scope."""
    if not file_path.exists():
        return None
    
    with open(file_path) as f:
        return json.load(f)


def get_token(scope: str, tenant_id: str = None) -> dict[str, Any]:
    """
    Authenticate and get access token using InteractiveBrowserCredential.
    
    Args:
        scope: OAuth2 scope (e.g., "api://<app-id>/App.Access")
        tenant_id: Optional tenant ID to authenticate against
    
    Returns:
        Dict with token, expires_on, and decoded claims
    """
    print(f"Authenticating for scope: {scope}")
    if tenant_id:
        print(f"Tenant: {tenant_id}")
    
    try:
        # Use InteractiveBrowserCredential for user authentication
        # This will open a browser window for interactive login
        credential = InteractiveBrowserCredential(tenant_id=tenant_id) if tenant_id else InteractiveBrowserCredential()
        token = credential.get_token(scope)
        
        print(f"✓ Successfully obtained token")
        
        # Decode token claims (basic - no validation, just for info)
        import base64
        token_parts = token.token.split('.')
        if len(token_parts) >= 2:
            # Add padding if needed
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
        else:
            claims = {}
        
        # Convert expires_on to ISO format
        expires_on_dt = datetime.fromtimestamp(token.expires_on, tz=timezone.utc)
        
        return {
            "token": token.token,
            "expires_on": token.expires_on,
            "expires_on_iso": expires_on_dt.isoformat(),
            "scope": scope,
            "obtained_at": datetime.now(timezone.utc).isoformat(),
            "claims": {
                "aud": claims.get("aud"),
                "iss": claims.get("iss"),
                "oid": claims.get("oid"),
                "appid": claims.get("appid"),
                "scp": claims.get("scp"),
                "roles": claims.get("roles", [])
            }
        }
    
    except ClientAuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print("1. Ensure you have access to the application in Azure Portal", file=sys.stderr)
        print("2. Verify the scope is correct (should be api://<app-id>/App.Access)", file=sys.stderr)
        print("3. Check that the app registration allows user authentication", file=sys.stderr)
        print("4. You may need admin consent for the scope", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def save_token(token_data: dict[str, Any], output_file: Path):
    """Save token data to JSON file."""
    with open(output_file, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"✓ Saved token to {output_file}")


def print_token_info(token_data: dict[str, Any]):
    """Print token information."""
    print("\n" + "="*60)
    print("AUTHENTICATION TOKEN OBTAINED")
    print("="*60)
    print(f"\nScope:       {token_data['scope']}")
    print(f"Expires:     {token_data['expires_on_iso']}")
    print(f"\nClaims:")
    claims = token_data['claims']
    print(f"  Audience:  {claims.get('aud', 'N/A')}")
    print(f"  Issuer:    {claims.get('iss', 'N/A')}")
    print(f"  User OID:  {claims.get('oid', 'N/A')}")
    print(f"  App ID:    {claims.get('appid', 'N/A')}")
    print(f"  Scope:     {claims.get('scp', 'N/A')}")
    print(f"  Roles:     {', '.join(claims.get('roles', [])) or 'None'}")
    print(f"\n{'='*60}")
    print("\nUsage in integration tests:")
    print('  with open("auth_token.json") as f:')
    print('      token_data = json.load(f)')
    print('  headers = {"Authorization": f"Bearer {token_data[\'token\']}"}')
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Get authentication token for ToyTrips local testing"
    )
    parser.add_argument(
        "--scope",
        help="OAuth2 scope (default: api://<app-id>/App.Access from app_registration.json)"
    )
    parser.add_argument(
        "--tenant-id",
        help="Tenant ID (default: from app_registration.json)"
    )
    parser.add_argument(
        "--app-file",
        default="app_registration.json",
        help="App registration details file (default: app_registration.json)"
    )
    parser.add_argument(
        "--output",
        default="auth_token.json",
        help="Output file for token (default: auth_token.json)"
    )
    
    args = parser.parse_args()
    output_path = Path(args.output)
    
    # Determine scope and tenant
    if args.scope:
        scope = args.scope
        tenant_id = args.tenant_id
    else:
        app_details = load_app_registration(Path(args.app_file))
        if not app_details:
            print(f"Error: {args.app_file} not found", file=sys.stderr)
            print("Either create app registration first or specify --scope manually", file=sys.stderr)
            sys.exit(1)
        
        app_id = app_details.get("appId")
        tenant_id = app_details.get("tenantId")
        if not app_id:
            print("Error: appId not found in registration file", file=sys.stderr)
            sys.exit(1)
        
        # Use the App.Access scope (user-delegated, not /.default)
        scope = f"api://{app_id}/App.Access"
    
    # Get token
    token_data = get_token(scope, tenant_id)
    
    # Save token
    save_token(token_data, output_path)
    
    # Print info
    print_token_info(token_data)


if __name__ == "__main__":
    main()
