from datetime import datetime
from pydantic import BaseModel


class AccountCreate(BaseModel):     # 입력용: 클라이언트가 보내는 형식
    name: str
    balance: int = 0


class AccountRead(BaseModel):       # 출력용: 서버가 돌려주는 형식(id 포함)
    id: int
    name: str
    balance: int
    model_config = {"from_attributes": True}   # SQLAlchemy 객체→스키마 자동 변환 허용


class TransactionCreate(BaseModel):  # 입력: id·occurred_at 없음(서버가 정함)
    account_id: int
    category_id: int | None = None
    amount: int
    memo: str | None = None


class TransactionRead(BaseModel):
    id: int
    account_id: int
    amount: int
    memo: str | None
    occurred_at: datetime
    model_config = {"from_attributes": True}


class AccountReadWithTx(BaseModel):  # 계좌 + 거래 중첩 응답
    id: int
    name: str
    balance: int
    transactions: list[TransactionRead] = []
    model_config = {"from_attributes": True}
