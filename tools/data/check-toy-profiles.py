"""
Check toy profiles in the toy service.

This script:
1. Lists all toys
2. Downloads avatars to verify they work (doesn't save)
3. Prints summary

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


def format_bytes(size: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"


def main():
    """Check toy profiles and avatars."""
    print("🔍 Toy Profile Check")
    print("=" * 50)
    
    # Load configuration
    service_url = os.getenv("TOY_SERVICE_URL", "http://localhost:8001")
    print(f"📡 Service URL: {service_url}")
    
    # Load auth token
    try:
        token_data = load_auth_token()
        headers = get_auth_headers(token_data)
        user_oid = token_data['claims'].get('oid')
        print(f"✅ Auth token loaded (user: {token_data['claims'].get('preferred_username', 'unknown')})")
        print(f"   User OID: {user_oid}")
    except Exception as e:
        print(f"❌ Failed to load auth token: {e}")
        sys.exit(1)
    
    print()
    
    # List all toys
    print("📋 Fetching toy list...")
    try:
        # Use a high limit to get all toys (API default is only 20)
        response = httpx.get(
            f"{service_url}/toy",
            headers=headers,
            params={"limit": 1000},  # High limit to get all toys
            timeout=10.0
        )
        response.raise_for_status()
        response_data = response.json()
        toys = response_data.get("items", [])
        total = response_data.get("total", len(toys))
        print(f"✅ Found {len(toys)} toys (total in database: {total})")
    except httpx.HTTPError as e:
        print(f"❌ Failed to fetch toys: {e}")
        sys.exit(1)
    
    if not toys:
        print("\n✨ No toys found")
        return
    
    print()
    print("🧸 Toy Profiles")
    print("-" * 50)
    
    # Check each toy and avatar
    avatar_ok = 0
    avatar_missing = 0
    avatar_failed = 0
    owned_count = 0
    
    for idx, toy in enumerate(toys, 1):
        toy_id = toy["id"]
        toy_name = toy["name"]
        owner_oid = toy.get("owner_oid", "unknown")
        has_avatar = toy.get("has_avatar", False)
        description = toy.get("description", "")
        is_owned = owner_oid == user_oid
        
        if is_owned:
            owned_count += 1
        
        print(f"\n[{idx}] {toy_name}")
        print(f"    ID: {toy_id}")
        print(f"    Owner: {owner_oid[:8]}... {'👤 (you)' if is_owned else ''}")
        
        if description:
            # Truncate long descriptions
            desc_preview = description[:60] + "..." if len(description) > 60 else description
            print(f"    Description: {desc_preview}")
        
        # Check avatar
        if has_avatar:
            print(f"    Avatar: ", end="")
            try:
                response = httpx.get(
                    f"{service_url}/toy/{toy_id}/avatar",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                
                # Get avatar info
                content_type = response.headers.get("content-type", "unknown")
                content_length = len(response.content)
                
                print(f"✅ {content_type}, {format_bytes(content_length)}")
                avatar_ok += 1
            except httpx.HTTPError as e:
                print(f"❌ Failed ({e.response.status_code if hasattr(e, 'response') else 'error'})")
                avatar_failed += 1
            except Exception as e:
                print(f"❌ Error: {e}")
                avatar_failed += 1
        else:
            print(f"    Avatar: ⏭️  No avatar")
            avatar_missing += 1
    
    # Summary
    print()
    print("=" * 50)
    print("📊 Summary")
    print(f"   Total toys: {len(toys)}")
    print(f"   Owned by you: {owned_count}")
    print(f"   Owned by others: {len(toys) - owned_count}")
    print(f"   Avatars OK: {avatar_ok}")
    print(f"   Avatars missing: {avatar_missing}")
    print(f"   Avatars failed: {avatar_failed}")
    print()
    
    if avatar_failed == 0:
        print("✨ All checks passed!")
    else:
        print(f"⚠️  {avatar_failed} avatar(s) failed to load")


if __name__ == "__main__":
    main()
