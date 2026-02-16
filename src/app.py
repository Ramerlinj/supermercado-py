import os
import json
from flask import Flask, render_template
# from livereload import Server

app = Flask(__name__)


def load_products():
    json_url = os.path.join(app.root_path, 'static', 'data', 'products.json')
    with open(json_url, 'r', encoding='utf-8') as f:
        return json.load(f)

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


@app.route('/login')
def login():
    return render_template('auth/login.html')


@app.route('/register')
def register():
    return render_template('auth/register.html')

if __name__ == '__main__':
    app.run(debug=True)
    