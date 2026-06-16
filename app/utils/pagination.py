from flask import request


def paginate(query, per_page=20):
    page = request.args.get("page", 1, type=int)
    return query.paginate(page=page, per_page=per_page, error_out=False)
