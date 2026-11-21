from flask import Flask, render_template

app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")


@app.after_request
def security_headers(response):
    # Strict policy: everything same-origin. Reviewed by security 2026-09.
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index():
    return render_template("index.html")
