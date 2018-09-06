from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from crypto_exchange_path.config import AppConfig
from flask_mail import Mail

app = Flask(__name__)
app.config.from_object(AppConfig)
db = SQLAlchemy(app)
mail = Mail(app)

from crypto_exchange_path import routes
