import requests
import vcr

from functools import wraps
from pathlib import Path
from tests import assets
from vcr.unittest import VCRTestCase

from eth_validator_watcher.entrypoint import ValidatorWatcher


def sepolia_test(config_path: str):
    """Decorator to "simplify" a bit the writing of unit tests.

    Tests using it will see their method called at the end of each
    slot processing on the watcher, with the dict `self.metrics`
    filled with what's exposed on prometheus.

    Example:

        @sepolia_test('config_path'):
        def my_test(self, slot: int):
            self.assertEqual(self.metrics['eth_slot{network="sepolia"}', float(slot)))

    """

    def wrapper(f):
        @wraps(f)
        def _run_test(self, *args, **kwargs):
            with self.vcr.use_cassette('tests/assets/cassettes/test_sepolia.yaml'):

                self.watcher = ValidatorWatcher(
                    Path(assets.__file__).parent / config_path
                )

                def h(slot: int):
                    self.slot_hook_calls += 1
                    self.metrics = self._get_metrics()
                    self.assertIsNone(f(self, slot))

                self.watcher._slot_hook = h
                self.slot_hook_calls = 0
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

        self.vcr = vcr.VCR(before_record=ignore_metrics_cb)

    def tearDown(self):
        pass

    def _get_metrics(self):
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

    def print_matching_metric(self, pattern: str):
        """Helper to print matching metrics.
        """
        for k, v in self.metrics.items():
            if pattern in k:
                print(f'{k}: {v}')

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_metric_slot(self, slot: int):
        """Verifies the slot metric is exposed.
        """
        self.assertEqual(float(slot), self.metrics['eth_slot{network="sepolia"}'])

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_metric_epoch(self, slot: int):
        """Verifies the epoch metric is exposed.
        """
        self.assertEqual(int(slot) // 32, self.metrics['eth_epoch{network="sepolia"}'])

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_validator_status(self, slot: int):
        """Verifies the validator statuses are exposed by scopes.
        """
        if slot != 7363592:
            return

        def test_for_label(
                label: str,
                pending_initialized: int = 0,
                pending_queued: int = 0,
                active_ongoing: int = 0,
                active_exiting: int = 0,
                active_slashed: int = 0,
                exited_unslashed: int = 0,
                exited_slashed: int = 0,
                withdrawal_possible: int = 0,
                withdrawal_done: int = 0,
        ) -> None:

            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="pending_initialized"}}'], float(pending_initialized))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="pending_queued"}}'], float(pending_queued))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="active_ongoing"}}'], float(active_ongoing))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="active_exiting"}}'], float(active_exiting))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="active_slashed"}}'], float(active_slashed))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="exited_unslashed"}}'], float(exited_unslashed))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="exited_slashed"}}'], float(exited_slashed))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="withdrawal_possible"}}'], float(withdrawal_possible))
            self.assertEqual(self.metrics[f'eth_validator_status_count{{network="sepolia",scope="{label}",status="withdrawal_done"}}'], float(withdrawal_done))

        test_for_label("scope:watched", active_ongoing=100)
        test_for_label("scope:all-network", active_ongoing=1781, withdrawal_possible=200, withdrawal_done=6)
        test_for_label("scope:network", active_ongoing=1681, withdrawal_possible=200, withdrawal_done=6)
        test_for_label("operator:kiln", active_ongoing=100)
        test_for_label("vc:prysm-validator-1", active_ongoing=50)
        test_for_label("vc:teku-validator-1", active_ongoing=50)

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_validator_scaled_status(self, slot: int):
        """Verifies the validator statuses are exposed by scopes.
        """
        if slot != 7363592:
            return

        def test_for_label(
                label: str,
                pending_initialized: int = 0,
                pending_queued: int = 0,
                active_ongoing: int = 0,
                active_exiting: int = 0,
                active_slashed: int = 0,
                exited_unslashed: int = 0,
                exited_slashed: int = 0,
                withdrawal_possible: int = 0,
                withdrawal_done: int = 0,
        ) -> None:

            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="pending_initialized"}}'], float(pending_initialized))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="pending_queued"}}'], float(pending_queued))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="active_ongoing"}}'], float(active_ongoing))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="active_exiting"}}'], float(active_exiting))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="active_slashed"}}'], float(active_slashed))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="exited_unslashed"}}'], float(exited_unslashed))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="exited_slashed"}}'], float(exited_slashed))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="withdrawal_possible"}}'], float(withdrawal_possible))
            self.assertEqual(self.metrics[f'eth_validator_status_scaled_count{{network="sepolia",scope="{label}",status="withdrawal_done"}}'], float(withdrawal_done))

        test_for_label("scope:watched", active_ongoing=100)
        test_for_label("scope:all-network", active_ongoing=1785.09375, withdrawal_possible=150, withdrawal_done=0)
        test_for_label("scope:network", active_ongoing=1685.09375, withdrawal_possible=150, withdrawal_done=0)
        test_for_label("operator:kiln", active_ongoing=100)
        test_for_label("vc:prysm-validator-1", active_ongoing=50)
        test_for_label("vc:teku-validator-1", active_ongoing=50)

    @sepolia_test("config.sepolia_replay_2_slots.yaml")
    def test_sepolia_missed_attestation(self, slot: int):
        """Verifies attestation misses
        """
        if slot != 7363592:
            return

        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="operator:kiln"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="vc:prysm-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="vc:teku-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="scope:watched"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="scope:all-network"}'], 101.0)
        self.assertEqual(self.metrics['eth_missed_attestations{network="sepolia",scope="scope:network"}'], 101.0)

        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="operator:kiln"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="vc:prysm-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="vc:teku-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="scope:watched"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="scope:all-network"}'], 100.9375)
        self.assertEqual(self.metrics['eth_missed_attestations_scaled{network="sepolia",scope="scope:network"}'], 100.9375)

    @sepolia_test("config.sepolia.yaml")
    def test_sepolia_missed_consecutive_attestation(self, slot: int):
        """Verifies consecutive attestation misses
        """
        if slot != 7363686:
            return

        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="operator:kiln"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="vc:prysm-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="vc:teku-validator-1"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="scope:watched"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="scope:all-network"}'], 101.0)
        self.assertEqual(self.metrics['eth_missed_consecutive_attestations{network="sepolia",scope="scope:network"}'], 101.0)

    @sepolia_test("config.sepolia.yaml")
    def test_sepolia_blocks(self, slot: int):
        """Verifies block proposals and misses.
        """
        if slot != 7363612:
            return

        self.assertEqual(self.metrics['eth_block_proposals_head_total{network="sepolia",scope="operator:kiln"}'], 2.0)
        self.assertEqual(self.metrics['eth_missed_block_proposals_head_total{network="sepolia",scope="operator:kiln"}'], 0.0)
        self.assertEqual(self.metrics['eth_block_proposals_finalized_total{network="sepolia",scope="operator:kiln"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_block_proposals_finalized_total{network="sepolia",scope="operator:kiln"}'], 0.0)

        self.assertEqual(self.metrics['eth_block_proposals_head_total{network="sepolia",scope="scope:all-network"}'], 18.0)
        self.assertEqual(self.metrics['eth_missed_block_proposals_head_total{network="sepolia",scope="scope:all-network"}'], 1.0)
        self.assertEqual(self.metrics['eth_block_proposals_finalized_total{network="sepolia",scope="scope:all-network"}'], 0.0)
        self.assertEqual(self.metrics['eth_missed_block_proposals_finalized_total{network="sepolia",scope="scope:all-network"}'], 0.0)

    @sepolia_test("config.sepolia.yaml")
    def test_sepolia_full(self, slot: int):
        """Runs a complete iteration of the watcher over two epochs.
        """
        self.assertEqual(float(slot), self.metrics['eth_slot{network="sepolia"}'])
