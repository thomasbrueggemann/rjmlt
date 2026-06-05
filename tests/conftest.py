import pathlib

import pytest

DATA = pathlib.Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_path():
    return DATA / "test.rjs"


@pytest.fixture(scope="session")
def sample_bytes(sample_path):
    return sample_path.read_bytes()


@pytest.fixture(scope="session")
def configured_path():
    # A real, user-configured file (the "example1" reference): named devices,
    # presets, songs, setlists and wiring -- not factory defaults.
    return DATA / "configured.rjs"


@pytest.fixture(scope="session")
def configured_bytes(configured_path):
    return configured_path.read_bytes()
