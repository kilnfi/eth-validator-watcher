import os
import requests
import vcr

from functools import wraps
from pathlib import Path
from tests import assets
from vcr.unittest import VCRTestCase

from eth_validator_watcher.entrypoint import ValidatorWatcher


def sepolia_test(config_path: str):
    """Decorator to "simplify" a bit the writing of unit tests.

    We expect tests to provide self.slot_hook which is a function that
    tests the current slot from the watcher's perspective. Prometheus
    metrics exposed at the slot are available to the hook via:

    self.metrics

    The test is then expected to assert values there.
    """

    def wrapper(f):
        @wraps(f)
        def _run_test(self, *args, **kwargs):
            with self.vcr.use_cassette('tests/assets/cassettes/test_sepolia.yaml'):

                self.watcher = ValidatorWatcher(
                    Path(assets.__file__).parent / config_path
                )

                f(self, *args, **kwargs)

                def h(slot: int):
                    self.slot_hook_calls += 1
                    slot_hook = self.slot_hook
                    if slot_hook:
                        self.metrics = self.get_metrics()
                        slot_hook(slot)

                self.watcher._slot_hook = h
                self.watcher.run()

                self.assertGreater(self.slot_hook_calls, 0)

        return _run_test

    return wrapper


class SepoliaTestCase(VCRTestCase):
    """This is a series of full end-to-end test.

    We mock a beacon with data recorded with cassette during ~2-3
    epochs, slightly adapted to expose specific edge cases. The
    available beacon data spans between:

    - slot 5493884 (timestamp=1721660208)
    - slot 6356780 (timestamp=1721661324)
    """

    def setUp(self):

        def ignore_metrics_cb(request):
            # Do not mock /metrics endpoint as this is exposed by our
            # service and we need it to validate metrics we expose are
            # correct.
            if request.uri == 'http://localhost:8000/metrics':
                return None
            return request

        self.slot_hook = None
        self.slot_hook_calls = 0
        self.vcr = vcr.VCR(before_record=ignore_metrics_cb)

    def tearDown(self):
        pass

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

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_metric_slot(self):
        """Verifies that the slot metric is exposed.
        """

        def hook(slot: int):
            self.assertEqual(float(slot), self.metrics['eth_slot{network="sepolia"}'])

        self.slot_hook = hook

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_metric_epoch(self):
        """Verifies that the epoch metric is exposed.
        """

        def hook(slot: int):
            self.assertEqual(int(slot) // 32, self.metrics['eth_epoch{network="sepolia"}'])

        self.slot_hook = hook
