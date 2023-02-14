from sqlmodel import Field, SQLModel, Session, select, create_engine
from pathlib import Path
from sqlalchemy.dialects.sqlite import insert
from datetime import datetime, timedelta
from typing import Optional
from dotenv import dotenv_values
from sqlalchemy import Column, DateTime


class Question(SQLModel, table=True):
    text: str = Field(primary_key=True, index=True)
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )


class CRUDQuestion:
    def __init__(self, model: Question, engine):
        self.model = model
        self.engine = engine

    def list_previous_questions(self) -> set:
        with Session(self.engine) as session:
            stmt = (
                select(Question.text)
                .where(Question.created_at > datetime.utcnow() - timedelta(days=7))
                .distinct()
                .limit(50)
            )
            return list(session.exec(stmt))

    def create(self, model_obj: Question) -> None:
        with Session(self.engine) as session, session.begin():
            stmt = (
                insert(self.model)
                .values(**model_obj.dict(exclude_unset=True))
                .on_conflict_do_nothing()
            )
            session.exec(stmt)


config = dotenv_values()
sqlite_fp = Path(config["DATA_DIR"]) / "databases" / "db.sqlite"
sqlite_url = f"sqlite:///{str(sqlite_fp)}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


crud_question = CRUDQuestion(Question, engine)
