"""Command-line interface for mozautodbg."""

import logging
import sys
from typing import List

import click

from mozautodbg import build_hook, config as config_mod


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG).",
)
@click.pass_context
def cli(ctx: click.Context, verbose: int) -> None:
    """
    mozautodbg CLI

    Use 'configure' to set up defaults, or 'mach' to run a mach command with an auto-generated
    temporary build hook.
    """
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@cli.command()
@click.option("--mozconfig", type=click.Path(), help="Set the default mozconfig file")
@click.option(
    "--branch", type=str, help="Set the main development branch (e.g., main or master)"
)
@click.option(
    "--include",
    multiple=True,
    help="Set default include paths (can be provided multiple times)",
)
@click.option(
    "--ignore",
    multiple=True,
    help="Set default ignore paths (can be provided multiple times)",
)
def configure(
    mozconfig: str | None,
    branch: str | None,
    include: List[str],
    ignore: List[str],
) -> None:
    """
    Configure mozautodbg.

    If no options are provided, an interactive TUI is launched.
    Otherwise, non-interactive configuration uses sensible defaults:
      - Default branch: bookmarks/central
      - Default mozconfig: $HOME/mozconfig (absolute path, must exist)
    """
    if mozconfig is None and branch is None and not include and not ignore:
        config_mod.interactive_configure()
    else:
        config_mod.configure_defaults(mozconfig, branch, include, ignore)


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.option(
    "--mozconfig", type=click.Path(), help="Override the default mozconfig file"
)
@click.option(
    "--base",
    type=str,
    help="Override the merge base target (branch name or commit SHA)",
)
@click.option("--show-hook", is_flag=True, help="Print the generated build hook file")
@click.option(
    "--include",
    multiple=True,
    help="Additional include paths (can be provided multiple times)",
)
@click.option(
    "--ignore",
    multiple=True,
    help="Additional ignore paths (can be provided multiple times)",
)
@click.argument("mach_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def mach(
    ctx: click.Context,
    mozconfig: str | None,
    base: str | None,
    show_hook: bool,
    include: List[str],
    ignore: List[str],
    mach_args: List[str],
) -> None:
    """
    Run a mach command with a generated temporary build hook.

    The final list of directories is computed as:
      (changed_dirs ∪ include) minus any directory that matches an ignore pattern.
    If --show-hook is given and no mach arguments are provided,
    the hook is printed and the command exits.
    """
    if not config_mod.CONFIG_FILE.exists():
        logging.info(
            "Configuration file not found. Launching interactive configuration."
        )
        config_mod.interactive_configure()
        return

    ret: int = build_hook.execute_mach(
        mozconfig, base, show_hook, list(include), list(ignore), list(mach_args)
    )
    sys.exit(ret)


if __name__ == "__main__":
    cli()
