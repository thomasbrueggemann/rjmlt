import pathlib

import pytest

DATA = pathlib.Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_path():
    return DATA / "test.rjs"


@pytest.fixture(scope="session")
def sample_bytes(sample_path):
    return sample_path.read_bytes()
