import os
import requests
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

    def get_metrics(self):
        url = 'http://localhost:8000/metrics'
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        result = {}
        for line in response.text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split(' ')
                result[key] = float(value)
        return result

    def slot_5493884(self):
        metrics = self.get_metrics()

        self.assertEqual(metrics['eth_slot{network="sepolia"}'], 5493884.0)
        self.assertEqual(metrics['eth_epoch{network="sepolia"}'], 171683.0)

    def slot_5493887(self):
        metrics = self.get_metrics()

        self.assertEqual(metrics['eth_slot{network="sepolia"}'], 5493887.0)
        self.assertEqual(metrics['eth_epoch{network="sepolia"}'], 171683.0)

    def test_sepolia(self):
        """Main entrypoint for entire Sepolia unit test.
        """

        def ignore_metrics_cb(request):
            if request.uri == 'http://localhost:8000/metrics':
                return None
            return request

        v = vcr.VCR(before_record=ignore_metrics_cb)
        
        with v.use_cassette('tests/assets/cassettes/test_sepolia.yaml'):
            self.watcher = ValidatorWatcher(
                Path(assets.__file__).parent / "config.sepolia.yaml"
            )

            callbacks = {
                5493884: self.slot_5493884,
                5493887: self.slot_5493887,
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
