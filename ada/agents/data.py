from __future__ import annotations

from typing import Any, Iterable, Optional
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, inspect
from abc import abstractmethod
import pandas as pd
from pathlib import Path
import duckdb
import tempfile
import gc
import os
from loguru import logger
import pickle
from .utils import complete_prompt, log_input_output


data_prompt_template = """Given an input question, first create a syntactically correct sqlite query to run, then look at the results of the query and return the answer. You can order the results by a relevant column to return the most interesting examples in the database at the top.

Never query for all the columns from a specific table, only ask for the few relevant columns given the question.

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.

Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Only use the following tables:

{tables_info}

Question: {question}
SQLQuery: """


class Data:
    @abstractmethod
    def get_tables_info(self, tables: list[str] = None) -> str:
        raise NotImplementedError

    def get_prompt(self, question: str, tables_info: str = None) -> str:
        tables_info = tables_info if tables_info else self.get_tables_info()
        return data_prompt_template.format(tables_info=tables_info, question=question)

    @log_input_output(log_input=False, log_output=True)
    def get_sql_query_from_prompt(
        self, prompt: str, stop: str = "\nSQLResult:", max_tokens: int = 2_000
    ) -> str:
        sql_query = complete_prompt(
            prompt=prompt,
            stop=stop,
            max_tokens=max_tokens,
            openai_api_key=self.openai_api_key,
        )
        return sql_query.completion

    @abstractmethod
    def run_sql_query(self, table_names) -> str:
        raise NotImplementedError

    @log_input_output(log_input=True, log_output=False)
    def query(self, question: str) -> str:
        prompt = self.get_prompt(question, self.tables_info)
        sql_query = self.get_sql_query_from_prompt(prompt)
        return self.run_sql_query(sql_query)


class Files(Data):
    """Run sql queries on files in a directory"""

    def __init__(self, files_dir_path: str, openai_api_key: str = None):
        self.dir_path = files_dir_path
        self.openai_api_key = openai_api_key
        self.tables = []
        self.con = duckdb.connect(
            database=os.path.join(str(files_dir_path), "files_db.duckdb"),
            read_only=False,
        )

        # Load tables from files_dir_path into duckdb
        for p in Path(files_dir_path).iterdir():
            if "files_db" in p.name:
                continue
            df, name = self._load_table(p), p.stem
            self.tables += [name]
            self.con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        del df
        gc.collect()

        self.tables_info = self.get_tables_info()

    def _load_table(self, path: Path) -> pd.DataFrame:
        """Load table from file"""
        file_type = path.suffix[1:]
        if "xlsx" in file_type:
            file_type = "excel"
        df = getattr(pd, f"read_{file_type}")(path)
        df = df.rename(columns={c: c.strip().lower() for c in df.columns})
        return df

    def get_tables_info(self, tables: list[str] = None) -> str:
        tables = tables if tables else self.tables
        tables_info = ""
        for table in tables:
            query = f"""SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table}';"""
            cols = self.con.execute(query).fetchall()
            tables_info += (
                f"Table '{table}' has columns: "
                + ", ".join([f"{col_name} ({col_type})" for col_name, col_type in cols])
                + ".\n"
            )
        return tables_info

    def run_sql_query(self, query: str) -> pd.DataFrame:
        df = self.con.execute(query).df()
        df_text = "\n" + df.head().to_markdown()
        return dict(text=df_text, data=df.to_json())

    def save(self, folder: Path):
        self.con.close()
        self.con = None
        with open(folder / "data_agent.pkl", "wb") as fp:
            pickle.dump(self, fp)

    @staticmethod
    def load(fp):
        with open(str(fp) + "/data_agent.pkl", "rb") as f:
            data_obj = pickle.load(f)
        duckdb_fp = str(data_obj.dir_path) + "/files_db.duckdb"
        data_obj.con = duckdb.connect(duckdb_fp, read_only=False)
        return data_obj

    # def __del__(self) -> None:
    #     self.con.close()
    #     self.temp_dir.cleanup()

    # self.temp_dir = tempfile.TemporaryDirectory()
    # self.con = duckdb.connect(
    #     database=os.path.join(self.temp_dir.name, "files_db.duckdb"),
    #     read_only=False,
    # )


class Database(Data):
    """Run SQL queries on a database"""

    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        ignore_tables: Optional[list[str]] = None,
        include_tables: Optional[list[str]] = None,
        sample_rows_in_table_info: int = 0,
    ):
        """Create engine from database URI."""
        self._engine = engine
        self._schema = schema
        if include_tables and ignore_tables:
            raise ValueError("Cannot specify both include_tables and ignore_tables")

        self._inspector = inspect(self._engine)
        self._all_tables = set(self._inspector.get_table_names(schema=schema))
        self._include_tables = set(include_tables) if include_tables else set()
        if self._include_tables:
            missing_tables = self._include_tables - self._all_tables
            if missing_tables:
                raise ValueError(
                    f"include_tables {missing_tables} not found in database"
                )
        self._ignore_tables = set(ignore_tables) if ignore_tables else set()
        if self._ignore_tables:
            missing_tables = self._ignore_tables - self._all_tables
            if missing_tables:
                raise ValueError(
                    f"ignore_tables {missing_tables} not found in database"
                )
        self._sample_rows_in_table_info = sample_rows_in_table_info
        self.tables_info = self.get_tables_info()

    @classmethod
    def from_uri(cls, database_uri: str, **kwargs: Any) -> Database:
        """Construct a SQLAlchemy engine from URI."""
        return cls(create_engine(database_uri), **kwargs)

    @property
    def dialect(self) -> str:
        """Return string representation of dialect to use."""
        return self._engine.dialect.name

    def get_table_names(self) -> Iterable[str]:
        """Get names of tables available."""
        if self._include_tables:
            return self._include_tables
        return self._all_tables - self._ignore_tables

    def get_tables_info(self, table_names: Optional[list[str]] = None) -> str:
        """Get information about specified tables.
        If `sample_rows_in_table_info`, the specified number of sample rows will be
        appended to each table description. This can increase performance as
        demonstrated by Rajkumar et al, 2022 (https://arxiv.org/abs/2204.00498).
        """
        all_table_names = self.get_table_names()
        if table_names is not None:
            missing_tables = set(table_names).difference(all_table_names)
            if missing_tables:
                raise ValueError(f"table_names {missing_tables} not found in database")
            all_table_names = table_names

        template = "Table '{table_name}' has columns: {columns}."

        tables = []
        for table_name in all_table_names:
            columns = []
            for column in self._inspector.get_columns(table_name, schema=self._schema):
                columns.append(f"{column['name']} ({str(column['type'])})")
            column_str = ", ".join(columns)
            table_str = template.format(table_name=table_name, columns=column_str)

            if self._sample_rows_in_table_info:
                row_template = (
                    " Here is an example of {n_rows} rows from this table "
                    "(long strings are truncated):\n"
                    "{sample_rows}"
                )
                sample_rows = self.run(
                    f"SELECT * FROM '{table_name}' LIMIT "
                    f"{self._sample_rows_in_table_info}"
                )
                sample_rows = eval(sample_rows)
                if len(sample_rows) > 0:
                    n_rows = len(sample_rows)
                    sample_rows = "\n".join(
                        [" ".join([str(i)[:100] for i in row]) for row in sample_rows]
                    )
                    table_str += row_template.format(
                        n_rows=n_rows, sample_rows=sample_rows
                    )

            tables.append(table_str)
        return "\n".join(tables)

    def run_sql_query(self, command: str) -> str:
        """Execute a SQL command and return a string representing the results.
        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        with self._engine.begin() as connection:
            if self._schema is not None:
                connection.exec_driver_sql(f"SET search_path TO {self._schema}")
            cursor = connection.exec_driver_sql(command)
            if cursor.returns_rows:
                result = cursor.fetchall()
                return str(result)
        return ""
