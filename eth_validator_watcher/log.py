import collections
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from eth_validator_watcher_ext import MetricsByLabel
from .config import Config
from .utils import LABEL_SCOPE_WATCHED
from .watched_validators import WatchedValidators

# We colorize anything related to validators so that it's easy to spot
# in the log noise from the watcher from actual issues.
COLOR_GREEN = "\x1b[32;20m"
COLOR_BOLD_GREEN = "\x1b[32;1m"
COLOR_YELLOW = "\x1b[33;20m"
COLOR_RED     = "\x1b[31;20m"
COLOR_BOLD_RED = "\x1b[31;1m"
COLOR_RESET = "\x1b[0m"


def shorten_validator(validator_pubkey: str) -> str:
    """Shorten a validator name
    """
    return f"{validator_pubkey[:10]}"


def beaconcha_validator_link(cfg: Config, validator: str) -> str:
    """Return a link to the beaconcha.in validator page.
    """
    return f'<https://{cfg.network}.beaconcha.in/validator/{validator}|{shorten_validator(validator)}>'


def beaconcha_slot_link(cfg: Config, slot: int) -> str:
    """Return a link to the beaconcha.in slot page.
    """
    return f'<https://{cfg.network}.beaconcha.in/slot/{slot}|{slot}>'


def slack_send(cfg: Config, msg: str) -> None:
    """Attempts to send a message to the configured slack channel."""
    if not (cfg.slack_channel and cfg.slack_token):
        return

    try:
        w = WebClient(token=cfg.slack_token)
        w.chat_postMessage(channel=cfg.slack_channel, text=msg)
    except SlackApiError as e:
        logging.warning(f'😿 Unable to send slack notification: {e.response["error"]}')


def log_single_entry(cfg: Config, validator: str, registry: WatchedValidators, msg: str, emoji: str, slot: int, color: str) -> None:
    """Logs a single validator entry.
    """
    v = registry.get_validator_by_pubkey(validator)

    label_msg_shell = ''
    label_msg_slack = ''
    if v:
        labels = [label for label in v.labels if not label.startswith('scope:')]
        if labels:
            label_msg_slack = f' ({", ".join([f"`{l}`" for l in labels])})'
            label_msg_shell = f' ({", ".join(labels)})'

    msg_shell = f'{color}{emoji} Validator {shorten_validator(validator)}{label_msg_shell} {msg}{COLOR_RESET}'
    logging.info(msg_shell)

    msg_slack = f'{emoji} Validator {beaconcha_validator_link(cfg, validator)}{label_msg_slack} {msg} on slot {beaconcha_slot_link(cfg, slot)}'
    slack_send(cfg, msg_slack)


def log_multiple_entries(cfg: Config, validators: list[str], registry: WatchedValidators, msg: str, emoji: str, slot: int, color: str) -> None:
    """Logs a multiple validator entries.
    """

    impacted_labels = collections.defaultdict(int)
    for validator in validators:
        v = registry.get_validator_by_pubkey(validator)
        if v:
            for label in v.labels:
                if not label.startswith('scope'):
                    impacted_labels[label] += 1
    top_labels = sorted(impacted_labels, key=impacted_labels.get, reverse=True)[:5]

    label_msg = ''
    if top_labels:
        label_msg = f' ({", ".join(top_labels)}...)'

    msg_validators_shell = f'{", ".join([shorten_validator(v) for v in validators])} and more'
    msg_shell = f'{color}{emoji} Validator(s) {msg_validators}{label_msg} {msg} on slot {slot}{COLOR_RESET}'
    logging.info(msg_shell)

    msg_validators_slack = f'{", ".join([beaconcha_validator_link(cfg, v) for v in validators])} and more'
    msg_slack = f'{emoji} Validator(s) {msg_validators}{label_msg} {msg} on slot {beaconcha_slot_link(cfg, slot)}'
    slack_send(cfg, msg_slack)


def log_details(cfg: Config, registry: WatchedValidators, metrics: MetricsByLabel, current_slot: int):
    """Log details about watched validators
    """
    m = metrics.get(LABEL_SCOPE_WATCHED)
    if not m:
        return None

    for slot, validator in m.details_future_blocks:
        # Only log once per epoch future block proposals.
        if current_slot % 32 == 0 and slot >= current_slot + 32:
            log_single_entry(cfg, validator, registry, f'will propose a block', '🙏', slot, COLOR_GREEN)

    for slot, validator in m.details_proposed_blocks:
        log_single_entry(cfg, validator, registry, f'proposed a block', '🏅', slot, COLOR_BOLD_GREEN)

    for slot, validator in m.details_missed_blocks:
        log_single_entry(cfg, validator, registry, f'likely missed a block', '😩', slot, COLOR_RED)

    for slot, validator in m.details_missed_blocks_finalized:
        log_single_entry(cfg, validator, registry, f'missed a block for real', '😭', slot, COLOR_BOLD_RED)

    if m.details_missed_attestations:
        log_multiple_entries(cfg, m.details_missed_attestations, registry, f'missed an attestation', '😞', slot, COLOR_YELLOW)
