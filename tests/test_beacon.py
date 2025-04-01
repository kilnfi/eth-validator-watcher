from pathlib import Path
import json
import unittest

from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon
from tests import assets


class BeaconTestCase(unittest.TestCase):
    """Test case for Beacon.

    We use data from the Sepolia testnet because it has a small number
    of validators and so the asset size we store on the repo is
    reasonable.
    """

    def test_has_block_at_slot_ok(self) -> None:
        """Test has_block_at_slot() with a block at the slot."""

        with open(Path(assets.__file__).parent / "sepolia_header_4996301.json") as fd:
            data = json.load(fd)

        with Mocker() as m:
            m.get("http://beacon-node:5051/eth/v1/beacon/headers/4996301", json=data)
            b = Beacon("http://beacon-node:5051", 90)
            self.assertTrue(b.has_block_at_slot(4996301))


if __name__ == "__main__":
    unittest.main()
