import pytest

from framework import config
from framework.db_client import DbClient
from framework.fix_client import FixClient
from framework.rest_client import RestClient


@pytest.fixture(scope="session")
def rest():
    client = RestClient()
    yield client
    client.close()


@pytest.fixture(scope="session")
def fix():
    client = FixClient()
    client.logon()
    yield client
    client.logout()


@pytest.fixture
def symbol():
    return config.SYMBOL


@pytest.fixture(scope="session")
def db():
    client = DbClient()
    yield client
    client.close()
