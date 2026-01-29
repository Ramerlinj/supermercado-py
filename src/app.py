from flask import Flask, render_template


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('main/index.html')


@app.route('/products')
def menu():
    return render_template('main/menu.html')

if __name__ == '__main__':
    app.run(debug=True)
    