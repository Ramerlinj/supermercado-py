from functools import wraps
from flask import redirect, url_for, request, render_template, session


def get_admin_role_id(conn):
    with conn.cursor() as cur:
        cur.execute("select id from public.roles where name = 'admin'")
        row = cur.fetchone()
        if row:
            return row['id']

        cur.execute(
            "insert into public.roles (name, description) values ('admin', 'Admin role') returning id"
        )
        return cur.fetchone()['id']


def is_admin(user_id, get_db_connection):
    if not user_id:
        return False
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select 1
                from public.user_roles ur
                join public.roles r on r.id = ur.role_id
                where ur.user_id = %s and r.name = 'admin'
                """,
                (user_id,),
            )
            return cur.fetchone() is not None


def build_admin_required(get_db_connection):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return redirect(url_for('login', next=request.path))
            if not is_admin(user_id, get_db_connection):
                return render_template('admin/forbidden.html'), 403
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
