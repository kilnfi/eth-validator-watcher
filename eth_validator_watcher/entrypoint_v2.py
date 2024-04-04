"""Draft entrypoint for the eth-validator-watcher v1.0.0.
"""

from functools import partial
from pathlib import Path
from typing import Optional

import logging
import typer
import time

from .beacon import Beacon
from .config import load_config, WatchedKeyConfig
from .watched_validators import WatchedValidators


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
        self._cfg_path = cfg_path
        self._cfg = None
        self._beacon = None

        self._reload_config()

    def _reload_config(self) -> None:
        """Reload the configuration file.
        """
        try:
            self._cfg = load_config(self._cfg_path)
        except ValidationError as err:
            raise typer.BadParameter(f'Invalid configuration file: {err}')

        if self._beacon is None or self._beacon.get_url() != self._cfg.beacon_url or self._beacon.get_timeout_sec() != self._cfg.beacon_timeout_sec:
            self._beacon = Beacon(self._cfg.beacon_url, self._cfg.beacon_timeout_sec)

    def run(self) -> None:
        """Run the Ethereum Validator Watcher.
        """
        watched_validators = WatchedValidators()
        while True:
            logging.info('Processing new epoch')
            beacon_validators = self._beacon.get_validators()
            watched_validators.process_epoch(beacon_validators)

            logging.info('Processing configuration update')
            self._reload_config()
            watched_validators.process_config(self._cfg)

            logging.info('Waiting for next iteration')
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s'
    )

    watcher = ValidatorWatcher(config)
    watcher.run()
