import sys
from datetime import datetime, timedelta
from pathlib import Path
from sys import argv

MAX_DIFF = timedelta(minutes=1)


def main(parameters: list[str]):
    assert len(parameters) > 1, "Missing liveness file path"

    _, liveness_file_str_path, *_ = parameters
    liveness_file_path = Path(liveness_file_str_path)

    liveness_file_last_modification_date = datetime.fromtimestamp(
        liveness_file_path.stat().st_mtime
    )

    current_date = datetime.now()

    if current_date - liveness_file_last_modification_date > MAX_DIFF:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main(argv)
