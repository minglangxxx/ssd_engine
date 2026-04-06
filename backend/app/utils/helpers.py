from dataclasses import dataclass

from flask import jsonify, request


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400


def success_response(data, status_code: int = 200):
    return jsonify(data), status_code


def error_response(code: str, message: str, status_code: int = 400):
    return jsonify({
        'error': {
            'code': code,
            'message': message,
        }
    }), status_code


def get_pagination_params(default_page: int = 1, default_page_size: int = 10):
    page = request.args.get('page', default_page, type=int)
    page_size = request.args.get('pageSize', default_page_size, type=int)
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    return page, page_size
