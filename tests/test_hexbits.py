import unittest

from eth_validator_watcher.duties import bitfield_to_bitstring


class HexBitsTestCase(unittest.TestCase):
    """Test case for hex_to_sparse_bitset function."""

    def test_hex_to_sparse_bitset_zero(self) -> None:
        """Test hex_to_sparse_bitset() with a zero hex value."""
        result = bitfield_to_bitstring("0x0000064814008019", False)
        indices = {i for i, bit in enumerate(result) if bit == "1"}
        self.assertEqual(indices, {17, 18, 27, 30, 34, 36, 55, 56, 59, 60})


if __name__ == "__main__":
    unittest.main()
