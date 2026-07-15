from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_query = Column(Text, nullable=False)
    mode = Column(String(50), nullable=False, default="react")  # react, cot, act, standard
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    final_answer = Column(Text, nullable=True)

    steps = relationship("TrajectoryStep", back_populates="query", cascade="all, delete-orphan", order_by="TrajectoryStep.step_number")
    citations = relationship("Citation", back_populates="query", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_query": self.user_query,
            "mode": self.mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "final_answer": self.final_answer,
            "steps": [step.to_dict() for step in self.steps],
            "citations": [citation.to_dict() for citation in self.citations],
        }

class TrajectoryStep(Base):
    __tablename__ = "trajectory_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)  # thought, action, observation
    content = Column(Text, nullable=True)
    tool_name = Column(String(100), nullable=True)
    tool_args = Column(Text, nullable=True)  # JSON string or raw text
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)

    query = relationship("Query", back_populates="steps")

    def to_dict(self):
        args_parsed = None
        if self.tool_args:
            try:
                args_parsed = json.loads(self.tool_args)
            except Exception:
                args_parsed = self.tool_args
        return {
            "id": self.id,
            "query_id": self.query_id,
            "step_number": self.step_number,
            "type": self.step_type,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_args": args_parsed,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(100), primary_key=True)  # Primary identifier (e.g. arxiv_id like "2210.03629" or S2 ID)
    arxiv_id = Column(String(100), nullable=True, index=True)
    semantic_scholar_id = Column(String(100), nullable=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)  # JSON list string or comma-separated
    year = Column(Integer, nullable=True)
    abstract = Column(Text, nullable=True)
    pdf_path = Column(Text, nullable=True)
    indexed_at = Column(DateTime, default=get_utc_now, nullable=False)

    citations = relationship("Citation", back_populates="paper")

    def to_dict(self):
        authors_list = []
        if self.authors:
            try:
                authors_list = json.loads(self.authors)
            except Exception:
                authors_list = [a.strip() for a in self.authors.split(",") if a.strip()]
        return {
            "id": self.id,
            "arxiv_id": self.arxiv_id,
            "semantic_scholar_id": self.semantic_scholar_id,
            "title": self.title,
            "authors": authors_list,
            "year": self.year,
            "abstract": self.abstract,
            "pdf_path": self.pdf_path,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
        }

class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(String(100), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)

    query = relationship("Query", back_populates="citations")
    paper = relationship("Paper", back_populates="citations")

    def to_dict(self):
        return {
            "id": self.id,
            "query_id": self.query_id,
            "paper_id": self.paper_id,
            "paper_title": self.paper.title if self.paper else self.paper_id,
            "chunk_text": self.chunk_text,
            "page_number": self.page_number,
        }
