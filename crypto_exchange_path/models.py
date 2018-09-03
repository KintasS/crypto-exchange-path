from crypto_exchange_path import db


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    topic = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(50))
    detail = db.Column(db.String(200))

    def __repr__(self):
        date = self.datetime.strftime("%Y%m%d")
        return ("Feedback({} [{}]: {})"
                .format(date, self.topic, self.subject))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_time = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    not_before_time = db.Column(db.DateTime)
    start_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer)
    return_info = db.Column(db.String(100))

    def __repr__(self):
        start_time = None
        if self.not_before_time:
            start_time = self.not_before_time.strftime("%Y%m%d")
        if self.user_id and start_time:
            return ("Task({}[user:{}]: Status:{}, Start Time:{})"
                    .format(self.name, self.user_id, self.status, start_time))
        elif (self.user_id is None) and (start_time is None):
            return ("Task({}: Status:{})"
                    .format(self.name, self.status))
        elif self.user_id is None:
            return ("Task({}: Status:{}, Start Time:{})"
                    .format(self.name, self.status, start_time))
        elif start_time is None:
            return ("Task({}[user:{}]: Status:{})"
                    .format(self.name, self.user_id, self.status))


class Price(db.Model):
    coin = db.Column(db.String(10), primary_key=True, nullable=False)
    base_coin = db.Column(db.String(10), primary_key=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return ("Price({}/{} ({}): {})"
                .format(self.coin, self.currency, self.price))


class Coin(db.Model):
    id = db.Column(db.String(10), primary_key=True, nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    long_name = db.Column(db.String(50), nullable=False)
    price_id = db.Column(db.String(10), nullable=False)
    ranking = db.Column(db.Float)
    image_url = db.Column(db.String(100))
    local_fn = db.Column(db.String(100))
    type = db.Column(db.String(30))
    status = db.Column(db.String(10))

    def __repr__(self):
        return ("Coin({} [{}]: symbol={} price_id={} type={} status={})"
                .format(self.id,
                        self.long_name,
                        self.symbol,
                        self.price_id,
                        self.type,
                        self.status))


class Exchange(db.Model):
    id = db.Column(db.String(30), primary_key=True, nullable=False)
    name = db.Column(db.String(30), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    img_fn = db.Column(db.String(50))
    site_url = db.Column(db.String(100))
    affiliate = db.Column(db.String(10), nullable=False)
    language = db.Column(db.String(50))
    trade_pairs = db.relationship('TradePair', backref='exchange_trade',
                                  lazy=True)
    fees = db.relationship('Fee', backref='exchange_fee', lazy=True)

    def __repr__(self):
        return ("Exchange({} [{}])".format(self.name, self.type))


class Fee(db.Model):
    exchange = db.Column(db.String(30), db.ForeignKey('exchange.id'),
                         primary_key=True, nullable=False)
    action = db.Column(db.String(30), primary_key=True, nullable=False)
    scope = db.Column(db.String(30), primary_key=True, nullable=False)
    amount = db.Column(db.Float)
    min_amount = db.Column(db.Float)
    fee_coin = db.Column(db.String(10))
    type = db.Column(db.String(10))

    def __repr__(self):
        return ("Fee({}-{}-{}: {})".format(self.exchange, self.action,
                                           self.scope, self.amount))


class TradePair(db.Model):
    exchange = db.Column(db.String(30), db.ForeignKey('exchange.id'),
                         primary_key=True, nullable=False)
    coin = db.Column(db.String(10), db.ForeignKey('coin.id'),
                     primary_key=True, nullable=False)
    base_coin = db.Column(db.String(10), db.ForeignKey('coin.id'),
                          primary_key=True, nullable=False)
    volume = db.Column(db.Float)

    def __repr__(self):
        return ("TradePair({} [{}/{}]: volume={})".format(self.exchange,
                                                          self.coin,
                                                          self.base_coin,
                                                          self.volume))


class QueryRegister(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    orig_amt = db.Column(db.Float)
    orig_coin = db.Column(db.String(10))
    orig_loc = db.Column(db.String(30))
    dest_coin = db.Column(db.String(10))
    dest_loc = db.Column(db.String(30))
    currency = db.Column(db.String(10))
    connection_type = db.Column(db.Integer)
    exchanges = db.Column(db.String(400))
    results = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)

    def __repr__(self):
        return ("QueryRegister([{}] id={}, results={})".format(self.session_id,
                                                               self.id,
                                                               self.results))
