from pathlib import Path
import json
import unittest

from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon, NoBlockError
from eth_validator_watcher.models import (
    BlockIdentierType,
    Genesis,
    Header,
    ProposerDuties,
    Spec,
    Validators,
    ValidatorsLivenessResponse,
    Rewards,
    Committees,
    Attestations,
    PendingDeposits,
    PendingWithdrawals,
    PendingConsolidations,
)
from tests import assets


class BeaconTestCase(unittest.TestCase):
    """Test case for Beacon.

    We use data from the Sepolia testnet because it has a small number
    of validators and so the asset size we store on the repo is
    reasonable.
    """

    def setUp(self) -> None:
        """Set up common test objects."""
        self.beacon_url = "http://beacon-node:5051"
        self.timeout = 90
        self.slot = 4996301

    def test_has_block_at_slot_ok(self) -> None:
        """Test has_block_at_slot() with a block at the slot."""

        with open(Path(assets.__file__).parent / "sepolia_header_4996301.json") as fd:
            data = json.load(fd)

        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/headers/{self.slot}", json=data)
            b = Beacon(self.beacon_url, self.timeout)
            self.assertTrue(b.has_block_at_slot(self.slot))

    def test_has_block_at_slot_missing(self) -> None:
        """Test has_block_at_slot() with no block at the slot."""
        with Mocker() as m:
            m.get(
                f"{self.beacon_url}/eth/v1/beacon/headers/{self.slot}",
                status_code=404
            )
            b = Beacon(self.beacon_url, self.timeout)
            self.assertFalse(b.has_block_at_slot(self.slot))

    def test_get_url(self) -> None:
        """Test get_url() returns the correct URL."""
        b = Beacon(self.beacon_url, self.timeout)
        self.assertEqual(b.get_url(), self.beacon_url)

    def test_get_timeout_sec(self) -> None:
        """Test get_timeout_sec() returns the correct timeout."""
        b = Beacon(self.beacon_url, self.timeout)
        self.assertEqual(b.get_timeout_sec(), self.timeout)

    def test_get_genesis(self) -> None:
        """Test get_genesis() returns the correct genesis data."""
        genesis_data = {
            "data": {
                "genesis_time": 1655733600
            }
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/genesis", json=genesis_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_genesis()
            self.assertIsInstance(result, Genesis)
            self.assertEqual(result.data.genesis_time, 1655733600)

    def test_get_spec(self) -> None:
        """Test get_spec() returns the correct spec data."""
        spec_data = {
            "data": {
                "SECONDS_PER_SLOT": 12,
                "SLOTS_PER_EPOCH": 32
            }
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/config/spec", json=spec_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_spec()
            self.assertIsInstance(result, Spec)
            self.assertEqual(result.data.SECONDS_PER_SLOT, 12)
            self.assertEqual(result.data.SLOTS_PER_EPOCH, 32)

    def test_get_header(self) -> None:
        """Test get_header() returns the correct header."""
        with open(Path(assets.__file__).parent / "sepolia_header_4996301.json") as fd:
            header_data = json.load(fd)
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/headers/{self.slot}", json=header_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_header(self.slot)
            self.assertIsInstance(result, Header)
            self.assertEqual(result.data.header.message.slot, 4996301)

    def test_get_header_not_found(self) -> None:
        """Test get_header() raises NoBlockError when block not found."""
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/headers/{self.slot}", status_code=404)
            b = Beacon(self.beacon_url, self.timeout)
            with self.assertRaises(NoBlockError):
                b.get_header(self.slot)

    def test_get_attestations(self) -> None:
        """Test get_attestations() returns attestation data."""
        attestation_data = {
            "data": [
                {
                    "aggregation_bits": "0x01",
                    "committee_bits": "0x02",
                    "data": {
                        "slot": 4996300,
                        "index": 1
                    }
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v2/beacon/blocks/{self.slot}/attestations", json=attestation_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_attestations(self.slot)
            self.assertIsInstance(result, Attestations)
            self.assertEqual(len(result.data), 1)
            self.assertEqual(result.data[0].data.slot, 4996300)

    def test_get_attestations_not_found(self) -> None:
        """Test get_attestations() returns None when attestations not found."""
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v2/beacon/blocks/{self.slot}/attestations", status_code=404)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_attestations(self.slot)
            self.assertIsNone(result)

    def test_get_committees(self) -> None:
        """Test get_committees() returns committee data."""
        committee_data = {
            "data": [
                {
                    "index": 0,
                    "slot": 4996301,
                    "validators": [1, 2, 3, 4]
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/{self.slot}/committees?slot={self.slot}", json=committee_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_committees(self.slot)
            self.assertIsInstance(result, Committees)
            self.assertEqual(len(result.data), 1)
            self.assertEqual(result.data[0].slot, self.slot)
            self.assertEqual(result.data[0].validators, [1, 2, 3, 4])

    def test_get_proposer_duties(self) -> None:
        """Test get_proposer_duties() returns proposer duty data."""
        epoch = 156134
        proposer_data = {
            "dependent_root": "0x1234567890abcdef",
            "data": [
                {
                    "pubkey": "0xabcdef1234567890",
                    "validator_index": 42,
                    "slot": self.slot
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/validator/duties/proposer/{epoch}", json=proposer_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_proposer_duties(epoch)
            self.assertIsInstance(result, ProposerDuties)
            self.assertEqual(result.dependent_root, "0x1234567890abcdef")
            self.assertEqual(len(result.data), 1)
            self.assertEqual(result.data[0].validator_index, 42)
            self.assertEqual(result.data[0].slot, self.slot)

    def test_get_validators(self) -> None:
        """Test get_validators() returns validator data."""
        validators_data = {
            "data": [
                {
                    "index": 42,
                    "status": "active_ongoing",
                    "validator": {
                        "pubkey": "0xabcdef1234567890",
                        "effective_balance": 32000000000,
                        "slashed": False,
                        "activation_epoch": 100,
                        "withdrawal_credentials": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    }
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/{self.slot}/validators", json=validators_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_validators(self.slot)
            self.assertIsInstance(result, Validators)
            self.assertEqual(len(result.data), 1)
            self.assertEqual(result.data[0].index, 42)
            self.assertEqual(result.data[0].status, "active_ongoing")
            self.assertEqual(result.data[0].validator.effective_balance, 32000000000)
            self.assertFalse(result.data[0].validator.slashed)
            self.assertEqual(result.data[0].validator.withdrawal_credentials, "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")

    def test_get_rewards(self) -> None:
        """Test get_rewards() returns reward data."""
        epoch = 156134
        rewards_data = {
            "data": {
                "ideal_rewards": [
                    {
                        "effective_balance": 32000000000,
                        "source": 12345,
                        "target": 23456,
                        "head": 34567
                    }
                ],
                "total_rewards": [
                    {
                        "validator_index": 42,
                        "source": 12345,
                        "target": 23456,
                        "head": 34567
                    }
                ]
            }
        }
        with Mocker() as m:
            m.post(f"{self.beacon_url}/eth/v1/beacon/rewards/attestations/{epoch}", json=rewards_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_rewards(epoch)
            self.assertIsInstance(result, Rewards)
            self.assertEqual(len(result.data.ideal_rewards), 1)
            self.assertEqual(result.data.ideal_rewards[0].effective_balance, 32000000000)
            self.assertEqual(len(result.data.total_rewards), 1)
            self.assertEqual(result.data.total_rewards[0].validator_index, 42)

    def test_get_validators_liveness(self) -> None:
        """Test get_validators_liveness() returns liveness data."""
        epoch = 156134
        indexes = [42, 43]
        liveness_data = {
            "data": [
                {
                    "index": 42,
                    "is_live": True
                },
                {
                    "index": 43,
                    "is_live": False
                }
            ]
        }
        with Mocker() as m:
            m.post(f"{self.beacon_url}/eth/v1/validator/liveness/{epoch}", json=liveness_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_validators_liveness(epoch, indexes)
            self.assertIsInstance(result, ValidatorsLivenessResponse)
            self.assertEqual(len(result.data), 2)
            self.assertEqual(result.data[0].index, 42)
            self.assertTrue(result.data[0].is_live)
            self.assertEqual(result.data[1].index, 43)
            self.assertFalse(result.data[1].is_live)

    def test_has_block_at_slot_with_block_identifier(self) -> None:
        """Test has_block_at_slot() with a BlockIdentifierType."""
        with open(Path(assets.__file__).parent / "sepolia_header_4996301.json") as fd:
            data = json.load(fd)
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/headers/{BlockIdentierType.HEAD}", json=data)
            b = Beacon(self.beacon_url, self.timeout)
            self.assertTrue(b.has_block_at_slot(BlockIdentierType.HEAD))

    def test_get_pending_deposits(self) -> None:
        """Test get_pending_deposits() returns pending deposit data."""
        deposits_data = {
            "data": [
                {
                    "pubkey": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "withdrawal_credentials": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    "amount": 32000000000,
                    "slot": 4996400
                },
                {
                    "pubkey": "0x2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef",
                    "withdrawal_credentials": "0xbcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890a",
                    "amount": 32000000000,
                    "slot": 4996500
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_deposits", json=deposits_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_deposits()
            self.assertIsInstance(result, PendingDeposits)
            self.assertEqual(len(result.data), 2)
            self.assertEqual(result.data[0].pubkey, "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
            self.assertEqual(result.data[0].withdrawal_credentials, "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
            self.assertEqual(result.data[0].amount, 32000000000)
            self.assertEqual(result.data[0].slot, 4996400)
            self.assertEqual(result.data[1].pubkey, "0x2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef2345678901abcdef")
            self.assertEqual(result.data[1].withdrawal_credentials, "0xbcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890a")
            self.assertEqual(result.data[1].amount, 32000000000)
            self.assertEqual(result.data[1].slot, 4996500)

    def test_get_pending_withdrawals(self) -> None:
        """Test get_pending_withdrawals() returns pending withdrawal data."""
        withdrawals_data = {
            "data": [
                {
                    "validator_index": 42,
                    "amount": 1000000000
                },
                {
                    "validator_index": 43,
                    "amount": 2000000000
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_partial_withdrawals", json=withdrawals_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_withdrawals()
            self.assertIsInstance(result, PendingWithdrawals)
            self.assertEqual(len(result.data), 2)
            self.assertEqual(result.data[0].validator_index, 42)
            self.assertEqual(result.data[0].amount, 1000000000)
            self.assertEqual(result.data[1].validator_index, 43)
            self.assertEqual(result.data[1].amount, 2000000000)

    def test_get_pending_consolidations(self) -> None:
        """Test get_pending_consolidations() returns pending consolidation data."""
        consolidations_data = {
            "data": [
                {
                    "source_index": 100,
                    "target_index": 200
                },
                {
                    "source_index": 101,
                    "target_index": 201
                }
            ]
        }
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_consolidations", json=consolidations_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_consolidations()
            self.assertIsInstance(result, PendingConsolidations)
            self.assertEqual(len(result.data), 2)
            self.assertEqual(result.data[0].source_index, 100)
            self.assertEqual(result.data[0].target_index, 200)
            self.assertEqual(result.data[1].source_index, 101)
            self.assertEqual(result.data[1].target_index, 201)

    def test_get_pending_deposits_empty(self) -> None:
        """Test get_pending_deposits() returns empty data when no pending deposits."""
        empty_data = {"data": []}
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_deposits", json=empty_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_deposits()
            self.assertIsInstance(result, PendingDeposits)
            self.assertEqual(len(result.data), 0)

    def test_get_pending_withdrawals_empty(self) -> None:
        """Test get_pending_withdrawals() returns empty data when no pending withdrawals."""
        empty_data = {"data": []}
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_partial_withdrawals", json=empty_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_withdrawals()
            self.assertIsInstance(result, PendingWithdrawals)
            self.assertEqual(len(result.data), 0)

    def test_get_pending_consolidations_empty(self) -> None:
        """Test get_pending_consolidations() returns empty data when no pending consolidations."""
        empty_data = {"data": []}
        with Mocker() as m:
            m.get(f"{self.beacon_url}/eth/v1/beacon/states/head/pending_consolidations", json=empty_data)
            b = Beacon(self.beacon_url, self.timeout)
            result = b.get_pending_consolidations()
            self.assertIsInstance(result, PendingConsolidations)
            self.assertEqual(len(result.data), 0)


if __name__ == "__main__":
    unittest.main()
