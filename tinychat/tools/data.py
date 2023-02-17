from abc import abstractmethod
import pandas as pd
from pathlib import Path
import duckdb
import gc
import os
import pickle
import tempfile
from ..utils import log_input_output


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
        sql_query = self.llm(prompt, stop=stop)
        return sql_query

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

    def __init__(self, data_dir: str, llm, persist_data: bool = True):
        self.data_dir = data_dir if persist_data else tempfile.TemporaryDirectory()
        self.llm = llm
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

    def run_sql_query(self, query: str) -> pd.DataFrame:
        df = self.con.execute(query).df()
        df_text = "\n" + df.head().to_markdown()
        return dict(text=df_text, data=df.to_json())

    def save(self, folder: str):
        self.con.close()
        self.con = None
        with open(folder + "/data_agent.pkl", "wb") as fp:
            pickle.dump(self, fp)

    @staticmethod
    def load(data_dir, llm=None):
        with open(str(data_dir) + "/data_agent.pkl", "rb") as f:
            data_agent = pickle.load(f)
        duckdb_fp = str(data_agent.data_dir) + "/files_db.duckdb"
        data_agent.con = duckdb.connect(duckdb_fp, read_only=False)
        if llm:
            data_agent.llm = llm
        return data_agent

    def __del__(self) -> None:
        try:
            self.con.close()
        except:
            pass
        if self.persist_data == False:
            self.temp_dir.cleanup()


class Database(Data):
    ...
