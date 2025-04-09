import unittest

from eth_validator_watcher.duties import hex_to_sparse_bitset


class HexBitsTestCase(unittest.TestCase):
    """Test case for hex_to_sparse_bitset function."""

    def test_hex_to_sparse_bitset_zero(self) -> None:
        """Test hex_to_sparse_bitset() with a zero hex value."""
        result = hex_to_sparse_bitset("0x00")
        self.assertEqual(result, set())

    def test_hex_to_sparse_bitset_with_prefix(self) -> None:
        """Test hex_to_sparse_bitset() with 0x prefix."""
        # 0000 0101
        result = hex_to_sparse_bitset("0x05")
        self.assertEqual(result, {5, 7})

    def test_hex_to_sparse_bitset_without_prefix(self) -> None:
        """Test hex_to_sparse_bitset() without 0x prefix."""
        # 0000 0101
        result = hex_to_sparse_bitset("05")
        self.assertEqual(result, {5, 7})

    def test_hex_to_sparse_bitset_complex(self) -> None:
        """Test hex_to_sparse_bitset() with a complex hex value."""
        # 1010 0101
        result = hex_to_sparse_bitset("0xA5")
        self.assertEqual(result, {0, 2, 5, 7})

    def test_hex_to_sparse_bitset_multi_byte(self) -> None:
        """Test hex_to_sparse_bitset() with a multi-byte hex value."""
        # 0001 0010 0011 0100
        result = hex_to_sparse_bitset("0x1234")
        self.assertEqual(result, {3, 6, 10, 11, 13})


if __name__ == "__main__":
    unittest.main()
