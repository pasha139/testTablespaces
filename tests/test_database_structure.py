# coding: utf-8

import pytest
from firebird.qa import *

from tests.support import load_initialization_script
from tests.support import prepare_tablespaces, assert_database_state


db = db_factory(
    filename="structure_test.fdb",
    init=load_initialization_script(),
    charset="UTF8",
)
act = python_act("db")

@pytest.mark.version(">=6.0")
def test_structure(act: Action, tmp_path):
    tablespace_files = {
    "TS_DATA": tmp_path / "ts_data.fdb",
    "TS_INDEX": tmp_path / "ts_index.fdb",
    "TS_ARCHIVE": tmp_path / "ts_archive.fdb",
    }

    with act.db.connect() as connection:
        prepare_tablespaces(connection, tablespace_files)
        assert_database_state(connection.cursor())
