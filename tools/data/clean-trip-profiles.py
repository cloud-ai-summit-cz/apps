"""
Clean all trip profiles from the trip service.

This script:
1. Lists all trips
2. Deletes all gallery images
3. Deletes all trips

Admin Role Support:
- Users with Admin.FullAccess role can delete ALL trips (regardless of owner)
- Regular users can only delete their own trips
- See tools/identity/ADMIN_ROLE_SETUP.md for role configuration

Requires:
- TRIP_SERVICE_URL environment variable
- AUTH_TOKEN_PATH pointing to valid auth token
- Running trip service
"""
import json
import os
import sys
import time
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
    if token_data.get("expires_on", 0) < time.time():
        print("❌ Auth token expired")
        print("   Run: python tools/identity/get_auth_token.py")
        sys.exit(1)

    return token_data


def get_auth_headers(token_data: dict) -> dict:
    """Generate authorization headers."""
    return {
        "Authorization": f"Bearer {token_data['token']}",
        "Content-Type": "application/json",
    }


def has_admin_role(token_data: dict) -> bool:
    """Check if user has Admin.FullAccess role."""
    roles = token_data.get("claims", {}).get("roles", [])
    return "Admin.FullAccess" in roles


def main():
    """Clean all trip profiles."""
    print("🧹 Trip Profile Cleanup")
    print("=" * 50)

    # Load configuration
    service_url = os.getenv("TRIP_SERVICE_URL", "http://localhost:8002")
    print(f"📡 Service URL: {service_url}")

    # Load auth token
    try:
        token_data = load_auth_token()
        headers = get_auth_headers(token_data)
        user_oid = token_data["claims"].get("oid")
        is_admin = has_admin_role(token_data)

        print(
            f"✅ Auth token loaded (user: {token_data['claims'].get('preferred_username', 'unknown')})"
        )
        print(f"   User OID: {user_oid}")

        if is_admin:
            print(f"   🔑 Admin role: Admin.FullAccess ✓")
            print(f"   ⚠️  You can delete ALL trips (including those owned by others)")
        else:
            print(f"   👤 Admin role: None")
            print(f"   ℹ️  You can only delete your own trips")
    except Exception as e:
        print(f"❌ Failed to load auth token: {e}")
        sys.exit(1)

    print()

    # List all trips
    print("📋 Fetching trip list...")
    try:
        response = httpx.get(
            f"{service_url}/trip", headers=headers, params={"limit": 1000}, timeout=10.0
        )
        response.raise_for_status()
        response_data = response.json()
        all_trips = response_data.get("items", [])
        print(f"✅ Found {len(all_trips)} total trips")
    except httpx.HTTPError as e:
        print(f"❌ Failed to fetch trips: {e}")
        sys.exit(1)

    # Determine which trips can be deleted
    if is_admin:
        # Admin can delete all trips
        trips_to_delete = all_trips
        trips_skipped = []
    else:
        # Regular user can only delete their own trips
        trips_to_delete = [
            trip for trip in all_trips if trip.get("owner_oid") == user_oid
        ]
        trips_skipped = [
            trip for trip in all_trips if trip.get("owner_oid") != user_oid
        ]

    if trips_skipped:
        print(f"⚠️  {len(trips_skipped)} trips owned by other users (will be skipped)")

    print(f"🎯 {len(trips_to_delete)} trips will be deleted")

    if not trips_to_delete:
        if is_admin:
            print("\n✨ No trips to clean (database is empty)")
        else:
            print("\n✨ No trips to clean (you don't own any)")
        return

    print()

    # Delete gallery images first
    print("🖼️  Deleting gallery images...")
    image_deleted = 0
    image_skipped = 0
    image_failed = 0

    for trip in trips_to_delete:
        trip_id = trip["id"]
        trip_title = trip["title"]
        gallery = trip.get("gallery", [])
        is_owner = trip.get("owner_oid") == user_oid
        owner_indicator = "" if is_owner else " [other owner]"

        if not gallery:
            continue

        for image in gallery:
            image_id = image["image_id"]

            try:
                response = httpx.delete(
                    f"{service_url}/trip/{trip_id}/gallery/{image_id}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                print(
                    f"   ✅ Deleted image {image_id} from {trip_title}{owner_indicator}"
                )
                image_deleted += 1
            except Exception as e:
                print(f"   ❌ Failed to delete image: {e}")
                image_failed += 1

    print(
        f"\n📊 Gallery Images: {image_deleted} deleted, {image_skipped} skipped, {image_failed} failed"
    )
    print()

    # Delete trips
    print("🗺️  Deleting trips...")
    trip_deleted = 0
    trip_failed = 0

    for trip in trips_to_delete:
        trip_id = trip["id"]
        trip_title = trip["title"]
        is_owner = trip.get("owner_oid") == user_oid
        owner_indicator = "" if is_owner else " [other owner]"

        try:
            response = httpx.delete(
                f"{service_url}/trip/{trip_id}", headers=headers, timeout=10.0
            )
            response.raise_for_status()
            print(f"   ✅ Deleted trip: {trip_title}{owner_indicator}")
            trip_deleted += 1
        except Exception as e:
            print(f"   ❌ Failed to delete trip {trip_title}: {e}")
            trip_failed += 1

    print(f"\n📊 Trips: {trip_deleted} deleted, {trip_failed} failed")
    print()

    # Summary
    if trip_failed == 0:
        print("✨ Cleanup complete!")
    else:
        print(f"⚠️  Cleanup complete with {trip_failed} failures")


if __name__ == "__main__":
    main()
