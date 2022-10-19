from pathlib import Path

from eth_validator_watcher.utils import write_liveliness_file


def test_write_liveliness_file(tmp_path):
    tmp_path = Path(tmp_path / "liveliness")
    write_liveliness_file(tmp_path)

    with tmp_path.open() as file_descriptor:
        assert next(file_descriptor) == "OK"
