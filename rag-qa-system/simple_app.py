from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>Flask 서버가 정상적으로 실행 중입니다!</h1>'

@app.route('/deotisrag')
def deotis_index():
    try:
        return render_template('modern_index.html')
    except Exception as e:
        return f'<h1>Template Error: {str(e)}</h1>'

@app.route('/test')
def test():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .success { color: green; font-size: 20px; }
        </style>
    </head>
    <body>
        <div class="success">
            ✅ Flask 서버 테스트 성공!
        </div>
        <p>다음 URL들을 확인해보세요:</p>
        <ul>
            <li><a href="/">메인 페이지</a></li>
            <li><a href="/deotisrag">Modern RAG UI</a></li>
        </ul>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')