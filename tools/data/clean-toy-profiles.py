"""
Clean all toy profiles from the toy service.

This script:
1. Lists all toys
2. Deletes all avatars
3. Deletes all toys

Admin Role Support:
- Users with Admin.FullAccess role can delete ALL toys (regardless of owner)
- Regular users can only delete their own toys
- See tools/identity/ADMIN_ROLE_SETUP.md for role configuration

Requires:
- TOY_SERVICE_URL environment variable
- AUTH_TOKEN_PATH pointing to valid auth token
- Running toy service
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def load_auth_token() -> dict:
    """Load authentication token from configured path."""
    token_path_str = os.getenv("AUTH_TOKEN_PATH", "../identity/auth_token.json")
    token_path = Path(__file__).parent / token_path_str
    
    if not token_path.exists():
        print(f"❌ Auth token not found at: {token_path}")
        print("   Run: python tools/identity/get_auth_token.py")
        sys.exit(1)
    
    with open(token_path) as f:
        token_data = json.load(f)
    
    # Basic expiry check
    import time
    if token_data.get("expires_on", 0) < time.time():
        print("❌ Auth token expired")
        print("   Run: python tools/identity/get_auth_token.py")
        sys.exit(1)
    
    return token_data


def get_auth_headers(token_data: dict) -> dict:
    """Generate authorization headers."""
    return {
        "Authorization": f"Bearer {token_data['token']}",
        "Content-Type": "application/json"
    }


def has_admin_role(token_data: dict) -> bool:
    """Check if user has Admin.FullAccess role."""
    roles = token_data.get('claims', {}).get('roles', [])
    return "Admin.FullAccess" in roles


def main():
    """Clean all toy profiles."""
    print("🧹 Toy Profile Cleanup")
    print("=" * 50)
    
    # Load configuration
    service_url = os.getenv("TOY_SERVICE_URL", "http://localhost:8001")
    print(f"📡 Service URL: {service_url}")
    
    # Load auth token
    try:
        token_data = load_auth_token()
        headers = get_auth_headers(token_data)
        user_oid = token_data['claims'].get('oid')
        is_admin = has_admin_role(token_data)
        
        print(f"✅ Auth token loaded (user: {token_data['claims'].get('preferred_username', 'unknown')})")
        print(f"   User OID: {user_oid}")
        
        if is_admin:
            print(f"   🔑 Admin role: Admin.FullAccess ✓")
            print(f"   ⚠️  You can delete ALL toys (including those owned by others)")
        else:
            print(f"   👤 Admin role: None")
            print(f"   ℹ️  You can only delete your own toys")
    except Exception as e:
        print(f"❌ Failed to load auth token: {e}")
        sys.exit(1)
    
    print()
    
    # List all toys
    print("📋 Fetching toy list...")
    try:
        response = httpx.get(f"{service_url}/toy", headers=headers, timeout=10.0)
        response.raise_for_status()
        response_data = response.json()
        all_toys = response_data.get("items", [])
        print(f"✅ Found {len(all_toys)} total toys")
    except httpx.HTTPError as e:
        print(f"❌ Failed to fetch toys: {e}")
        sys.exit(1)
    
    # Determine which toys can be deleted
    if is_admin:
        # Admin can delete all toys
        toys_to_delete = all_toys
        toys_skipped = []
    else:
        # Regular user can only delete their own toys
        toys_to_delete = [toy for toy in all_toys if toy.get("owner_oid") == user_oid]
        toys_skipped = [toy for toy in all_toys if toy.get("owner_oid") != user_oid]
    
    if toys_skipped:
        print(f"⚠️  {len(toys_skipped)} toys owned by other users (will be skipped)")
    
    print(f"🎯 {len(toys_to_delete)} toys will be deleted")
    
    if not toys_to_delete:
        if is_admin:
            print("\n✨ No toys to clean (database is empty)")
        else:
            print("\n✨ No toys to clean (you don't own any)")
        return
    
    print()
    
    # Delete avatars first
    print("🖼️  Deleting avatars...")
    avatar_deleted = 0
    avatar_skipped = 0
    avatar_failed = 0
    
    for toy in toys_to_delete:
        toy_id = toy["id"]
        toy_name = toy["name"]
        has_avatar = toy.get("has_avatar", False)
        is_owner = toy.get("owner_oid") == user_oid
        owner_indicator = "" if is_owner else " [other owner]"
        
        if not has_avatar:
            print(f"   ⏭️  {toy_name}{owner_indicator} (no avatar)")
            avatar_skipped += 1
            continue
        
        try:
            response = httpx.delete(
                f"{service_url}/toy/{toy_id}/avatar",
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 204:
                print(f"   ✅ {toy_name}{owner_indicator}")
                avatar_deleted += 1
            else:
                print(f"   ⚠️  {toy_name}{owner_indicator} (status {response.status_code})")
                avatar_failed += 1
        except Exception as e:
            print(f"   ❌ {toy_name}{owner_indicator}: {e}")
            avatar_failed += 1
    
    print(f"\n📊 Avatars: {avatar_deleted} deleted, {avatar_skipped} skipped, {avatar_failed} failed")
    print()
    
    # Delete toys
    print("🧸 Deleting toys...")
    toy_deleted = 0
    toy_failed = 0
    
    for toy in toys_to_delete:
        toy_id = toy["id"]
        toy_name = toy["name"]
        is_owner = toy.get("owner_oid") == user_oid
        owner_indicator = "" if is_owner else " [other owner]"
        
        try:
            response = httpx.delete(
                f"{service_url}/toy/{toy_id}",
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 204:
                print(f"   ✅ {toy_name}{owner_indicator}")
                toy_deleted += 1
            else:
                print(f"   ⚠️  {toy_name}{owner_indicator} (status {response.status_code})")
                toy_failed += 1
        except Exception as e:
            print(f"   ❌ {toy_name}{owner_indicator}: {e}")
            toy_failed += 1
    
    print(f"\n📊 Toys: {toy_deleted} deleted, {toy_failed} failed")
    print()
    
    # Summary
    if toy_failed == 0:
        print("✨ Cleanup complete!")
    else:
        print(f"⚠️  Cleanup complete with {toy_failed} failures")


if __name__ == "__main__":
    main()
