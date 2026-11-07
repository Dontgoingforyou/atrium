"""Юнит-тесты чистого парсера CSV-выгрузки Jira Tempo (без БД)."""

from __future__ import annotations

from datetime import date

import pytest
from app.core.exceptions import ValidationError
from app.portal_time_entries.schemas.time_entry import TIME_ENTRY_TASK_NAME_MAX_LENGTH
from app.portal_time_entries.services._jira_csv_import import (
    _MAX_IMPORT_ROWS,
    ImportRowError,
    ParsedImportRow,
    parse_jira_worklog_csv,
)

_HEADER = '"Ключ задачи","Тема задачи","Часов","Дата работы","Имя пользователя"\n'


def _csv(rows: str) -> bytes:
    return (_HEADER + rows).encode("utf-8")


def test_parses_valid_rows() -> None:
    content = _csv(
        '"STLT-1","Сделать штуку","0.5","2026-07-01 08:43","ee.nikolaev"\n'
        '"STLT-2","Административные задачи","1.5","2026-07-02 16:34","ee.nikolaev"\n'
    )
    rows, errors = parse_jira_worklog_csv(content)
    assert errors == []
    assert rows == [
        ParsedImportRow(task_name="Сделать штуку", worked_on=date(2026, 7, 1), minutes=30),
        ParsedImportRow(task_name="Административные задачи", worked_on=date(2026, 7, 2), minutes=90),
    ]


def test_decodes_utf8_bom() -> None:
    content = b"\xef\xbb\xbf" + _csv('"STLT-1","Тема","1","2026-07-01 08:43","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert errors == []
    assert rows == [ParsedImportRow(task_name="Тема", worked_on=date(2026, 7, 1), minutes=60)]


def test_missing_required_column_raises_validation_error() -> None:
    content = '"Ключ задачи","Часов","Дата работы"\n"STLT-1","1","2026-07-01 08:43"\n'.encode()
    with pytest.raises(ValidationError, match="Тема задачи"):
        parse_jira_worklog_csv(content)


def test_empty_file_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="Пустой CSV"):
        parse_jira_worklog_csv(b"")


@pytest.mark.parametrize(
    ("hours", "expected_message_part"),
    [
        ("не число", "часов"),
        ("0", "больше 0"),
        ("-1", "больше 0"),
        ("25", "24ч"),
        ("inf", "часов"),
        ("nan", "часов"),
        ("Infinity", "часов"),
    ],
)
def test_invalid_hours_reported_as_row_error(hours: str, expected_message_part: str) -> None:
    content = _csv(f'"STLT-1","Тема","{hours}","2026-07-01 08:43","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert rows == []
    assert len(errors) == 1
    assert errors[0].row == 2
    assert expected_message_part in errors[0].message


def test_invalid_date_reported_as_row_error() -> None:
    content = _csv('"STLT-1","Тема","1","не дата","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert rows == []
    assert errors == [ImportRowError(row=2, message="Не удалось разобрать дату «не дата»")]


def test_empty_task_name_reported_as_row_error() -> None:
    content = _csv('"STLT-1","","1","2026-07-01 08:43","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert rows == []
    assert errors == [ImportRowError(row=2, message="Не указана тема задачи")]


def test_invalid_rows_do_not_block_valid_rows() -> None:
    content = _csv(
        '"STLT-1","Тема 1","1","2026-07-01 08:43","u"\n'
        '"STLT-2","","1","2026-07-02 08:43","u"\n'
        '"STLT-3","Тема 3","0.5","2026-07-03 08:43","u"\n'
    )
    rows, errors = parse_jira_worklog_csv(content)
    assert [r.task_name for r in rows] == ["Тема 1", "Тема 3"]
    assert [e.row for e in errors] == [3]


def test_date_without_time_component_is_accepted() -> None:
    content = _csv('"STLT-1","Тема","1","2026-07-01","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert errors == []
    assert rows[0].worked_on == date(2026, 7, 1)


def test_too_many_rows_raises_validation_error() -> None:
    row_line = '"STLT-1","Тема","1","2026-07-01 08:43","u"\n'
    content = _csv(row_line * (_MAX_IMPORT_ROWS + 1))
    with pytest.raises(ValidationError, match=str(_MAX_IMPORT_ROWS)):
        parse_jira_worklog_csv(content)


def test_non_utf8_bytes_raise_validation_error() -> None:
    with pytest.raises(ValidationError, match="UTF-8"):
        parse_jira_worklog_csv(b"\xff\xfe\x00\x00not-utf8")


def test_task_name_longer_than_schema_limit_is_row_error() -> None:
    too_long = "A" * (TIME_ENTRY_TASK_NAME_MAX_LENGTH + 1)
    content = _csv(f'"STLT-1","{too_long}","1","2026-07-01 08:43","u"\n')
    rows, errors = parse_jira_worklog_csv(content)
    assert rows == []
    assert len(errors) == 1
    assert errors[0].row == 2
    assert str(TIME_ENTRY_TASK_NAME_MAX_LENGTH) in errors[0].message
