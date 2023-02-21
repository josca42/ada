from sqlmodel import Field, SQLModel, Session, select, create_engine
from typing import Optional
import hashlib
from ada.config import config
from sqlalchemy.dialects.sqlite import insert
import pandas as pd


class Completion(SQLModel, table=True):
    hash_id: Optional[str] = Field(primary_key=True, index=True)
    prompt: str
    stop: Optional[str]
    model: str
    max_tokens: int
    temperature: float
    completion: Optional[str]

    def __init__(self, *args, **kwargs):
        if args:
            raise ValueError("Only kwargs are allowed")

        kwargs["hash_id"] = self.get_hash_id(**kwargs)
        super().__init__(**kwargs)

    @staticmethod
    def get_hash_id(prompt, stop, model, temperature, max_tokens, **kwargs) -> str:
        str_repr = f"{prompt}{stop}{model}{max_tokens}{round(temperature, 2)}"
        hash_id = hashlib.sha256(str_repr.encode("utf8")).hexdigest()
        return hash_id


class CRUDCompletion:
    def __init__(self, model, engine):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLModel class
        * `engine`: A sqlalchemy engine
        """
        self.model = model
        self.engine = engine

    def get(self, hash_id) -> Completion:
        with Session(self.engine) as session:
            stmt = select(Completion).where(Completion.hash_id == hash_id)
            return session.exec(stmt).first()

    def get_all(self) -> list[Completion]:
        with Session(self.engine) as session:
            stmt = select(Completion)
            result = session.exec(stmt).all()
        return pd.DataFrame([r.dict() for r in result])

    def create(self, model_obj: Completion) -> None:
        with Session(self.engine) as session, session.begin():
            stmt = (
                insert(self.model)
                .values(**model_obj.dict(exclude_unset=True))
                .on_conflict_do_nothing()
            )
            session.exec(stmt)


sqlite_fp = config["DATA_DIR"] / "databases" / "db.sqlite"
sqlite_url = f"sqlite:///{str(sqlite_fp)}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


crud_completion = CRUDCompletion(Completion, engine)
