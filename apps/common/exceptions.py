#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import copy
import logging

from django.http import HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('django.request')

ERROR_CODE_SUCCESS = 0

# client side error
ERROR_CODE_AUTH_FAILED = 1001
ERROR_CODE_VALIDATE_FORM_FAILED = 1002
ERROR_CODE_INVALID_PARAMETER = 1003
ERROR_CODE_NEW_PASSWORD_NOT_MATCH = 1004
ERROR_CODE_RECORD_NOT_EXIST = 1005

# permission error
ERROR_CODE_AUTH_REQUIRED = 4001
ERROR_CODE_PERMISSION_DENY = 4002

ERROR_CODE_UNKNOWN = 9999

ERROR_CODES = {
    ERROR_CODE_SUCCESS: {
        "ret": ERROR_CODE_SUCCESS,
        "errmsg": "成功"
    },
    ERROR_CODE_AUTH_FAILED: {
        "ret": ERROR_CODE_AUTH_FAILED,
        "errmsg": u"认证失败：用户名/密码不匹配"
    },
    ERROR_CODE_NEW_PASSWORD_NOT_MATCH: {
        "ret": ERROR_CODE_NEW_PASSWORD_NOT_MATCH,
        "errmsg": "验证表单失败，新密码不匹配"
    },
    ERROR_CODE_VALIDATE_FORM_FAILED: {
        "ret": ERROR_CODE_VALIDATE_FORM_FAILED,
        "errmsg": "验证表单失败，请确认表单的必填项都填写完整和数据格式正确"
    },
    ERROR_CODE_RECORD_NOT_EXIST: {
        "ret": ERROR_CODE_RECORD_NOT_EXIST,
        "errmsg": "记录不存在"
    },
    ERROR_CODE_INVALID_PARAMETER: {
        "ret": ERROR_CODE_INVALID_PARAMETER,
        "errmsg": "参数错误"
    },

    ERROR_CODE_AUTH_REQUIRED: {
        "ret": ERROR_CODE_AUTH_REQUIRED,
        "errmsg": "该操作需要进行认证，请先登录"
    },
    ERROR_CODE_PERMISSION_DENY: {
        "ret": ERROR_CODE_PERMISSION_DENY,
        "errmsg": "没有足够的权限进行该操作"
    },

    ERROR_CODE_UNKNOWN: {
        "ret": ERROR_CODE_UNKNOWN,
        "errmsg": "未知错误"
    },
}

_SUCCESS_RESPONSE_CODE = ERROR_CODES[ERROR_CODE_SUCCESS]


def build_response_result(error_code, errors=None):
    ret = copy.deepcopy(ERROR_CODES[error_code])
    if errors:
        ret['errmsg-detail'] = errors
    return ret


def build_success_response_result():
    ret = copy.deepcopy(_SUCCESS_RESPONSE_CODE)
    ret['errmsg'] = ret['errmsg']
    return ret


class AjaxException(Exception):
    def __init__(self, code, errors=None):
        self.code = code
        self.errors = errors


class AjaxRecordNotExist(AjaxException):
    def __init__(self, errors=None):
        super(AjaxRecordNotExist, self).__init__(ERROR_CODE_RECORD_NOT_EXIST, errors=errors)


class AjaxUnknownException(AjaxException):
    def __init__(self, errors=None):
        super(AjaxUnknownException, self).__init__(ERROR_CODE_UNKNOWN, errors=errors)


class AjaxValidateFormFailed(AjaxException):
    def __init__(self, errors=None):
        super(AjaxValidateFormFailed, self).__init__(ERROR_CODE_VALIDATE_FORM_FAILED, errors=errors)


class AjaxInvalidParameter(AjaxException):
    def __init__(self, errors=None):
        super(AjaxInvalidParameter, self).__init__(ERROR_CODE_INVALID_PARAMETER, errors=errors)


class AjaxAuthRequired(AjaxException):
    def __init__(self, errors=None):
        super(AjaxAuthRequired, self).__init__(ERROR_CODE_AUTH_REQUIRED, errors=errors)


class AjaxPermissionDeny(AjaxException):
    def __init__(self, errors=None):
        super(AjaxPermissionDeny, self).__init__(ERROR_CODE_PERMISSION_DENY, errors=errors)


class AjaxExceptionMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if not isinstance(exception, AjaxException):
            logger.error(
                msg=f'Internal Server Error: {request.path}',
                exc_info=sys.exc_info(),
                extra={
                    'status_code': 500,
                    'request': request
                }
            )
            return HttpResponse(u'服务器内部错误', status=500)
        if exception.code in ERROR_CODES:
            error_code = ERROR_CODES[exception.code]
        else:
            error_code = ERROR_CODES[ERROR_CODE_UNKNOWN]

        ret = copy.deepcopy(error_code)
        # simplicity, only have first error for browser to show
        if isinstance(exception.errors, str):
            ret["errmsg-detail"] = exception.errors
        else:
            ret["errmsg-detail"] = dict(
                [(key, error[0]) for key, error in exception.errors.items()]
            ) if exception.errors else {}

        return JsonResponse(ret)
