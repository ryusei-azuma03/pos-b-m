# models.py

from sqlalchemy import Column, Integer, String, CHAR, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class MProductMatsuda(Base):
    __tablename__ = "m_product_matsuda"

    PRD_ID = Column(Integer, primary_key=True, nullable=False)
    CODE   = Column(CHAR(13), nullable=False)
    NAME   = Column(String(50), nullable=False)
    PRICE  = Column(Integer, nullable=False)
    
    # リレーション設定は必須ではないが、必要に応じて
    # transaction_details = relationship("TransactionDetailsMatsuda", back_populates="product")


class TransactionsMatsuda(Base):
    __tablename__ = "transactions_matsuda"

    TRD_ID    = Column(Integer, primary_key=True, autoincrement=True)
    DATETIME  = Column(TIMESTAMP, nullable=False)
    EMP_CD    = Column(CHAR(10), nullable=False)
    STORE_CD  = Column(CHAR(5),  nullable=False)
    POS_NO    = Column(CHAR(3),  nullable=False)
    TOTAL_AMT = Column(Integer,  nullable=False)
    
    # リレーション
    details = relationship("TransactionDetailsMatsuda", back_populates="transaction")


class TransactionDetailsMatsuda(Base):
    __tablename__ = "transaction_details_matsuda"

    TRD_ID    = Column(Integer, ForeignKey("transactions_matsuda.TRD_ID", ondelete="CASCADE"), primary_key=True)
    DTL_ID    = Column(Integer, primary_key=True, nullable=False)
    PRD_ID    = Column(Integer, ForeignKey("m_product_matsuda.PRD_ID", ondelete="RESTRICT"), nullable=False)
    PRD_CODE  = Column(CHAR(13),  nullable=False)
    PRD_NAME  = Column(String(50), nullable=False)
    PRD_PRICE = Column(Integer,    nullable=False)
    
    transaction = relationship("TransactionsMatsuda", back_populates="details")
    # product     = relationship("MProductMatsuda", back_populates="transaction_details")
