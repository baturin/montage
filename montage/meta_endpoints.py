
import json
import datetime

from clastic import render_basic, GET, POST
from clastic.errors import Forbidden
from boltons.strutils import indent
from boltons.jsonutils import reverse_iter_lines

from rdb import MaintainerDAO

DEFAULT_LINE_COUNT = 500


def get_meta_routes():
    ret = [GET('/maintainer/active_users', get_active_users),
           GET('/logs/audit', get_audit_logs),
           GET('/logs/api', get_api_log_tail, render_basic),
           GET('/logs/api_exc', get_api_exc_log_tail, render_basic),
           GET('/logs/feel', get_frontend_error_log, render_basic),
           POST('/logs/feel', post_frontend_error_log, render_basic)]
    return ret


def get_active_users(user_dao):
    maint_dao = MaintainerDAO(user_dao)
    users = maint_dao.get_active_users()
    data = []
    for user in users:
        ud = user.to_details_dict()
        ud['last_active_date'] = ud['last_active_date'].isoformat()
        data.append(ud)
    return {'data': data}


def get_audit_logs(user_dao, request):
    # TODO: Docs
    maint_dao = MaintainerDAO(user_dao)
    limit = request.values.get('limit', 10)
    offset = request.values.get('offset', 0)
    audit_logs = maint_dao.get_audit_log(limit=limit, offset=offset)
    data = [l.to_info_dict() for l in audit_logs]
    return {'data': data}


def get_api_log_tail(config, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden()
    request_dict = request_dict or {}
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))

    log_path = config.get('api_log_path')
    if not log_path:
        return ['(no API log path configured)']

    lines = _get_tail_from_path(log_path, count=count)

    return lines


def get_api_exc_log_tail(config, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden()
    request_dict = request_dict or {}
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))

    log_path = config.get('api_exc_log_path')
    if not log_path:
        return ['(no API exception log path configured)']
    lines = _get_tail_from_path(log_path, count=count)

    return lines


def _get_tail_from_path(path, count=DEFAULT_LINE_COUNT):
    log_path = open(path, 'rb')

    rliter = reverse_iter_lines(log_path)
    lines = []
    for i, line in enumerate(rliter):
        if i > count:
            break
        lines.append(line)
    lines.reverse()
    return lines


def post_frontend_error_log(user, config, request_dict):
    feel_path = config.get('feel_log_path', None)
    if not feel_path:
        return ['(no front-end error log configured)']
    now = datetime.datetime.utcnow()
    now_str = now.isoformat()

    username = user.username if user else '<nouser>'
    err_bytes = json.dumps(request_dict, sort_keys=True, indent=2)
    err_bytes = indent(err_bytes, '  ')
    with open(feel_path, 'ab') as feel_file:
        feel_file.write('Begin error at %s:\n\n' % now_str)
        feel_file.write('  + Username: ' + username + '\n')
        feel_file.write(err_bytes)
        feel_file.write('\n\nEnd error at %s\n\n' % now_str)

    return


def get_frontend_error_log(config, request_dict):
    # TODO
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))
    feel_path = config.get('feel_log_path', None)
    if not feel_path:
        return ['(no front-end error log configured)']

    return _get_tail_from_path(feel_path, count=count)


META_ROUTES = get_meta_routes()
