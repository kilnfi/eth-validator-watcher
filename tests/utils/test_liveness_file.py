from pathlib import Path

from eth_validator_watcher.utils import write_liveness_file


def test_write_liveness_file(tmp_path):
    tmp_path = Path(tmp_path / "liveness")
    write_liveness_file(tmp_path)

    with tmp_path.open() as file_descriptor:
        assert next(file_descriptor) == "OK"
