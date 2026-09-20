"""例外を、設計どおりのエラーJSON（errorCode・message・fieldErrors・traceId）へ変換する。"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from alteration_rules import AlterationError
from products import error_response
from rule_errors import BusinessRuleError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessRuleError)
    async def handle_rule_error(request: Request, error: BusinessRuleError):
        return error_response(
            error.status_code, error.error_code, error.message, error.field
        )

    @app.exception_handler(AlterationError)
    async def handle_alteration_error(request: Request, error: AlterationError):
        return error_response(
            error.status_code, error.error_code, error.message, error.field
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        return error_response(
            422, "VALIDATION_ERROR", "リクエストの形式が正しくありません。"
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, error: SQLAlchemyError):
        return error_response(
            503,
            "SERVICE_UNAVAILABLE",
            "処理を完了できません。時間をおいて再試行してください。",
        )
