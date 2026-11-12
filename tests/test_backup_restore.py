# coding: utf-8

from pathlib import Path
import pytest
from firebird.qa import *
from firebird.driver import connect

from tests.support import (
    load_initialization_script,
    prepare_tablespaces,
    assert_database_state,
)

db = db_factory(
    filename="backup_restore_source.fdb",
    init=load_initialization_script(),
    charset="UTF8",
)
act = python_act("db")

backup_file = temp_file("backup_restore.fbk")
restored_file = temp_file("backup_restore_restored.fdb")


@pytest.mark.version(">=6.0")
def test_backup_restore(act: Action, tmp_path, backup_file, restored_file):
    tablespace_files = {
        "TS_DATA": tmp_path / "ts_data.fdb",
        "TS_INDEX": tmp_path / "ts_index.fdb",
        "TS_ARCHIVE": tmp_path / "ts_archive.fdb",
    }

    with act.db.connect() as connection:
        prepare_tablespaces(connection, tablespace_files)
        assert_database_state(connection.cursor())

    act.gbak(switches=["-b", act.db.dsn, str(backup_file)])
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    act.reset()

    moved_files = []
    for path_value in tablespace_files.values():
        path = Path(path_value).resolve()
        if path.exists():
            moved = path.with_name(path.name + ".source")
            if moved.exists():
                moved.unlink()
            path.rename(moved)
            moved_files.append(moved)

    try:
        try:
            act.gbak(switches=["-c", "-v", str(backup_file), str(restored_file)])
        except ExecutionError:
            print(act.stderr)
            print(act.stdout)
            raise

        assert restored_file.exists()
        for path_value in tablespace_files.values():
            assert Path(path_value).resolve().exists(), (
                f"Файл табличного пространства не восстановлен: {path_value}"
            )

        with connect(
            str(restored_file),
            user=act.db.user,
            password=act.db.password,
            charset="UTF8",
        ) as connection:
            assert_database_state(connection.cursor())
    finally:
        for moved in moved_files:
            if moved.exists():
                moved.unlink()
