"""HTTP for the two-step import.

preview takes a multipart upload (the CSV plus the column mapping as form
fields); confirm takes JSON (the rows the landlord kept, with categories).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.core.security import CurrentLandlordId
from app.modules.imports.dependencies import ImportServiceDep
from app.modules.imports.schemas import (
    DEFAULT_DATE_FORMAT,
    CsvMapping,
    ImportConfirmRequest,
    ImportPreview,
    ImportResult,
)

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

router = APIRouter(prefix="/properties/{property_id}/imports", tags=["imports"])


def get_csv_mapping(
    date_column: Annotated[str, Form()],
    description_column: Annotated[str, Form()],
    amount_column: Annotated[str | None, Form()] = None,
    paid_in_column: Annotated[str | None, Form()] = None,
    paid_out_column: Annotated[str | None, Form()] = None,
    date_format: Annotated[str, Form()] = DEFAULT_DATE_FORMAT,
    invert_sign: Annotated[bool, Form()] = False,
) -> CsvMapping:
    try:
        return CsvMapping(
            date_column=date_column,
            description_column=description_column,
            amount_column=amount_column,
            paid_in_column=paid_in_column,
            paid_out_column=paid_out_column,
            date_format=date_format,
            invert_sign=invert_sign,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[e["msg"] for e in exc.errors()]) from None


@router.post("/preview", response_model=ImportPreview)
def preview_import(
    property_id: UUID,
    file: UploadFile,
    mapping: Annotated[CsvMapping, Depends(get_csv_mapping)],
    landlord_id: CurrentLandlordId,
    service: ImportServiceDep,
):
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 2 MB")
    return service.preview(landlord_id, property_id, content, mapping)


@router.post("/confirm", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
def confirm_import(
    property_id: UUID,
    payload: ImportConfirmRequest,
    landlord_id: CurrentLandlordId,
    service: ImportServiceDep,
):
    return service.confirm(landlord_id, property_id, payload.rows)
