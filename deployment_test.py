"""
Simple deployment test to identify login issues
"""
from flask import Flask, session, request, render_template_string
import os

# Create a minimal test app
test_app = Flask(__name__)
test_app.secret_key = os.environ.get("SESSION_SECRET", "test-secret")

# Simple test template
TEST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Login Test</title></head>
<body>
    <h1>Deployment Login Test</h1>
    
    {% if session.get('test_logged_in') %}
        <div style="color: green;">
            <h2>✓ Login Working!</h2>
            <p>Session: {{ session }}</p>
            <p><a href="/test-logout">Logout</a></p>
        </div>
    {% else %}
        <form method="POST" action="/test-login">
            <h2>Test Login</h2>
            <p>Username: <input type="text" name="username" value="admin"></p>
            <p>Password: <input type="password" name="password" value="admin"></p>
            <p><input type="submit" value="Login"></p>
        </form>
        {% if error %}
            <p style="color: red;">{{ error }}</p>
        {% endif %}
    {% endif %}
    
    <hr>
    <h3>Debug Info:</h3>
    <ul>
        <li>Environment: {{ env }}</li>
        <li>Session Secret Set: {{ secret_set }}</li>
        <li>Current Session: {{ session }}</li>
    </ul>
</body>
</html>
"""

@test_app.route('/')
def test_index():
    return render_template_string(TEST_TEMPLATE, 
                                  session=dict(session),
                                  env=os.environ.get('ENVIRONMENT', 'unknown'),
                                  secret_set=bool(os.environ.get('SESSION_SECRET')),
                                  error=None)

@test_app.route('/test-login', methods=['POST'])
def test_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'admin' and password == 'admin':
        session.clear()
        session.permanent = True
        session['test_logged_in'] = True
        session['test_user'] = 'admin'
        return render_template_string(TEST_TEMPLATE,
                                      session=dict(session),
                                      env=os.environ.get('ENVIRONMENT', 'unknown'),
                                      secret_set=bool(os.environ.get('SESSION_SECRET')),
                                      error=None)
    else:
        return render_template_string(TEST_TEMPLATE,
                                      session=dict(session),
                                      env=os.environ.get('ENVIRONMENT', 'unknown'),
                                      secret_set=bool(os.environ.get('SESSION_SECRET')),
                                      error="Invalid credentials")

@test_app.route('/test-logout')
def test_logout():
    session.clear()
    return render_template_string(TEST_TEMPLATE,
                                  session=dict(session),
                                  env=os.environ.get('ENVIRONMENT', 'unknown'),
                                  secret_set=bool(os.environ.get('SESSION_SECRET')),
                                  error=None)

if __name__ == '__main__':
    test_app.run(host='0.0.0.0', port=5001, debug=True)
