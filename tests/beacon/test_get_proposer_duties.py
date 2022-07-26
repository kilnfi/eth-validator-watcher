from tests.beacon import assets
from pathlib import Path
import json
from eth_validator_watcher.models import ProposerDuties
from requests_mock import Mocker
from eth_validator_watcher.beacon import Beacon


def test_():
    beacon_url = "http://beacon:5052"

    proposer_duties_path = Path(assets.__file__).parent / "proposer_duties.json"

    with proposer_duties_path.open() as file_descriptor:
        proposer_duties = json.load(file_descriptor)

    expected = ProposerDuties(
        dependent_root="0x6a23256440b627bdb3de50e1bcafa9a5a3efbfcf2976bd3b15139e61f47de8b0",
        data=[
            ProposerDuties.Data(
                pubkey="0x951d69f32685615df304c035151bd596d43bc3250f966e0c777544c506e3035d031afa4a3fcca1b85c41a4a041aefc01",
                validator_index=382,
                slot=209344,
            ),
            ProposerDuties.Data(
                pubkey="0xa0b8e0ef0756255edd80938c4e555a3d992953cd43371915d7a7280dc1bd8433933382919d50a98faad918fc9083bc07",
                validator_index=1176,
                slot=209345,
            ),
            ProposerDuties.Data(
                pubkey="0x825aca3d3dfa1d0b914e59fc3eeab6afcc5dc7e30fccd4879c592da4ea9a4e8a7a1057fc5b3faab12086e587126aa443",
                validator_index=965,
                slot=209346,
            ),
        ],
    )

    with Mocker() as mock:
        mock.get(
            f"{beacon_url}/eth/v1/validator/duties/proposer/6542", json=proposer_duties
        )

        beacon = Beacon(beacon_url)

        assert beacon.get_proposer_duties(6542) == expected
