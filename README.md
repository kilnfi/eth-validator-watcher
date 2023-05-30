Ethereum Validator Watcher
==========================

![kiln-logo](docs/img/Kiln_Logo-Transparent-Dark.svg)

[![License](https://img.shields.io/badge/license-MIT-blue)](https://opensource.org/licenses/MIT)

The code is provided as-is with no warranties.

Description
-----------
```
                                                                                                                                                                                 
 Usage: eth-validator-watcher [OPTIONS]                                                                                                                                          
                                                                                                                                                                                 
 🚨 Ethereum Validator Watcher 🚨                                                                                                                                                
 This tool watches the 🥓 Ethereum Beacon chain 🥓 and tells you when some of your                                                                                               
 validators:                                                                                                                                                                     
 - missed a block proposal                                                                                                                                                       
 - are going to propose a block in the next two epochs                                                                                                                           
 - did not attest optimally                                                                                                                                                      
 - missed an attestation                                                                                                                                                         
 - missed two attestations in a raw                                                                                                                                              
                                                                                                                                                                                 
 This tool also exposes extra data as how many validators are active, pending, etc...                                                                                            
                                                                                                                                                                                 
 You can specify:                                                                                                                                                                
 - the path to a file containing the list of public your keys to watch, or / and                                                                                                 
 - an URL to a Web3Signer instance managing your keys to watch.                                                                                                                  
                                                                                                                                                                                 
 Pubkeys are load dynamically, at each epoch start.                                                                                                                              
 - If you use pubkeys file, you can change it without having to restart the watcher.                                                                                             
 - If you use Web3Signer, a call to Web3Signer will be done at every epoch to get the                                                                                            
 latest set of keys to watch.                                                                                                                                                    
                                                                                                                                                                                 
 Prometheus server is automatically exposed on port 8000.                                                                                                                        
                                                                                                                                                                                 
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --beacon-url                               TEXT                             URL of beacon node [default: None] [required]                                                  │
│    --pubkeys-file-path                        FILE                             File containing the list of public keys to watch [default: None]                               │
│    --web3signer-url                           TEXT                             URL to web3signer managing keys to watch [default: None]                                       │
│    --slack-channel                            TEXT                             Slack channel to send alerts - SLACK_TOKEN env var must be set [default: None]                 │
│    --lighthouse            --no-lighthouse                                     Use this flag if connected to a lighthouse beacon node. See                                    │
│                                                                                https://github.com/sigp/lighthouse/issues/4243 for more details.                               │
│                                                                                [default: no-lighthouse]                                                                       │
│    --liveness-file                            PATH                             Liveness file [default: None]                                                                  │
│    --install-completion                       [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                                    │
│    --show-completion                          [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the installation.             │
│                                                                                [default: None]                                                                                │
│    --help                                                                      Show this message and exit.                                                                    │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Installation
------------

From PyPI:

```console
pip install eth-validator-watcher # TBD
```

From source:
```console
git clone git@github.com:kilnfi/eth-validator-watcher.git
cd eth-validator-watcher
pip install .
```


Developer guide
---------------
We use [Poetry](https://python-poetry.org/) to manage dependencies and packaging.

**Installation:**
```console
git clone git@github.com:kilnfi/validator-watcher.git
cd validator-watcher
poetry install --with dev
```

**Running tests:**
```console
pytest

# With coverage
pytest --cov eth_validator_watcher --cov-report=term-missing
```

**Beacon node compatibility:**
- Lighthouse: Full compatible (with `--lighthouse` flag used in the **watcher**)
- Teku: Full compatible (with `--beacon-liveness-tracking-enabled` flag used in the **beacon node**)

**Example of lineness probe usage on Kubernetes**
```yaml
livenessProbe:
  periodSeconds: 60
  initialDelaySeconds: 60
  failureThreshold: 1
  exec:
    command:
    - /usr/bin/python3.9
    - /usr/local/bin/liveness_check.py
    - /tmp/liveness
```

## License

[MIT License](LICENSE).
