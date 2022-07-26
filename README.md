Validator Watcher
=================

Description
-----------

🚨 Be alerted when you miss a block proposal! 🚨

This tool watches the 🥓 Ethereum Beacon chain 🥓 and raises and alert when
a block proposal is missed. It needs to be connected to a beacon node.

You can specify:
- the path to a file containing the list of public your keys to watch, or / and
- an URL to a Web3Signer instance managing your keys to watch

Pubkeys are load dynamically, at each slot.
- If you use pubkeys file, you can change it without having to restart the watcher.
- If you use Web3Signer, a call to Web3Signer will be done at every slot to get the
latest keys to watch.

A prometheus counter named `missed_block_proposals` is automatically increased by 1
when one of your validators missed a block.

Prometheus server is automatically exposed on port 8000.

```
Options:
  --beacon-url TEXT               URL of Teku beacon node  [required]
  --pubkeys-file-path FILE        File containing the list of public keys to watch
  --web3signer-url TEXT           URL to web3signer managing keys to watch
```

Installation
------------

To install it from PyPI:

```
pip install validator-watcher
```

To install it from source:
```
git clone git@github.com:kilnfi/validator-watcher.git
cd validator-watcher
pip install .
```


Developer guide
---------------

**Installation:**
```
git clone git@github.com:kilnfi/validator-watcher.git
cd validator-watcher
pip install .[dev]
```

**Running tests:**
```
pytest
```