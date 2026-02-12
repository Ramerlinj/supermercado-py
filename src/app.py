import os
import json
from flask import Flask, render_template
# from livereload import Server

app = Flask(__name__)

@app.route('/')
def index():
    
    json_url = os.path.join(app.root_path, 'static', 'data', 'products.json')
    
    
    data_del_json = {}
    with open(json_url, 'r', encoding='utf-8') as f:
        data_del_json = json.load(f)
    return render_template('main/index.html', products=data_del_json)


@app.route('/products')
def menu():
    return render_template('main/menu.html')

if __name__ == '__main__':
    app.run(debug=True)
    