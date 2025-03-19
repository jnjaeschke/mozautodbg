"""Configuration helpers for mozautodbg."""

import configparser
from pathlib import Path
from typing import List
import sys
import questionary
import logging

CONFIG_FILE: Path = Path.home() / ".mozautodbg.ini"


def get_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    else:
        config["DEFAULT"] = {}
    return config


def save_config(config: configparser.ConfigParser) -> None:
    with CONFIG_FILE.open("w") as f:
        config.write(f)


def set_default_mozconfig_value(config: configparser.ConfigParser, path: str) -> None:
    config["DEFAULT"]["mozconfig"] = path


def get_default_mozconfig_value(config: configparser.ConfigParser) -> str | None:
    return config["DEFAULT"].get("mozconfig")


def set_default_branch_value(config: configparser.ConfigParser, branch: str) -> None:
    config["DEFAULT"]["branch"] = branch


def get_default_branch_value(config: configparser.ConfigParser) -> str | None:
    return config["DEFAULT"].get("branch")


def set_include_value(
    config: configparser.ConfigParser, include_list: List[str]
) -> None:
    config["DEFAULT"]["include"] = ",".join(include_list)


def get_include_value(config: configparser.ConfigParser) -> List[str]:
    val = config["DEFAULT"].get("include", "")
    return [x.strip() for x in val.split(",") if x.strip()]


def set_ignore_value(config: configparser.ConfigParser, ignore_list: List[str]) -> None:
    config["DEFAULT"]["ignore"] = ",".join(ignore_list)


def get_ignore_value(config: configparser.ConfigParser) -> List[str]:
    val = config["DEFAULT"].get("ignore", "")
    return [x.strip() for x in val.split(",") if x.strip()]


def interactive_configure() -> None:
    """
    Launch an interactive configuration TUI using questionary.
    Uses logging to display messages.
    """

    cfg = get_config()
    current_mozconfig: str = get_default_mozconfig_value(cfg) or ""
    current_branch: str = get_default_branch_value(cfg) or ""
    current_include: List[str] = get_include_value(cfg)
    current_ignore: List[str] = get_ignore_value(cfg)

    new_mozconfig: str = questionary.text(
        "Enter the default mozconfig file", default=current_mozconfig
    ).ask()  # type: ignore
    new_branch: str = questionary.text(
        "Enter the main development branch (e.g., main or master)",
        default=current_branch,
    ).ask()  # type: ignore
    new_include_str: str = questionary.text(
        "Enter default include paths (comma separated)",
        default=",".join(current_include) if current_include else "",
    ).ask()  # type: ignore
    new_ignore_str: str = questionary.text(
        "Enter default ignore paths (comma separated)",
        default=",".join(current_ignore) if current_ignore else "",
    ).ask()  # type: ignore
    confirm: bool = questionary.confirm("Save these settings?").ask()  # type: ignore

    if confirm:
        # Expand mozconfig to absolute path and check for existence.
        mozconfig_path = Path(new_mozconfig).expanduser().resolve()
        if not mozconfig_path.exists():
            logging.error(
                "Error: The mozconfig file %s does not exist.", mozconfig_path
            )
            sys.exit(1)
        set_default_mozconfig_value(cfg, str(mozconfig_path))
        set_default_branch_value(cfg, new_branch)
        include_list: List[str] = [
            s.strip() for s in new_include_str.split(",") if s.strip()
        ]
        ignore_list: List[str] = [
            s.strip() for s in new_ignore_str.split(",") if s.strip()
        ]
        set_include_value(cfg, include_list)
        set_ignore_value(cfg, ignore_list)
        save_config(cfg)
        logging.info("Configuration saved.")
    else:
        logging.info("Exiting without saving changes.")


def configure_defaults(
    mozconfig: str | None,
    branch: str | None,
    include: List[str],
    ignore: List[str],
) -> None:
    """
    Configure defaults non-interactively.
    Uses the following sensible defaults if missing:
      - Default branch: "bookmarks/central"
      - Default mozconfig: $HOME/mozconfig
    When setting the mozconfig file, its path is expanded to an absolute path and verified to exist.
    """

    cfg = get_config()

    # Use provided value or default to $HOME/mozconfig.
    if mozconfig is None:
        default_moz = (Path.home() / "mozconfig").expanduser().resolve()
        mozconfig = str(default_moz)
    else:
        mozconfig = str(Path(mozconfig).expanduser().resolve())
    if not Path(mozconfig).exists():
        logging.error("Error: The mozconfig file %s does not exist.", mozconfig)
        sys.exit(1)
    set_default_mozconfig_value(cfg, mozconfig)
    logging.info("Default mozconfig set to: %s", mozconfig)

    if branch is None:
        branch = "bookmarks/central"
    set_default_branch_value(cfg, branch)
    logging.info("Main development branch set to: %s", branch)

    set_include_value(cfg, list(include))
    logging.info(
        "Default include paths set to: %s", ", ".join(include) if include else "None"
    )
    set_ignore_value(cfg, list(ignore))
    logging.info(
        "Default ignore paths set to: %s", ", ".join(ignore) if ignore else "None"
    )

    save_config(cfg)
