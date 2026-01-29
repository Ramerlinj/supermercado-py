from flask import Flask, render_template
from livereload import Server

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('main/index.html')


@app.route('/products')
def menu():
    return render_template('main/menu.html')

if __name__ == '__main__':
    server = Server(app.wsgi_app)
    server.watch('src/templates/')
    server.watch('src/static/')
    server.serve(host='localhost', port=5000)
    