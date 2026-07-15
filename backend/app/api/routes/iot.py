from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import IotBatchOut
from app.services.iot_ingestion import ingest_gateway_batch

router = APIRouter(prefix="/iot/v1")


@router.post("/ingest/batch", response_model=IotBatchOut, status_code=status.HTTP_200_OK)
async def ingest_iot_batch(
    request: Request,
    x_agro_gateway_id: str | None = Header(default=None),
    x_agro_timestamp: str | None = Header(default=None),
    x_agro_nonce: str | None = Header(default=None),
    x_agro_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> IotBatchOut:
    body = await request.body()
    return ingest_gateway_batch(
        db,
        body=body,
        gateway_header=x_agro_gateway_id,
        timestamp_header=x_agro_timestamp,
        nonce_header=x_agro_nonce,
        signature_header=x_agro_signature,
    )
