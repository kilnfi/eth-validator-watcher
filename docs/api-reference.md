# API Reference

This page documents the key modules and classes in the Ethereum Validator Watcher. The documentation is automatically generated from the docstrings in the code.

## Configuration

The Configuration module handles loading and parsing configuration from files and environment variables.

::: eth_validator_watcher.config
    options:
      members:
        - Config
        - WatchedKeyConfig
        - load_config

## Beacon Client

The Beacon module provides a client interface for interacting with Ethereum consensus layer nodes.

::: eth_validator_watcher.beacon
    options:
      members:
        - Beacon
        - NoBlockError

## Watched Validators

The WatchedValidators module manages the validators being monitored by the system.

::: eth_validator_watcher.watched_validators
    options:
      members:
        - WatchedValidator
        - WatchedValidators
        - normalized_public_key

## Metrics

The Metrics module provides Prometheus metrics for validator monitoring.

::: eth_validator_watcher.metrics
    options:
      members:
        - PrometheusMetrics
        - compute_validator_metrics
        - get_prometheus_metrics

## Entry Point

The Entry Point module contains the main application logic.

::: eth_validator_watcher.entrypoint
    options:
      members:
        - ValidatorWatcher
        - handler

## Duties

The Duties module handles validator attestation and proposer duties.

::: eth_validator_watcher.duties
    options:
      members:
        - process_duties

## Models

The Models module defines data models used throughout the application.

::: eth_validator_watcher.models
    options:
      members:
        - Validators
        - Genesis
        - Spec
        - Header
        - Block
        - ProposerDuties
        - ValidatorsLivenessResponse
        - BlockIdentierType