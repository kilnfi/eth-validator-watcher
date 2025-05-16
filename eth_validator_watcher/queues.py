from .beacon import Beacon


def get_pending_deposits(beacon: Beacon) -> tuple[int, int]:
    """Returns deposits information from the beacon chain.

        Args:
            beacon: Beacon
                The beacon client to fetch data from.
        Returns:
                tuple[int, int]
                    Number of deposits and the total amount in Gwei.
    """
    deposits = beacon.get_pending_deposits()

    total = 0
    count = 0
    for deposit in deposits.data:
        total += deposit.amount
        count += 1

    return count, total


def get_pending_consolidations(beacon: Beacon) -> int:
    """Returns the number of pending consolidations from the beacon chain.

        Args:
            beacon: Beacon
                The beacon client to fetch data from.
        Returns:
            int
                Number of pending consolidations.
    """
    consolidations = beacon.get_pending_consolidations()
    return len(consolidations.data)


def get_pending_withdrawals(beacon: Beacon) -> int:
    """Returns the number of pending withdrawals from the beacon chain.

        Args:
            beacon: Beacon
                The beacon client to fetch data from.
        Returns:
            int
                Number of pending withdrawals.
    """
    withdrawals = beacon.get_pending_withdrawals()
    return len(withdrawals.data)
