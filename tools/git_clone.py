"""Tool: git_clone — Clone a Git repository for source code analysis."""

import subprocess
from pathlib import Path
from tools.common import OUTPUT_DIR
from tools.registry import register

REPOS_DIR = OUTPUT_DIR / "repos"
REPOS_DIR.mkdir(exist_ok=True)

DEFINITION = {
    "type": "function",
    "function": {
        "name": "git_clone",
        "description": (
            "Clone a Git repository (shallow, depth=1) into output/repos/ for analysis. "
            "Use this after finding a paper's code repository. "
            "After cloning, use list_files and read_file to explore the source code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "Git repository URL, e.g. 'https://github.com/user/repo'",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to clone (optional, defaults to the repo's default branch)",
                },
            },
            "required": ["repo_url"],
        },
    },
}


def handler(repo_url: str, branch: str = "") -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    if not repo_name:
        return "Error: Could not determine repository name from URL."

    target_dir = REPOS_DIR / repo_name

    if target_dir.exists():
        return (
            f"Repository '{repo_name}' already exists at {target_dir}\n"
            f"Use list_files(directory=\"{target_dir}\") to explore it."
        )

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [repo_url, str(target_dir)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Clone timed out after 120 seconds. The repository may be too large."

    if result.returncode != 0:
        return f"Error: git clone failed.\n{result.stderr.strip()}"

    file_count = sum(1 for _ in target_dir.rglob("*") if _.is_file())
    return (
        f"Cloned '{repo_name}' to {target_dir} ({file_count} files)\n"
        f"Use list_files(directory=\"{target_dir}\") to explore the source code."
    )


register("git_clone", DEFINITION, handler)
