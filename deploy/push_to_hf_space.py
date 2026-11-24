"""Create (or update) the Hugging Face Space and upload the app.

Prerequisites (once):
    pip install huggingface_hub
    hf auth login          # paste a *write* token from https://huggingface.co/settings/tokens

Usage:
    python deploy/push_to_hf_space.py --space <hf-username>/agrichain-portal
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]

# Mirrors .dockerignore, plus the project README (the Space gets its own README with metadata).
IGNORE = [
    ".env", ".env.*.local", ".git/*", ".vscode/*", ".venv/*", "venv/*",
    "**/__pycache__/*", "*.pyc", ".pytest_cache/*",
    "*.pdf", "*.docx", "*.pptx", "docs/*", "Submit_Google_Drive*", "*_submission.zip",
    "data/generated_images/*", "README.md",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", required=True, help="Space id, e.g. username/agrichain-portal")
    parser.add_argument("--private", action="store_true", help="Create the Space as private")
    args = parser.parse_args()

    api = HfApi()
    api.create_repo(args.space, repo_type="space", space_sdk="docker", private=args.private, exist_ok=True)
    api.upload_folder(
        folder_path=str(ROOT), repo_id=args.space, repo_type="space",
        ignore_patterns=IGNORE, commit_message="Deploy AgriChain portal",
    )
    api.upload_file(
        path_or_fileobj=str(ROOT / "deploy" / "huggingface" / "README.md"), path_in_repo="README.md",
        repo_id=args.space, repo_type="space", commit_message="Space metadata",
    )
    print(f"Uploaded. Build logs and app: https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
