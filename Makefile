all:
	eth-validator-watcher 2>&1 | tee -a /var/log/ethereum-watcher/watcher.log

test:
	poetry run pytest
