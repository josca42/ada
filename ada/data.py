from abc import abstractmethod
import pandas as pd
from pathlib import Path
import duckdb
import gc
import os
import pickle
import tempfile


class DataFetcher:
    @abstractmethod
    def get_tables_info(self, tables: list[str] = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def run_sql_query(self, table_names) -> str:
        raise NotImplementedError


class Files(DataFetcher):
    """Run sql queries on files in a directory"""

    def __init__(self, data_dir: str, persist_data: bool = True):
        self.data_dir = data_dir if persist_data else tempfile.TemporaryDirectory()
        self.persist_data = persist_data
        self.tables = []
        self.con = duckdb.connect(
            database=os.path.join(
                self.data_dir if persist_data else self.data_dir.name, "files_db.duckdb"
            ),
            read_only=False,
        )

        # Load tables from files_dir_path into duckdb
        for p in Path(data_dir).iterdir():
            if "files_db" in p.name:
                continue
            df, name = self._load_table(p), p.stem
            self.tables += [name]

            if persist_data:
                self.con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
            else:
                self.con.register(name, df)
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

    def exec_sql(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df()

    def save(self, fp: str):
        self.con.close()
        self.con = None
        with open(fp, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(fp: str):
        with open(fp, "rb") as f:
            data_fetcher = pickle.load(f)
        duckdb_fp = str(data_fetcher.data_dir) + "/files_db.duckdb"
        data_fetcher.con = duckdb.connect(duckdb_fp, read_only=False)
        return data_fetcher

    def __del__(self) -> None:
        try:
            self.con.close()
        except:
            pass
        if self.persist_data == False:
            self.data_dir.cleanup()


class Database(DataFetcher):
    ...
