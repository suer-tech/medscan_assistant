"""Configure only this MedScan project's secrets, without printing their values.

Run from the linked project directory. Pass --ai-env only when the owner has
authorized using that local AI account. The database is provisioned separately.
"""
import argparse
import json
import secrets
import shutil
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from passlib.hash import pbkdf2_sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-env", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    private = root / ".private"
    private.mkdir(exist_ok=True)
    access_path = private / "medscan-access.json"
    if access_path.exists():
        access = json.loads(access_path.read_text(encoding="utf-8"))
    else:
        password = secrets.token_urlsafe(24)
        access = {
            "url": "https://medscan-assistant.vercel.app",
            "email": "admin@medscan.local",
            "password": password,
            "password_hash": pbkdf2_sha256.using(rounds=600_000).hash(password),
            "jwt_secret": secrets.token_urlsafe(48),
        }
        access_path.write_text(json.dumps(access, indent=2), encoding="utf-8")
    config = {
        "NODE_ENV": ("production", False),
        "VITE_APP_ID": ("medscan-assistant", False),
        "MEDSCAN_ADMIN_EMAIL": (access["email"], False),
        "MEDSCAN_ADMIN_NAME": ("MedScan administrator", False),
        "MEDSCAN_ADMIN_PASSWORD_HASH": (access["password_hash"], True),
        "JWT_SECRET": (access["jwt_secret"], True),
    }
    if args.ai_env:
        source = dotenv_values(args.ai_env)
        key = source.get("BUILT_IN_FORGE_API_KEY")
        if not key:
            raise SystemExit("The authorized local file contains no AI key")
        config.update({
            "BUILT_IN_FORGE_API_KEY": (key, True),
            "BUILT_IN_FORGE_API_URL": (source.get("BUILT_IN_FORGE_API_URL") or "https://openrouter.ai/api", False),
            "LLM_MODEL": (source.get("LLM_MODEL") or "openai/gpt-4o-mini", False),
        })
    command = shutil.which("npx.cmd") or shutil.which("npx")
    if not command:
        raise SystemExit("npx is required")
    for name, (value, sensitive) in config.items():
        result = subprocess.run(
            [command, "--yes", "vercel@59.11.7", "env", "add", name,
             "production,preview", "--sensitive" if sensitive else "--no-sensitive",
             "--force", "--yes", "--scope", "suer-techs-projects"],
            input=value, text=True, capture_output=True, cwd=root,
        )
        if result.returncode:
            # Never forward tool output: it may echo the submitted secret.
            raise SystemExit(f"Failed to configure {name}; no secret output was printed")
        print(f"Configured {name}", flush=True)
    print(f"Private login details saved locally: {access_path}")


if __name__ == "__main__":
    main()
