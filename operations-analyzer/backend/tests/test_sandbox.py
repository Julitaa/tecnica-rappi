import pandas as pd
import pytest
from app.chat.sandbox import SqlSandbox, SqlValidationError


@pytest.fixture
def sandbox():
    metrics_df = pd.DataFrame([
        {"country": "CO", "zone": "Chapinero", "metric": "Lead Penetration",
         "week_offset": 0, "value": 0.5}
    ])
    orders_df = pd.DataFrame([
        {"country": "CO", "zone": "Chapinero", "metric": "Orders",
         "week_offset": 0, "value": 1000}
    ])
    return SqlSandbox(metrics_df, orders_df)


def test_select_query_works(sandbox):
    result = sandbox.run("SELECT * FROM metrics_df")
    assert len(result["data"]) == 1


def test_select_with_filter(sandbox):
    result = sandbox.run("SELECT zone, value FROM metrics_df WHERE country = 'CO'")
    assert result["data"][0]["zone"] == "Chapinero"


def test_insert_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("INSERT INTO metrics_df VALUES ('X', 'Y', 'Z', 0, 0.1)")


def test_update_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("UPDATE metrics_df SET value = 0")


def test_delete_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("DELETE FROM metrics_df")


def test_unknown_table_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("SELECT * FROM users")


def test_attach_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("ATTACH 'evil.db' AS evil")
