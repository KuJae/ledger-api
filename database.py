import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()                                              # .env를 읽어 환경변수로 등록
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ledger.db")

kwargs = {"echo": True}                                    # echo=True: 실행되는 SQL을 콘솔에 출력(학습에 매우 유용)
if DATABASE_URL.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}  # SQLite 전용 옵션

# Engine: DB로 가는 연결의 관리자. 앱에 하나만 만들어 공유(무거운 자원).
engine = create_engine(DATABASE_URL, **kwargs)

# Session 공장: Session=DB와의 한 번의 대화(작업 단위). commit할 때 한꺼번에 반영.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Base: 모든 모델(테이블) 클래스의 공통 부모.
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()   # 이 요청 전용 세션을 연다
    try:
        yield db          # 요청 처리 함수에 세션을 건네준다
    finally:
        db.close()        # 성공/실패 무관하게 반드시 닫는다(누수 방지)
