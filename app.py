from flask import Flask, request, redirect, session, url_for, render_template, flash
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Настройки OAuth (замените на свои!)
CLIENT_ID = "ваш_client_id"
CLIENT_SECRET = "ваш_client_secret"
REDIRECT_URI = "https://ваш-ngrok-адрес.ngrok.io/auth/callback"  # или ваш домен

MYTEAM_TOKEN_URL = "https://auth.mail.ru/oauth/token"
MYTEAM_USERINFO_URL = "https://auth.mail.ru/oauth/userinfo"

# Защита маршрутов
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def index():
    # Временно: подставляем тестового пользователя (для локального теста)
    if os.getenv('FLASK_ENV') == 'development':
        session['user'] = {
            'id': 'test_123',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': 'ivan@example.edu.ru'
        }
        return redirect(url_for('main'))

    # В продакшене — реальный OAuth
    auth_url = (
        "https://auth.mail.ru/oauth/auth?"
        "response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        "scope=basic"
    )
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    if not code:
        return "Ошибка авторизации", 400

    token_resp = requests.post(MYTEAM_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI
    })

    if token_resp.status_code != 200:
        return "Не удалось получить токен", 400

    access_token = token_resp.json()['access_token']
    user_resp = requests.get(MYTEAM_USERINFO_URL, headers={'Authorization': f'Bearer {access_token}'})
    session['user'] = user_resp.json()
    return redirect(url_for('main'))

@app.route('/main')
@login_required
def main():
    user = session['user']
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    return render_template('main.html', user_name=user_name, user_id=user['id'])

# === Страницы форм ===

@app.route('/submit-request', methods=['GET', 'POST'])
@login_required
def submit_request():
    if request.method == 'POST':
        # Здесь отправка в ваш API / БД
        subject = request.form['subject']
        flash(f'✅ Заявка "{subject}" отправлена! Номер: REQ-{session["user"]["id"][:8]}', 'success')
        return redirect(url_for('main'))
    return render_template('submit_request.html')

@app.route('/order-certificate', methods=['GET', 'POST'])
@login_required
def order_certificate():
    if request.method == 'POST':
        cert_type = dict(request.form).get('cert_type')
        types = {
            'enrollment': 'об обучении',
            'military': 'для военкомата',
            'visa': 'для визы',
            'academic': 'об успеваемости'
        }
        name = types.get(cert_type, 'справка')
        flash(f'✅ Заказана {name}. Готова будет в течение 2 рабочих дней.', 'success')
        return redirect(url_for('main'))
    return render_template('order_certificate.html')

@app.route('/book-ecp', methods=['GET', 'POST'])
@login_required
def book_ecp():
    today = datetime.now().date()
    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        flash(f'✅ Вы записаны на {date} в {time} для оформления ЭЦП.', 'success')
        return redirect(url_for('main'))

    min_date = today.isoformat()
    max_date = (today + timedelta(days=14)).isoformat()
    return render_template('book_ecp.html', min_date=min_date, max_date=max_date)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, ssl_context='adhoc')  # для ngrok — OK; для продакшена — нет!
