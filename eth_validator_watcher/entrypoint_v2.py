"""Draft entrypoint for the eth-validator-watcher v1.0.0.
"""

from functools import partial
from pathlib import Path
from typing import Optional

import typer
import time

from .config import load_config, WatchedKeyConfig


print = partial(print, flush=True)
app = typer.Typer(add_completion=False)


class ValidatorWatcher:
    """Ethereum Validator Watcher.
    """

    def __init__(self, cfg_path: Path) -> None:
        """Initialize the Ethereum Validator Watcher.

        Args:
        -----
        cfg_path: Path
            Path to the configuration file.
        """
        self.cfg_path = cfg_path
        self.cfg = None

    def reload_config(self) -> None:
        """Reload the configuration file.
        """
        try:
            self.cfg = load_config(self.cfg_path)
        except ValidationError as err:
            raise typer.BadParameter(f'Invalid configuration file: {err}')

    def run(self) -> None:
        """Run the Ethereum Validator Watcher.
        """
        while True:
            print('Reloading configuration...')
            self.reload_config()
            time.sleep(1)



@app.command()
def handler(
    config: Optional[Path] = typer.Option(
        'etc/config.local.yaml',
        help="File containing the Ethereum Validator Watcher configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        show_default=True,
    ),
) -> None:
    """Run the Ethereum Validator Watcher."""

    watcher = ValidatorWatcher(config)
    watcher.run()
