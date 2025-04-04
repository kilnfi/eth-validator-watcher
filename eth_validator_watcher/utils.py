
# Slots at which processing is performed.
SLOT_FOR_CONFIG_RELOAD = 15
SLOT_FOR_MISSED_ATTESTATIONS_PROCESS = 16
SLOT_FOR_REWARDS_PROCESS = 17

# Default set of existing scopes.
LABEL_SCOPE_ALL_NETWORK = "scope:all-network"
LABEL_SCOPE_WATCHED = "scope:watched"
LABEL_SCOPE_NETWORK = "scope:network"


def pct(a: int, b: int, inclusive: bool = False) -> float:
    """Helper function to calculate the percentage of a over b.

    Args:
        a: int
            Numerator value.
        b: int
            Denominator value.
        inclusive: bool
            If True, uses b as total; if False, uses a+b as total.

    Returns:
        float: Percentage value (0-100.0).
    """
    total = a + b if not inclusive else b
    if total == 0:
        return 0.0
    return float(a / total) * 100.0
