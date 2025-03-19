"""Build hook helpers for mozautodbg."""

from os import environ

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator, List
from contextlib import contextmanager

import logging


def get_local_merge_base(base_override: str | None = None) -> str:
    """
    Compute the merge base between HEAD and the target branch.

    If base_override is provided, use it directly.
    Otherwise, use the configured default branch (falling back to "main" or "master").
    When on the default branch, the target is set to origin/<branch>.
    """
    if base_override:
        logging.info("Using provided merge base override: %s", base_override)
        try:
            merge_base = subprocess.check_output(
                ["git", "merge-base", "HEAD", base_override],
                text=True,
            ).strip()
            logging.debug(
                "Merge base with override '%s': %s", base_override, merge_base
            )
            return merge_base
        except subprocess.CalledProcessError as e:
            logging.error(
                "Error: Unable to determine merge base with '%s'. %s", base_override, e
            )
            sys.exit(1)

    try:
        from mozautodbg import config as config_mod

        cfg = config_mod.get_config()
        default_branch = config_mod.get_default_branch_value(cfg)
    except ImportError:
        default_branch = None

    if not default_branch:
        for branch in ["main", "master"]:
            try:
                subprocess.check_output(
                    ["git", "rev-parse", "--verify", branch], text=True
                )
                default_branch = branch
                break
            except subprocess.CalledProcessError:
                continue
        if not default_branch:
            logging.error("Unable to find a default branch ('main' or 'master').")
            sys.exit("Error: Unable to find a default branch 'main' or 'master'.")

    try:
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        logging.error("Unable to determine the current branch.")
        sys.exit("Error: Unable to determine the current branch.")

    target = (
        f"origin/{default_branch}"
        if current_branch == default_branch
        else default_branch
    )
    logging.info("Using target branch: %s", target)
    try:
        merge_base = subprocess.check_output(
            ["git", "merge-base", "HEAD", target], text=True
        ).strip()
        logging.debug("Computed merge base: %s", merge_base)
        return merge_base
    except subprocess.CalledProcessError as e:
        logging.error("Unable to determine merge base with '%s'. %s", target, e)
        sys.exit(f"Error: Unable to determine merge base with branch {target}.")


def get_changed_directories(merge_base: str) -> List[str]:
    """
    Return a sorted list of unique directories that have changed relative to merge_base.
    This function incorporates committed, staged, and unstaged changes.
    """
    changed_files = set()
    commands = [
        ["git", "diff", "--name-only", merge_base, "HEAD"],  # Committed changes
        ["git", "diff", "--name-only", merge_base],  # Unstaged (working tree) changes
        ["git", "diff", "--name-only", "--cached", merge_base],  # Staged changes
    ]
    for cmd in commands:
        try:
            output = subprocess.check_output(cmd, text=True)
            for line in output.strip().splitlines():
                changed_files.add(line)
        except subprocess.CalledProcessError as e:
            logging.error(
                "Unable to determine changed files using %s: %s", " ".join(cmd), e
            )
            sys.exit(
                "Error: Unable to determine changed files. Are you in a git repository?"
            )
    dirs = {str(Path(f).parent) for f in changed_files if Path(f).parent != Path(".")}
    return sorted(dirs)


@contextmanager
def write_build_hook(directories: List[str]) -> Generator[str, None, None]:
    """
    Write a temporary Python file with the build hook.
    The hook disables optimization (sets COMPILE_FLAGS['OPTIMIZE'] = [])
    for directories that match.
    """
    hook_lines = [
        "noopt = " + repr(directories),
        "for no in noopt:",
        "    if RELATIVEDIR.startswith(no):",
        "        COMPILE_FLAGS['OPTIMIZE'] = []",
    ]
    hook_content = "\n".join(hook_lines) + "\n"
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8"
    ) as temp_file:
        temp_file.write(hook_content)
        yield temp_file.name


def execute_mach(
    mozconfig: str | None,
    base: str | None,
    show_hook: bool,
    include: List[str],
    ignore: List[str],
    mach_args: List[str],
) -> int:
    """
    Execute the mach command with the generated temporary build hook.

    The final list of directories is computed as:
       (changed_dirs ∪ include) minus any directory that matches an ignore pattern.
    If --show-hook is given and no mach_args are provided, prints the hook and returns 0.
    Otherwise, sets MOZ_BUILD_HOOK (and optionally MOZCONFIG) and runs ./mach.
    """
    merge_base: str = get_local_merge_base(base)
    changed_dirs: List[str] = get_changed_directories(merge_base)
    logging.debug("Changed directories: %s", changed_dirs)

    # Compute union of changed directories and additional include directories.
    union_dirs = set(changed_dirs).union(set(include))
    logging.debug("Adding directories: %s", include)

    # Normalize ignore list: ensure each pattern ends with a slash.
    ignore_normalized = [ign if ign.endswith("/") else ign + "/" for ign in ignore]
    logging.debug("Ignoring directories: %s", ignore_normalized)

    # Filter out directories that match any ignore pattern.
    final_dirs: List[str] = list(
        sorted(
            d
            for d in union_dirs
            if not any(d == ign[:-1] or d.startswith(ign) for ign in ignore_normalized)
        )
    )
    logging.debug("Final directories for hook: %s", final_dirs)

    with write_build_hook(final_dirs) as hook_path:
        if show_hook:
            hook_content: str = Path(hook_path).read_text()
            loglevel = logging.getLogger().level
            logging.getLogger().setLevel(logging.INFO)
            logging.info("Generated hook content:\n%s", hook_content)
            logging.getLogger().setLevel(loglevel)

        if len(mach_args) == 0:
            return 0

        environ["MOZ_BUILD_HOOK"] = hook_path
        if mozconfig:
            environ["MOZCONFIG"] = mozconfig
            logging.info("Using MOZCONFIG: %s", mozconfig)
        else:
            logging.info("No MOZCONFIG override provided.")

        mach_cmd: List[str] = ["./mach"] + mach_args
        logging.info("Executing command: %s", " ".join(mach_cmd))
        ret: int = subprocess.call(mach_cmd)

    return ret
