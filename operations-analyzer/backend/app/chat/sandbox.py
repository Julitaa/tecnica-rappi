"""SQL sandbox: validate with sqlglot, run with DuckDB over pandas."""
from __future__ import annotations
import duckdb
import pandas as pd
import sqlglot
from sqlglot import expressions as exp

ALLOWED_TABLES = {"metrics_df", "orders_df"}
MAX_ROWS = 1000


class SqlValidationError(ValueError):
    pass


class SqlSandbox:
    def __init__(self, metrics_df: pd.DataFrame, orders_df: pd.DataFrame):
        self.metrics_df = metrics_df
        self.orders_df = orders_df

    def _validate(self, sql: str) -> None:
        try:
            parsed = sqlglot.parse(sql, dialect="duckdb")
        except Exception as e:
            raise SqlValidationError(f"Parse error: {e}") from e
        if len(parsed) != 1:
            raise SqlValidationError("Solo se permite una sentencia.")
        stmt = parsed[0]
        if not isinstance(stmt, (exp.Select, exp.With)):
            raise SqlValidationError(
                f"Solo SELECT/WITH permitidos; encontrado {type(stmt).__name__}."
            )
        forbidden_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
            exp.Alter, exp.Attach, exp.Pragma, exp.Command, exp.Copy,
        )
        for node in stmt.walk():
            if isinstance(node, forbidden_types):
                raise SqlValidationError(
                    f"Sentencia no permitida: {type(node).__name__}"
                )
        for table in stmt.find_all(exp.Table):
            name = table.name.lower()
            if name not in ALLOWED_TABLES:
                raise SqlValidationError(f"Tabla no permitida: {name}")

    def run(self, sql: str) -> dict:
        self._validate(sql)
        con = duckdb.connect(":memory:")
        try:
            con.register("metrics_df", self.metrics_df)
            con.register("orders_df", self.orders_df)
            df = con.execute(sql).fetchdf()
        finally:
            con.close()
        truncated = len(df) > MAX_ROWS
        if truncated:
            df = df.head(MAX_ROWS)
        return {
            "data": df.to_dict("records"),
            "summary": (f"{len(df)} filas devueltas"
                        + (f" (truncado a {MAX_ROWS})" if truncated else "")),
            "metadata": {"rows": len(df), "truncated": truncated},
        }
