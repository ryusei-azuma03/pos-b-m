from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
import models, schemas
from sqlalchemy import func

app = FastAPI()

# ===== CORS設定ここから =====
# フロントエンドが稼働しているURLを指定
# 例として localhost, 127.0.0.1, 192.168.10.102 をすべて許可
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://localhost:3000",
    "http://192.168.10.102:3000",
    "https://192.168.10.102:3000",
    "https://tech0-gen8-step4-pos-app-39.azurewebsites.net"
    # 必要に応じて他のドメインも追加
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] (開発中のみ推奨)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ===== CORS設定ここまで =====

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# 1) 新規取引を作成
# ---------------------------
@app.post("/api/transactions", response_model=schemas.Transaction)
def create_transaction(tran: schemas.TransactionCreate, db: Session = Depends(get_db)):
    new_tran = models.TransactionsMatsuda(
        DATETIME  = tran.DATETIME,
        EMP_CD    = tran.EMP_CD,
        STORE_CD  = tran.STORE_CD,
        POS_NO    = tran.POS_NO,
        TOTAL_AMT = tran.TOTAL_AMT
    )
    db.add(new_tran)
    db.commit()
    db.refresh(new_tran)  # ここでAUTO_INCREMENTされたTRD_IDが決まる
    return new_tran

# ---------------------------
# 2) 取引を参照
# ---------------------------
@app.get("/api/transactions", response_model=list[schemas.Transaction])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.TransactionsMatsuda).all()

@app.get("/api/transactions/{trd_id}", response_model=schemas.TransactionWithDetails)
def get_transaction(trd_id: int, db: Session = Depends(get_db)):
    tran = db.query(models.TransactionsMatsuda).filter_by(TRD_ID=trd_id).first()
    if not tran:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tran

# ---------------------------
# 3) 取引を更新
# ---------------------------
@app.put("/api/transactions/{trd_id}", response_model=schemas.Transaction)
def update_transaction(trd_id: int, tran_data: schemas.TransactionBase, db: Session = Depends(get_db)):
    tran = db.query(models.TransactionsMatsuda).filter_by(TRD_ID=trd_id).first()
    if not tran:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tran.DATETIME  = tran_data.DATETIME
    tran.EMP_CD    = tran_data.EMP_CD
    tran.STORE_CD  = tran_data.STORE_CD
    tran.POS_NO    = tran_data.POS_NO
    tran.TOTAL_AMT = tran_data.TOTAL_AMT

    db.commit()
    db.refresh(tran)
    return tran

# ---------------------------
# 4) 取引を削除
# ---------------------------
@app.delete("/api/transactions/{trd_id}")
def delete_transaction(trd_id: int, db: Session = Depends(get_db)):
    tran = db.query(models.TransactionsMatsuda).filter_by(TRD_ID=trd_id).first()
    if not tran:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(tran)
    db.commit()
    # ON DELETE CASCADE により紐づく明細も削除される
    return {"detail": "Transaction deleted."}

# ---------------------------
# 5) 取引明細を追加
# ---------------------------
@app.post("/api/transactions/{trd_id}/details", response_model=schemas.TransactionDetail)
def add_transaction_detail(
    trd_id: int,
    detail_data: schemas.TransactionDetailBase,
    db: Session = Depends(get_db)
):
    # 取引存在チェック
    tran = db.query(models.TransactionsMatsuda).filter_by(TRD_ID=trd_id).first()
    if not tran:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # DTL_ID が重複しないか一応チェック
    exist_detail = db.query(models.TransactionDetailsMatsuda)\
                     .filter_by(TRD_ID=trd_id, DTL_ID=detail_data.DTL_ID).first()
    if exist_detail:
        raise HTTPException(status_code=400, detail="DTL_ID already exists in this transaction.")

    # 明細行を追加
    new_detail = models.TransactionDetailsMatsuda(
        TRD_ID    = trd_id,
        DTL_ID    = detail_data.DTL_ID,
        PRD_ID    = detail_data.PRD_ID,
        PRD_CODE  = detail_data.PRD_CODE,
        PRD_NAME  = detail_data.PRD_NAME,
        PRD_PRICE = detail_data.PRD_PRICE
    )
    db.add(new_detail)

    # 合計金額を更新 (単純に加算する例)
    tran.TOTAL_AMT += detail_data.PRD_PRICE

    db.commit()
    db.refresh(new_detail)
    return new_detail

# ---------------------------
# 6) 取引明細の削除
# ---------------------------
@app.delete("/api/transactions/{trd_id}/details/{dtl_id}")
def delete_transaction_detail(trd_id: int, dtl_id: int, db: Session = Depends(get_db)):
    detail = db.query(models.TransactionDetailsMatsuda)\
               .filter_by(TRD_ID=trd_id, DTL_ID=dtl_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="Detail not found")

    # 親取引を取得して後で合計再集計する
    tran = db.query(models.TransactionsMatsuda).filter_by(TRD_ID=trd_id).first()

    # 明細削除
    db.delete(detail)

    # 合計金額を再集計 (差分計算でも良い)
    if tran:
        sum_price = db.query(func.sum(models.TransactionDetailsMatsuda.PRD_PRICE)) \
                      .filter_by(TRD_ID=trd_id).scalar()
        tran.TOTAL_AMT = sum_price if sum_price else 0

    db.commit()
    return {"detail": "Detail deleted."}

# ---------------------------
# 7) 商品コード検索 (新規追加)
# ---------------------------
@app.get("/api/products-by-code/{code}", response_model=schemas.Product)
def get_product_by_code(code: str, db: Session = Depends(get_db)):
    """
    商品コード(code)で商品マスタ(m_product_matsuda)を検索し、
    該当商品を返す。見つからなければ404エラー。
    """
    product = db.query(models.MProductMatsuda).filter(models.MProductMatsuda.CODE == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product
