from flask import Blueprint

from app.utils.helpers import ApiError, error_response, success_response


api_bp = Blueprint('api', __name__)


@api_bp.get('/health')
def health():
    return success_response({
        'status': 'ok',
        'service': 'ssd-engine-backend',
    })


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(error.code, error.message, error.status_code)

    @app.errorhandler(404)
    def handle_not_found(_error):
        return error_response('NOT_FOUND', '资源不存在', 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        return error_response('METHOD_NOT_ALLOWED', '请求方法不允许', 405)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception('Unhandled exception: %s', error)
        return error_response('INTERNAL_ERROR', '服务器内部错误', 500)


from . import analysis, data, device, monitor, task  # noqa: E402,F401

