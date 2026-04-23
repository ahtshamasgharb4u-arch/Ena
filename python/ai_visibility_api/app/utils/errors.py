from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


def error_payload(code: str, message: str, details=None):
    p = {"error": {"code": code, "message": message}}
    if details is not None:
        p["error"]["details"] = details
    return p


def register_error_handlers(app: Flask):
    @app.errorhandler(HTTPException)
    def http_exc(e: HTTPException):
        return jsonify(error_payload(code=e.name, message=e.description)), e.code

    @app.errorhandler(Exception)
    def unhandled(e: Exception):
        return jsonify(error_payload(code="InternalServerError", message=str(e))), 500

