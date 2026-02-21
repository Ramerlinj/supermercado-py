import os
import json
import bcrypt
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session
from middleware.admin import build_admin_required, get_admin_role_id, is_admin as is_admin_user
from dotenv import load_dotenv
from decimal import Decimal
# from livereload import Server

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')


def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL is not set')
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def _normalize_cantity(description):
    if not description:
        return ''
    prefix = 'Cantidad:'
    if description.startswith(prefix):
        return description[len(prefix):].strip()
    return description


def load_products():
        with get_db_connection() as conn:
                with conn.cursor() as cur:
                        cur.execute(
                                """
                                select
                                    p.id,
                                    p.name,
                                    p.description,
                                    p.price,
                                    p.image_url,
                                    p.is_on_offer,
                                    p.offer_price,
                                    c.name as category
                                from public.products p
                                left join public.product_categories pc
                                    on pc.product_id = p.id
                                left join public.categories c
                                    on c.id = pc.category_id
                                where p.is_active = true
                                order by p.created_at desc, p.name asc
                                """
                        )
                        rows = cur.fetchall()

        products = []
        for row in rows:
                products.append({
                        'id': str(row.get('id')),
                        'name': row.get('name'),
                        'category': row.get('category') or 'Sin categoria',
                        'price': float(row.get('price') or 0),
                        'cantity': _normalize_cantity(row.get('description')),
                        'image_url': row.get('image_url'),
                        'is_on_offer': bool(row.get('is_on_offer')),
                        'offer_price': float(row.get('offer_price') or 0),
                })
        return {'Products': products}


def _hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _check_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def _is_valid_email(email):
    return bool(email) and '@' in email and '.' in email


def _slugify(value):
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9\s-]', '', value)
    value = re.sub(r'\s+', '-', value)
    return value or 'producto'


admin_required = build_admin_required(get_db_connection)


def _get_cart():
    cart = session.get('cart')
    if not isinstance(cart, dict):
        cart = {}
    return cart


def _save_cart(cart):
    session['cart'] = cart


def _fetch_products_by_ids(product_ids):
    if not product_ids:
        return []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  p.id,
                  p.name,
                  p.price,
                  p.image_url,
                  p.is_on_offer,
                  p.offer_price
                from public.products p
                where p.id = any(%s::uuid[])
                """,
                (product_ids,),
            )
            return cur.fetchall()


def _build_cart_snapshot(cart):
    product_ids = list(cart.keys())
    rows = _fetch_products_by_ids(product_ids)
    items = []
    subtotal = Decimal('0')

    for row in rows:
        product_id = str(row.get('id'))
        qty = int(cart.get(product_id, 0))
        if qty <= 0:
            continue
        is_on_offer = bool(row.get('is_on_offer'))
        offer_price = Decimal(str(row.get('offer_price') or 0))
        price = Decimal(str(row.get('price') or 0))
        unit_price = offer_price if is_on_offer and offer_price > 0 else price
        line_total = unit_price * qty
        subtotal += line_total
        items.append({
            'id': product_id,
            'name': row.get('name'),
            'image_url': row.get('image_url'),
            'quantity': qty,
            'unit_price': float(unit_price),
            'line_total': float(line_total),
        })

    return items, float(subtotal)


def _cart_payload(cart):
    items, subtotal = _build_cart_snapshot(cart)
    item_map = {item['id']: item for item in items}
    cart_count = sum(int(qty) for qty in cart.values()) if cart else 0
    return items, subtotal, item_map, cart_count


@app.context_processor
def inject_globals():
    cart = _get_cart()
    cart_count = sum(int(qty) for qty in cart.values()) if cart else 0
    is_admin = False
    user_id = session.get('user_id')
    if user_id:
        is_admin = is_admin_user(user_id, get_db_connection)
        session['is_admin'] = is_admin
    return {
        'cart_count': cart_count,
        'user_name': session.get('user_name'),
        'is_admin': is_admin,
    }

@app.route('/')
def index():
    data_del_json = load_products()
    return render_template('main/index.html', products=data_del_json)


@app.route('/products')
def menu():
    data_del_json = load_products()
    categories = sorted({
        product.get('category')
        for product in data_del_json.get('Products', [])
        if product.get('category')
    })
    return render_template(
        'menu/index.html',
        products=data_del_json,
        categories=categories,
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'GET':
        next_url = request.args.get('next', '')
        return render_template('auth/login.html', next_url=next_url)

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')
    password_confirm = request.form.get('password_confirm', '')
    password_confirm = request.form.get('password_confirm', '')
    password_confirm = request.form.get('password_confirm', '')
    next_url = request.form.get('next', '').strip()
    if not email or not password:
        return render_template(
            'auth/login.html',
            error='Completa tus credenciales.',
            email=email,
            next_url=next_url,
        )

    if not _is_valid_email(email):
        return render_template(
            'auth/login.html',
            error='Email invalido.',
            email=email,
            next_url=next_url,
        )

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, password_hash, full_name
                from public.users
                where email = %s and is_active = true
                """,
                (email,),
            )
            user = cur.fetchone()

    if not user or not _check_password(password, user['password_hash']):
        return render_template(
            'auth/login.html',
            error='Credenciales invalidas.',
            email=email,
            next_url=next_url,
        )

    session['user_id'] = str(user['id'])
    session['user_name'] = user.get('full_name')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'GET':
        return render_template('auth/register.html')

    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not email or not password or not first_name or not last_name:
        return render_template(
            'auth/register.html',
            error='Completa los datos requeridos.',
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    if not _is_valid_email(email):
        return render_template(
            'auth/register.html',
            error='Email invalido.',
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    if len(password) < 6:
        return render_template(
            'auth/register.html',
            error='La contrasena debe tener al menos 6 caracteres.',
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    full_name = f"{first_name} {last_name}".strip()
    password_hash = _hash_password(password)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('select 1 from public.users where email = %s', (email,))
            if cur.fetchone():
                return render_template(
                    'auth/register.html',
                    error='El email ya existe.',
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )

            cur.execute(
                """
                insert into public.users (email, password_hash, full_name)
                values (%s, %s, %s)
                returning id
                """,
                (email, password_hash, full_name),
            )
            user_id = cur.fetchone()['id']
            conn.commit()

    session['user_id'] = str(user_id)
    session['user_name'] = full_name or email
    return redirect(url_for('index'))


@app.route('/cart')
def cart():
    cart_data = _get_cart()
    items, subtotal = _build_cart_snapshot(cart_data)
    return render_template('cart/index.html', items=items, subtotal=subtotal)


@app.route('/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id') or request.form.get('product_id')
    quantity = data.get('quantity') or request.form.get('quantity') or 1

    if not product_id:
        return {'status': 'error', 'message': 'Missing product_id'}, 400

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    if quantity <= 0:
        quantity = 1

    cart_data = _get_cart()
    cart_data[product_id] = int(cart_data.get(product_id, 0)) + quantity
    _save_cart(cart_data)

    if request.is_json:
        items, subtotal, item_map, cart_count = _cart_payload(cart_data)
        return {
            'status': 'ok',
            'cart_count': cart_count,
            'subtotal': subtotal,
            'items': item_map,
        }

    return redirect(request.referrer or url_for('cart'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id') or request.form.get('product_id')
    quantity = data.get('quantity') or request.form.get('quantity')

    if not product_id:
        return {'status': 'error', 'message': 'Missing product_id'}, 400

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return {'status': 'error', 'message': 'Invalid quantity'}, 400

    cart_data = _get_cart()
    if quantity <= 0:
        cart_data.pop(product_id, None)
    else:
        cart_data[product_id] = quantity
    _save_cart(cart_data)

    if request.is_json:
        items, subtotal, item_map, cart_count = _cart_payload(cart_data)
        return {
            'status': 'ok',
            'cart_count': cart_count,
            'subtotal': subtotal,
            'items': item_map,
        }

    return redirect(url_for('cart'))


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id') or request.form.get('product_id')

    if not product_id:
        return {'status': 'error', 'message': 'Missing product_id'}, 400

    cart_data = _get_cart()
    cart_data.pop(product_id, None)
    _save_cart(cart_data)

    if request.is_json:
        items, subtotal, item_map, cart_count = _cart_payload(cart_data)
        return {
            'status': 'ok',
            'cart_count': cart_count,
            'subtotal': subtotal,
            'items': item_map,
        }

    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
def checkout():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    cart_data = _get_cart()
    items, subtotal = _build_cart_snapshot(cart_data)
    if not items:
        return redirect(url_for('cart'))

    tax = 0
    total = subtotal + tax

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.orders (user_id, status, subtotal, tax, total, currency)
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (session['user_id'], 'pending', subtotal, tax, total, 'USD'),
            )
            order_id = cur.fetchone()['id']

            for item in items:
                cur.execute(
                    """
                    insert into public.order_items
                    (order_id, product_id, quantity, unit_price, line_total)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        item['id'],
                        item['quantity'],
                        item['unit_price'],
                        item['line_total'],
                    ),
                )

            conn.commit()

    session.pop('cart', None)
    return redirect(url_for('checkout_success', order_id=order_id))


@app.route('/checkout/success')
def checkout_success():
    order_id = request.args.get('order_id')
    return render_template('cart/success.html', order_id=order_id)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_home():
    return render_template('admin/index.html')


@app.route('/admin/products')
@admin_required
def admin_products():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  p.id,
                  p.name,
                  p.price,
                  p.is_active,
                  p.is_on_offer,
                  p.offer_price,
                  c.name as category
                from public.products p
                left join public.product_categories pc on pc.product_id = p.id
                left join public.categories c on c.id = pc.category_id
                order by p.created_at desc
                """
            )
            products = cur.fetchall()

    return render_template('admin/products_list.html', products=products)


@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_product_new():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('select id, name from public.categories order by name asc')
            categories = cur.fetchall()

    if request.method == 'GET':
        return render_template('admin/product_form.html', categories=categories)

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()
    price = request.form.get('price', '0').strip()
    offer_price = request.form.get('offer_price', '0').strip()
    category_id = request.form.get('category_id')
    is_active = request.form.get('is_active') == 'on'
    is_on_offer = request.form.get('is_on_offer') == 'on'

    try:
        price_value = float(price)
        offer_value = float(offer_price or 0)
    except ValueError:
        return render_template(
            'admin/product_form.html',
            categories=categories,
            error='Precio invalido.',
        )

    if not name:
        return render_template(
            'admin/product_form.html',
            categories=categories,
            error='Nombre requerido.',
        )

    slug = _slugify(name)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.products
                (name, slug, description, price, image_url, is_on_offer, offer_price, is_active)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (name, slug, description, price_value, image_url, is_on_offer, offer_value, is_active),
            )
            product_id = cur.fetchone()['id']

            if category_id:
                cur.execute(
                    "insert into public.product_categories (product_id, category_id) values (%s, %s)",
                    (product_id, category_id),
                )
            conn.commit()

    return redirect(url_for('admin_products'))


@app.route('/admin/products/<product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select p.*, pc.category_id
                from public.products p
                left join public.product_categories pc on pc.product_id = p.id
                where p.id = %s
                """,
                (product_id,),
            )
            product = cur.fetchone()
            cur.execute('select id, name from public.categories order by name asc')
            categories = cur.fetchall()

    if not product:
        return render_template('admin/forbidden.html'), 404

    if request.method == 'GET':
        return render_template('admin/product_form.html', product=product, categories=categories)

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()
    price = request.form.get('price', '0').strip()
    offer_price = request.form.get('offer_price', '0').strip()
    category_id = request.form.get('category_id')
    is_active = request.form.get('is_active') == 'on'
    is_on_offer = request.form.get('is_on_offer') == 'on'

    try:
        price_value = float(price)
        offer_value = float(offer_price or 0)
    except ValueError:
        return render_template(
            'admin/product_form.html',
            product=product,
            categories=categories,
            error='Precio invalido.',
        )

    if not name:
        return render_template(
            'admin/product_form.html',
            product=product,
            categories=categories,
            error='Nombre requerido.',
        )

    slug = _slugify(name)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.products
                set name = %s,
                    slug = %s,
                    description = %s,
                    price = %s,
                    image_url = %s,
                    is_on_offer = %s,
                    offer_price = %s,
                    is_active = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    name,
                    slug,
                    description,
                    price_value,
                    image_url,
                    is_on_offer,
                    offer_value,
                    is_active,
                    product_id,
                ),
            )
            cur.execute('delete from public.product_categories where product_id = %s', (product_id,))
            if category_id:
                cur.execute(
                    "insert into public.product_categories (product_id, category_id) values (%s, %s)",
                    (product_id, category_id),
                )
            conn.commit()

    return redirect(url_for('admin_products'))


@app.route('/admin/products/<product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('delete from public.products where id = %s', (product_id,))
            conn.commit()
    return redirect(url_for('admin_products'))


@app.route('/admin/users')
@admin_required
def admin_users():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  u.id,
                  u.email,
                  u.full_name,
                  u.is_active,
                  exists (
                    select 1
                    from public.user_roles ur
                    join public.roles r on r.id = ur.role_id
                    where ur.user_id = u.id and r.name = 'admin'
                  ) as is_admin
                from public.users u
                order by u.created_at desc
                """
            )
            users = cur.fetchall()
    return render_template('admin/users_list.html', users=users)


@app.route('/admin/users/new', methods=['GET', 'POST'])
@admin_required
def admin_user_new():
    if request.method == 'GET':
        return render_template('admin/user_form.html')

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    is_active = request.form.get('is_active') == 'on'
    is_admin_flag = request.form.get('is_admin') == 'on'

    if not email or not password:
        return render_template('admin/user_form.html', error='Email y contrasena requeridos.')

    if not _is_valid_email(email):
        return render_template('admin/user_form.html', error='Email invalido.')

    if len(password) < 6:
        return render_template('admin/user_form.html', error='La contrasena debe tener al menos 6 caracteres.')

    password_hash = _hash_password(password)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('select 1 from public.users where email = %s', (email,))
            if cur.fetchone():
                return render_template('admin/user_form.html', error='El email ya existe.')

            cur.execute(
                """
                insert into public.users (email, password_hash, full_name, is_active)
                values (%s, %s, %s, %s)
                returning id
                """,
                (email, password_hash, full_name, is_active),
            )
            user_id = cur.fetchone()['id']

            if is_admin_flag:
                role_id = get_admin_role_id(conn)
                cur.execute(
                    "insert into public.user_roles (user_id, role_id) values (%s, %s)",
                    (user_id, role_id),
                )
            conn.commit()

    return redirect(url_for('admin_users'))


@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_user_edit(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  u.id,
                  u.email,
                  u.full_name,
                  u.is_active,
                  exists (
                    select 1
                    from public.user_roles ur
                    join public.roles r on r.id = ur.role_id
                    where ur.user_id = u.id and r.name = 'admin'
                  ) as is_admin
                from public.users u
                where u.id = %s
                """,
                (user_id,),
            )
            user = cur.fetchone()

    if not user:
        return render_template('admin/forbidden.html'), 404

    if request.method == 'GET':
        return render_template('admin/user_form.html', user=user)

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    is_active = request.form.get('is_active') == 'on'
    is_admin_flag = request.form.get('is_admin') == 'on'

    if not email:
        return render_template('admin/user_form.html', user=user, error='Email requerido.')

    if not _is_valid_email(email):
        return render_template('admin/user_form.html', user=user, error='Email invalido.')

    if password and len(password) < 6:
        return render_template(
            'admin/user_form.html',
            user=user,
            error='La contrasena debe tener al menos 6 caracteres.',
        )

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.users
                set email = %s,
                    full_name = %s,
                    is_active = %s,
                    updated_at = now()
                where id = %s
                """,
                (email, full_name, is_active, user_id),
            )

            if password:
                password_hash = _hash_password(password)
                cur.execute(
                    "update public.users set password_hash = %s where id = %s",
                    (password_hash, user_id),
                )

            role_id = get_admin_role_id(conn)
            cur.execute(
                "select 1 from public.user_roles where user_id = %s and role_id = %s",
                (user_id, role_id),
            )
            has_admin = cur.fetchone() is not None
            if is_admin_flag and not has_admin:
                cur.execute(
                    "insert into public.user_roles (user_id, role_id) values (%s, %s)",
                    (user_id, role_id),
                )
            if not is_admin_flag and has_admin:
                cur.execute(
                    "delete from public.user_roles where user_id = %s and role_id = %s",
                    (user_id, role_id),
                )
            conn.commit()

    if session.get('user_id') == user_id:
        session['is_admin'] = is_admin_flag

    return redirect(url_for('admin_users'))


@app.route('/admin/users/<user_id>/delete', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('delete from public.users where id = %s', (user_id,))
            conn.commit()
    return redirect(url_for('admin_users'))


@app.route('/health/db')
def health_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('select 1 as ok')
                row = cur.fetchone()
    except Exception as exc:
        return {
            'status': 'error',
            'message': str(exc),
        }, 500

    return {
        'status': 'ok',
        'result': row.get('ok') if row else None,
    }

if __name__ == '__main__':
    app.run(debug=True)
    