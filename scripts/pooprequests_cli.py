#!/usr/bin/env python3
"""CLI helper to clone/pull PoopRequests and build its Docker image."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_REPO = "https://github.com/<your-user>/pooprequests.git"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    location = f" (cwd={cwd})" if cwd else ""
    print(f"\n$ {' '.join(cmd)}{location}")
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(cmd)}")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command not found in PATH: {name}")


def clone_or_update(repo_url: str, branch: str, checkout_dir: Path) -> Path:
    if checkout_dir.exists() and (checkout_dir / ".git").exists():
        run(["git", "fetch", "--all", "--prune"], cwd=checkout_dir)
        run(["git", "checkout", branch], cwd=checkout_dir)
        run(["git", "pull", "--ff-only", "origin", branch], cwd=checkout_dir)
        return checkout_dir

    if checkout_dir.exists() and not (checkout_dir / ".git").exists():
        raise RuntimeError(
            f"Checkout path exists but is not a git repository: {checkout_dir}. "
            "Please remove it or choose another --checkout-dir."
        )

    checkout_dir.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--branch", branch, repo_url, str(checkout_dir)])
    return checkout_dir


def build_image(project_dir: Path, image_tag: str) -> None:
    run(["docker", "build", "-t", image_tag, "."], cwd=project_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone/pull PoopRequests and build the Docker image.",
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"Git repository URL (default: {DEFAULT_REPO})",
    )
    parser.add_argument("--branch", default="main", help="Branch to checkout/pull (default: main)")
    parser.add_argument(
        "--checkout-dir",
        default="./pooprequests-src",
        help="Local path used for clone/pull (default: ./pooprequests-src)",
    )
    parser.add_argument(
        "--image-tag",
        default="pooprequests:latest",
        help="Docker image tag to build (default: pooprequests:latest)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        ensure_command("git")
        ensure_command("docker")

        checkout_dir = Path(args.checkout_dir).expanduser().resolve()
        project_dir = clone_or_update(args.repo, args.branch, checkout_dir)
        build_image(project_dir, args.image_tag)

        print("\n✅ Done. Image built successfully.")
        print(f"Repository: {project_dir}")
        print(f"Image tag: {args.image_tag}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should report readable errors.
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
