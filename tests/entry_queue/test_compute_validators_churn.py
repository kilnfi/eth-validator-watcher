from eth_validator_watcher.entry_queue import compute_validators_churn


def test_compute_validators_churn() -> None:
    assert compute_validators_churn(0) == 4
    assert compute_validators_churn(327_679) == 4
    assert compute_validators_churn(327_680) == 5
    assert compute_validators_churn(478_816) == 7
