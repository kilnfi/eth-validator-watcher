# Getting Started

This guide will help you quickly set up and start using the Ethereum
Validator Watcher using Docker.

## Installation

Docker images are available for both AMD64 and ARM64 architectures:

```bash
docker pull ghcr.io/kilnfi/eth-validator-watcher:latest
```
        
## Creating your Configuration File

Start by creating a configuration file in the YAML format:

```yaml
# Example config file for the Ethereum validator watcher.

beacon_url: http://url-to-your-beacon:5051/
beacon_timeout_sec: 90
network: mainnet
metrics_port: 8000

watched_keys:
  - public_key: '0xa1d1ad...'
    labels: ["region:us", "client:teku"]
  - public_key: '0x8619c0...'
    labels: ["region:eu", "client:prysm"]
  - public_key: '0x91c445...'
    labels: ["region:eu", "client:lighthouse"]
```
   
The `beacon_url` is the consensus client used by the watcher to get
its view of the network. It is recommended to use a different node
than your validation nodes so that the watcher can watch your keys
from the [outside of your
infrastructure](https://www.kiln.fi/post/monitoring-ethereum-staking-infrastructure-at-scale).

Labels are optional, they enable to monitor independently sets of keys
on the network:

- compare your performances to the rest of the network,
- in large infrastructure, narrow down issues to a specific beacon
  node or validator node,
- compare new versions of software on a subset of [canary
  keys](https://www.kiln.fi/post/ethereum-upgrades-at-scale).

In this example, we can compare validators by client (`teku` vs
`prysm` vs `lighthouse`), or by region (`eu` vs `us`), you can use
arbitrary strings here and come with your own mapping for any keys
on the network.

## Run the container

```bash
docker run -v /path/to/your/config.yaml:/app/etc/config.yaml -p 8000:8000 ghcr.io/kilnfi/eth-validator-watcher:latest
```

## Viewing Metrics

The Prometheus metrics endpoint is exposed on port 8000 by default. Access metrics at:

```
http://localhost:8000/metrics
```

## Setting Up Grafana Dashboards

1. Import the [overview dashboard](https://github.com/kilnfi/eth-validator-watcher/blob/main/grafana/dashboard-overview.json) into Grafana
2. Import the [breakdown dashboard](https://github.com/kilnfi/eth-validator-watcher/blob/main/grafana/dashboard-breakdown.json) into Grafana
3. Configure your Prometheus data source in Grafana

## Next Steps

To understand the full API and metrics, see the [API
Reference](api-reference.md).