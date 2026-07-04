import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    issuer = Column(String, default="")
    category = Column(String, default="")
    date = Column(String, default="")
    description = Column(Text, default="")
    credential_url = Column(String, default="")
    file_url = Column(String, default="")   # public URL of merged PDF/image in Supabase Storage
    media_type = Column(String, default="") # "pdf" or "image"
    modules = Column(ARRAY(String), default=list)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
