"""Persistence via SQLAlchemy. PostgreSQL in production (DATABASE_URL=postgresql://...), SQLite fallback for zero-setup."""
import json, os, time, uuid
from sqlalchemy import JSON, Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

_default = "sqlite:///" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db"))
URL = os.getenv("DATABASE_URL", _default).replace("postgres://", "postgresql+psycopg2://", 1)
if URL.startswith("postgresql://"):
    URL = URL.replace("postgresql://", "postgresql+psycopg2://", 1)
if URL.startswith("sqlite:///"):
    os.makedirs(os.path.dirname(URL[len("sqlite:///"):]) or ".", exist_ok=True)
engine = create_engine(URL, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created: Mapped[float] = mapped_column(Float)
    jd_title: Mapped[str] = mapped_column(String(300))
    jd: Mapped[dict] = mapped_column(JSON)
    errors: Mapped[list] = mapped_column(JSON)
    candidates: Mapped[list["CandidateResult"]] = relationship(cascade="all, delete-orphan", order_by="CandidateResult.rank")


class CandidateResult(Base):
    __tablename__ = "candidate_results"
    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    cid: Mapped[str] = mapped_column(String(16))
    rank: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON)          # full explanation document


Base.metadata.create_all(engine)


def _clean(o):
    return json.loads(json.dumps(o, default=lambda x: float(x) if hasattr(x, "__float__") else str(x)))


def save(jd: dict, candidates: list, errors: list) -> str:
    aid = uuid.uuid4().hex[:10]
    with Session.begin() as s:
        a = Analysis(id=aid, created=time.time(), jd_title=jd["title"][:300], jd=_clean(jd), errors=_clean(errors))
        a.candidates = [CandidateResult(cid=c["id"], rank=c["rank"], name=c["name"], email=c["email"],
                                        score=c["score"], data=_clean(c)) for c in candidates]
        s.add(a)
    return aid


def load(aid: str):
    with Session() as s:
        a = s.get(Analysis, aid)
        if not a:
            return None
        return {"id": a.id, "jd": a.jd, "errors": a.errors, "candidates": [c.data for c in a.candidates]}


def candidate(aid: str, cid: str):
    with Session() as s:
        row = s.execute(select(CandidateResult, Analysis).join(Analysis).where(
            CandidateResult.analysis_id == aid, CandidateResult.cid == cid)).first()
        return {"jd": row[1].jd, "candidate": row[0].data} if row else None


def recent(n=10):
    with Session() as s:
        rows = s.execute(select(Analysis).order_by(Analysis.created.desc()).limit(n)).scalars().all()
        return [{"id": a.id, "created": a.created, "title": a.jd_title, "candidates": len(a.candidates)} for a in rows]
