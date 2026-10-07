from datetime import datetime
from sqlalchemy import String, BigInteger, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


# 클래스 하나 = 테이블 하나. __tablename__이 실제 테이블 이름이 된다.
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account", cascade="all, delete-orphan")


# unique=True라 같은 이름의 카테고리를 두 번 넣으면 DB가 거절한다.
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[str] = mapped_column(String(10))


# 거래는 계좌를 반드시, 카테고리는 있으면 가리킨다(category_id는 비어 있어도 된다).
class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))                        # 외래키
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    memo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    account: Mapped["Account"] = relationship(back_populates="transactions")
