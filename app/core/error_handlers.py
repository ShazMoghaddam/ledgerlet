"""Translate domain errors into HTTP responses. The only place that mapping lives."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    DomainError,
    NotFoundError,
    UpstreamError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    BusinessRuleError: 422,  # literal: Starlette renamed this constant between versions
    UpstreamError: 502,
}


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    code = next(
        (code for err_type, code in _STATUS_BY_ERROR.items() if isinstance(exc, err_type)),
        status.HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(status_code=code, content={"detail": exc.message})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
