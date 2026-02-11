#!/usr/bin/env python3
"""
API Key Management Utility for TM MCP Server

Usage:
    python scripts/manage_keys.py generate --name "Team Alpha"
    python scripts/manage_keys.py list
    python scripts/manage_keys.py revoke <key_id>
    python scripts/manage_keys.py sync-to-gcp
"""

import argparse
import json
import secrets
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional

# Keys file location (git-ignored)
KEYS_FILE = Path(__file__).parent.parent / ".keys.json"


def load_keys() -> Dict:
    """Load keys from local storage."""
    if not KEYS_FILE.exists():
        return {"keys": [], "revoked": []}
    with open(KEYS_FILE) as f:
        return json.load(f)


def save_keys(data: Dict) -> None:
    """Save keys to local storage."""
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    # Ensure file is only readable by owner
    KEYS_FILE.chmod(0o600)


def generate_key(prefix: str = "mcp") -> str:
    """Generate a cryptographically secure API key."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


def generate_key_id() -> str:
    """Generate a short key identifier (first 8 chars)."""
    return secrets.token_hex(4)


def cmd_generate(args) -> None:
    """Generate a new API key."""
    data = load_keys()

    key = generate_key()
    key_id = generate_key_id()

    key_info = {
        "id": key_id,
        "key": key,
        "name": args.name or "Unnamed",
        "created": datetime.now(UTC).isoformat(),
        "last_used": None,
    }

    data["keys"].append(key_info)
    save_keys(data)

    print("✅ New API key generated:")
    print(f"   ID:   {key_id}")
    print(f"   Name: {args.name or 'Unnamed'}")
    print(f"   Key:  {key}")
    print()
    print("⚠️  Save this key securely - it won't be shown again!")
    print()
    print("Next steps:")
    print("1. Share this key securely with the user")
    print("2. Run: python scripts/manage_keys.py sync-to-gcp")


def cmd_list(args) -> None:
    """List all active keys."""
    data = load_keys()

    if not data["keys"]:
        print("No active keys found.")
        return

    print(f"{'ID':<12} {'Name':<25} {'Created':<20} {'Status':<10}")
    print("-" * 70)

    for key_info in data["keys"]:
        key_id = key_info["id"]
        name = key_info["name"]
        created = key_info["created"][:10]  # Just the date
        masked_key = f"{key_info['key'][:8]}...{key_info['key'][-4:]}"

        print(f"{key_id:<12} {name:<25} {created:<20} Active")

    if data["revoked"]:
        print()
        print(f"Revoked keys: {len(data['revoked'])}")


def cmd_revoke(args) -> None:
    """Revoke an API key."""
    data = load_keys()

    # Find key by ID or partial match
    key_to_revoke = None
    for i, key_info in enumerate(data["keys"]):
        if key_info["id"].startswith(args.key_id):
            key_to_revoke = i
            break

    if key_to_revoke is None:
        print(f"❌ Key not found: {args.key_id}")
        return

    revoked = data["keys"].pop(key_to_revoke)
    revoked["revoked_at"] = datetime.now(UTC).isoformat()
    data["revoked"].append(revoked)

    save_keys(data)

    print(f"✅ Key revoked: {revoked['name']} ({revoked['id']})")
    print()
    print("Next step:")
    print("Run: python scripts/manage_keys.py sync-to-gcp")


def cmd_export(args) -> None:
    """Export active keys as comma-separated string for Secret Manager."""
    data = load_keys()

    if not data["keys"]:
        print("")  # Empty string for no keys
        return

    keys = [key_info["key"] for key_info in data["keys"]]
    print(",".join(keys))


def cmd_sync_to_gcp(args) -> None:
    """Sync keys to GCP Secret Manager."""
    import subprocess

    data = load_keys()

    if not data["keys"]:
        print("❌ No active keys to sync.")
        return

    # Export keys as comma-separated string
    keys = ",".join([key_info["key"] for key_info in data["keys"]])

    secret_name = args.secret_name

    try:
        # Check if secret exists
        result = subprocess.run(
            ["gcloud", "secrets", "describe", secret_name],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Secret exists, add new version
            print(f"Updating existing secret: {secret_name}")
            subprocess.run(
                ["gcloud", "secrets", "versions", "add", secret_name, "--data-file=-"],
                input=keys,
                text=True,
                check=True,
            )
        else:
            # Create new secret
            print(f"Creating new secret: {secret_name}")
            subprocess.run(
                ["gcloud", "secrets", "create", secret_name, "--data-file=-"],
                input=keys,
                text=True,
                check=True,
            )

        print(f"✅ Keys synced to GCP Secret Manager: {secret_name}")
        print(f"   Total active keys: {len(data['keys'])}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to sync to GCP: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/install")
        sys.exit(1)


def cmd_show(args) -> None:
    """Show full details of a specific key."""
    data = load_keys()

    # Find key by ID
    for key_info in data["keys"]:
        if key_info["id"].startswith(args.key_id):
            print(f"Key ID:      {key_info['id']}")
            print(f"Name:        {key_info['name']}")
            print(f"Created:     {key_info['created']}")
            print(f"Full Key:    {key_info['key']}")
            return

    print(f"❌ Key not found: {args.key_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage API keys for TM MCP Server")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a new API key")
    gen_parser.add_argument("--name", help="Friendly name for this key (e.g., 'Team Alpha', 'John Doe')")

    # List command
    subparsers.add_parser("list", help="List all active keys")

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("key_id", help="Key ID to revoke (or first few characters)")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show full key details")
    show_parser.add_argument("key_id", help="Key ID to show")

    # Export command
    subparsers.add_parser("export", help="Export active keys as comma-separated string")

    # Sync to GCP command
    sync_parser = subparsers.add_parser("sync-to-gcp", help="Sync keys to GCP Secret Manager")
    sync_parser.add_argument(
        "--secret-name",
        default="mcp-api-keys",
        help="Name of the secret in GCP (default: mcp-api-keys)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handlers
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "revoke":
        cmd_revoke(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "sync-to-gcp":
        cmd_sync_to_gcp(args)


if __name__ == "__main__":
    main()
