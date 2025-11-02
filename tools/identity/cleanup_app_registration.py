#!/usr/bin/env python3
"""
Clean Up Entra ID App Registration for ToyTrips Application

Deletes the app registration and service principal created by create_app_registration.py.
Reads configuration from app_registration.json by default.

Requirements:
- Azure CLI authenticated with permissions to delete app registrations
- Run from tools/identity directory

Usage:
    python cleanup_app_registration.py
    python cleanup_app_registration.py --file app_registration.json
    python cleanup_app_registration.py --app-id <app-id>
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import platform


def run_az_command(cmd: list[str], check: bool = True) -> dict[str, Any] | None:
    """Execute Azure CLI command and return JSON result."""
    try:
        # On Windows, use az.cmd explicitly
        if platform.system() == "Windows" and cmd[0] == "az":
            cmd[0] = "az.cmd"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}
    except subprocess.CalledProcessError as e:
        if not check:
            return None
        print(f"Error executing command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        sys.exit(1)


def load_registration_details(file_path: Path) -> dict[str, Any]:
    """Load app registration details from JSON file."""
    if not file_path.exists():
        print(f"Error: Registration file not found: {file_path}", file=sys.stderr)
        print("Use --app-id to specify the application ID directly", file=sys.stderr)
        sys.exit(1)
    
    with open(file_path) as f:
        return json.load(f)


def delete_app_registration(app_id: str, display_name: str = None):
    """
    Delete Entra ID app registration and associated service principal.
    
    Args:
        app_id: Application (client) ID
        display_name: Optional display name for logging
    """
    name_str = f" ({display_name})" if display_name else ""
    print(f"Deleting app registration{name_str}: {app_id}")
    
    # Check if app exists
    app = run_az_command(
        ["az", "ad", "app", "show", "--id", app_id],
        check=False
    )
    
    if not app:
        print(f"⚠ App registration {app_id} not found (may already be deleted)")
    else:
        # Delete the app registration (this also deletes the service principal)
        run_az_command([
            "az", "ad", "app", "delete",
            "--id", app_id
        ])
        print(f"✓ Deleted app registration and service principal")


def cleanup_registration_file(file_path: Path, keep_file: bool = False):
    """Remove the registration details file."""
    if file_path.exists() and not keep_file:
        file_path.unlink()
        print(f"✓ Removed {file_path}")
    elif keep_file:
        print(f"ℹ Keeping registration file: {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Entra ID app registration for ToyTrips"
    )
    parser.add_argument(
        "--file",
        default="app_registration.json",
        help="Registration details file (default: app_registration.json)"
    )
    parser.add_argument(
        "--app-id",
        help="Application ID to delete (overrides file)"
    )
    parser.add_argument(
        "--keep-file",
        action="store_true",
        help="Keep the registration details file after deletion"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    file_path = Path(args.file)
    
    # Determine app ID and display name
    if args.app_id:
        app_id = args.app_id
        display_name = None
    else:
        details = load_registration_details(file_path)
        app_id = details.get("appId")
        display_name = details.get("displayName")
        
        if not app_id:
            print("Error: No appId found in registration file", file=sys.stderr)
            sys.exit(1)
    
    # Confirmation prompt
    if not args.yes:
        name_str = f" ({display_name})" if display_name else ""
        response = input(f"Delete app registration{name_str} {app_id}? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # Delete app registration
    delete_app_registration(app_id, display_name)
    
    # Cleanup file
    if not args.app_id:  # Only cleanup file if we loaded from it
        cleanup_registration_file(file_path, args.keep_file)
    
    print("\n" + "="*60)
    print("CLEANUP COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nApp registration and service principal have been deleted.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
