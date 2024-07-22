import os
import vcr

from pathlib import Path
from tests import assets
from vcr.unittest import VCRTestCase

from eth_validator_watcher.entrypoint import ValidatorWatcher


class SepoliaTestCase(VCRTestCase):
    """This is a full end-to-end test.

    We mock a beacon with data recorded with cassette during ~2-3 epochs,
    slightly adapted to expose specific edge cases:

    - slot 5493884 (timestamp=1721660208)
    - slot 6356780 (timestamp=1721661324)
    """
    def slot_5493884(self):
        pass

    @vcr.use_cassette('tests/assets/cassettes/test_sepolia.yaml')
    def test_sepolia(self):
        """Main entrypoint for entire Sepolia unit test.
        """
        self.watcher = ValidatorWatcher(
            Path(assets.__file__).parent / "config.sepolia.yaml"
        )

        callbacks = {
            5493884: self.slot_5493884
        }

        called = {}

        def slot_hook(slot: int):
            if slot in callbacks:
                callbacks[slot]()
                called[slot] = True

        self.watcher._slot_hook = slot_hook
        self.watcher.run()

        for slot in callbacks.keys():
            self.assertTrue(called.get(slot))
