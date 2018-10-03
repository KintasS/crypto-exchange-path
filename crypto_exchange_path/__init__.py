from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_admin import Admin
from flask_security import Security, SQLAlchemyUserDatastore
from flask_admin import helpers as admin_helpers
from crypto_exchange_path.config import AppConfig
from crypto_exchange_path.admin_view import (ExchangeView, FeeView, CoinView,
                                             TradePairView, PriceView,
                                             FeedbackView, QueryRegisterView,
                                             UserView, RoleView)
from flask_security.utils import encrypt_password

app = Flask(__name__)
app.config.from_object(AppConfig)
db = SQLAlchemy(app)
mail = Mail(app)

# Create Flask Admin
admin = Admin(app, name='CFS Admin',
              url='/cfs_admin',
              base_template='my_master.html',
              template_mode='bootstrap3')

from crypto_exchange_path import routes
from crypto_exchange_path.models import (User, Role, Exchange, Fee, Coin,
                                         TradePair, Price, Feedback,
                                         QueryRegister)

# Create Admin views
admin.add_view(ExchangeView(Exchange, db.session, category="Site Data"))
admin.add_view(FeeView(Fee, db.session, category="Site Data"))
admin.add_view(CoinView(Coin, db.session, category="Site Data"))
admin.add_view(TradePairView(TradePair, db.session, category="Site Data"))
admin.add_view(PriceView(Price, db.session, category="Site Data"))
admin.add_view(UserView(User, db.session, category="User Config"))
admin.add_view(RoleView(Role, db.session, category="User Config"))
admin.add_view(FeedbackView(Feedback, db.session))
admin.add_view(QueryRegisterView(QueryRegister, db.session))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


@security.context_processor
def security_context_processor():
    """
    Define a context processor for merging flask-admin's template context into
    the flask-security views.
    """
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
