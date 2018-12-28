from crypto_exchange_path.models import Coin, TradePair, Fee, Price, Exchange
from crypto_exchange_path import db
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils import is_number, float_to_str


def get_active_coins(type=None, price_id=False):
    """Returns the complete list of active coins available in 'Coin' table.
    By default, it returns its symbols, unless 'price_id' is set to True.
    If type is given, only those coins are retrieved (Cryptos o Fiat)
    """
    if type:
        coin_in_db = Coin.query.filter_by(type=type, status="Active").all()
    else:
        coin_in_db = Coin.query.filter_by(status="Active").all()
    coin_list = []
    if price_id:
        for coin in coin_in_db:
            coin_list.append(coin.price_id)
    else:
        for coin in coin_in_db:
            coin_list.append(coin.id)
    return coin_list


def get_coins(pos_limit=9999, type=None):
    """Returns the active coins available in 'Coin' table.
    If type is given, only those coins are retrieved (Cryptos o Fiat)
    If a position limit is given, only coins ranked below that figure are
    retrieved.
    """
    if type:
        # coin_in_db = Coin.query.filter_by(type=type, status="Active").all()
        coin_in_db = db.session.query(Coin)\
            .filter((Coin.type == type) &
                    (Coin.ranking <= pos_limit) &
                    (Coin.status == "Active")).all()
    else:
        # coin_in_db = Coin.query.filter_by(status="Active").all()
        coin_in_db = db.session.query(Coin)\
            .filter((Coin.ranking <= pos_limit) &
                    (Coin.status == "Active")).all()
    coin_in_db = sorted(coin_in_db, key=lambda x: x.ranking)
    return coin_in_db


def get_coin(id):
    """Returns a Coin object given its symbol.
    """
    coin = Coin.query.filter_by(id=id.upper()).first()
    return coin


def get_coin_by_longname(longname):
    """Returns a Coin object given its longname.
    """
    coin = Coin.query.filter_by(long_name=longname).first()
    return coin


def get_coin_by_urlname(url_name):
    """Returns a Coin object given its url name.
    """
    coin = Coin.query.filter_by(url_name=url_name).first()
    return coin


def get_coin_by_price_id(price_id):
    """Returns a Coin object given its 'price_id'.
    """
    coin = Coin.query.filter_by(price_id=price_id).first()
    return coin


def get_exchange(id):
    """Returns the exchange object with the given 'id'.
    """
    exchange = Exchange.query.filter_by(id=id).first()
    if exchange:
        return exchange
    else:
        return None


def get_exch_by_name(name):
    """Returns the exchange object with the given 'name'.
    """
    exchange = Exchange.query.filter_by(name=name).first()
    if exchange:
        return exchange
    else:
        return None


def get_exchanges(types=[]):
    """Returns the list of exchanges available in 'Exchange' table.
    """
    exchanges = []
    if types:
        for type in types:
            exchanges += Exchange.query.filter_by(type=type).all()
    else:
        exchanges = Exchange.query.all()
    return exchanges


def get_exchange_choices(types=[]):
    """Returns the list of exchanges available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    exchanges = []
    for type in types:
        exchanges += Exchange.query.filter_by(type=type).all()
    choices = []
    for exch in exchanges:
        choices.append((exch.id, exch.name))
    return choices


def get_feedback_topics():
    """Gets the feedback topics from the configuration file and builds
    a list of tuples.
    """
    topics = Params.FEEDBACK_TOPICS
    choices = [('(Select a topic)', '(Select a topic)')]
    for topic in topics:
        choices.append((topic, topic))
    return choices


def get_currency_choices():
    """Returns the list of currencies available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    currencies = get_active_coins('Fiat')
    choices = []
    for currency in currencies:
        choices.append((currency, currency))
    return choices


def get_exch_by_pair(coin, base_coin, logger):
    """Gets the exchanges that trade a given pair,
    together with its Volume_24h.
    Results are sorted by Volume_24h.
    """
    exchs = db.session.query(TradePair)\
                      .filter(((TradePair.coin == coin) &
                               (TradePair.base_coin == base_coin)) |
                              ((TradePair.coin == base_coin) &
                               (TradePair.base_coin == coin)))\
                      .order_by(TradePair.volume.desc()).all()
    logger.debug("get_exch_by_pair: Returned '{}'exchanges that "
                 "trade '{}-{}'".format(len(exchs), coin, base_coin))
    if exchs:
        return set([item.exchange for item in exchs])
    return set()


def get_exch_by_coin(coin):
    """Gets the exchanges that allows deposit or withdrawal of 'coin'.
    It is assumed that, in order for an exchange to allow the deposit of a
    coin, it must allow the withdrawal of that coin (which should be the case).
    """
    exchs = db.session.query(Fee.exchange)\
                      .filter((Fee.action == 'Withdrawal') &
                              (Fee.scope == coin))\
                      .distinct(Fee.exchange).all()
    if exchs:
        return set([item[0] for item in exchs])
    return set()


def get_trading_fees_by_exch(exchange):
    """Gets all the trading fees for 'exchange'.
    Returns a list of dics: [{"order": x, "scope": y, "amount": z}]
    """
    return_list = list()
    fee_query = Fee.query.filter_by(exchange=exchange,
                                    action='Trade').all()
    for fee in fee_query:
        if fee.scope == '(Maker)':
            return_list.append({"order": 1,
                                "scope": 'Market Maker',
                                "amount": str(fee.amount) + '%'})
        elif fee.scope == '(Taker)':
            return_list.append({"order": 2,
                                "scope": 'Market Taker',
                                "amount": str(fee.amount) + '%'})
        elif fee.scope == '(BIX)':
            return_list.append({"order": 99,
                                "scope": 'If paying with BIX',
                                "amount": str(fee.amount) + '%'})
        elif fee.scope == '(BNB)':
            return_list.append({"order": 99,
                                "scope": 'Paying with BNB',
                                "amount": str(fee.amount) + '%'})
        else:
            return_list.append({"order": 9,
                                "scope": fee.scope,
                                "amount": str(fee.amount) + '%'})
    return_list = sorted(return_list, key=lambda x: x["order"])
    return return_list


def generate_fee_info(fee):
    """Aux function for 'dep_get_with_fees_by_exch(exchange)' and
    'get_coin_fees(coin_id)'.
    Generates the formated content to be provided.
    """
    # If Fee Amount == None, return n/a
    if not is_number(fee.amount):
        return {"amount": 'n/a', "comments": None}
    # Generate fee string
    fee_str = fee.amount
    # Calculate fee info
    if fee.type == 'Percentage':
        fee_str = "{}%".format(fee.amount)
    else:
        fee_str = "{} {}".format(float_to_str(fee.amount),
                                 fee.scope)
    if fee.min_amount and is_number(fee.min_amount):
        try:
            symbol = Params.CURRENCY_SYMBOLS[fee.scope]
        except Exception as e:
            symbol = " {}".format(fee.scope)
        if symbol == '$':
            fee_str = "{}\n(Min: {}{})".format(fee_str,
                                               symbol,
                                               fee.min_amount)
        else:
            fee_str = "{}\n(Min: {}{})".format(fee_str,
                                               fee.min_amount,
                                               symbol)
    # Generate comments
    comments = None
    if fee.type == 'Less1kUSD':
        comments = 'Fee applied on deposits of less than a 1,000 USD'\
            ' equivalent'
    return {"amount": fee_str, "comments": comments}


def get_dep_with_fees_by_exch(exchange):
    """Gets all the deposit and withdrawal fees for 'exchange'.
    Returns a list of dics: [{"coin": x,
                              "deposit": {"amount": y,
                                          "comments": z},
                              "withdrawal": {"amount": y,
                                             "comments": z}]
    """
    return_list = list()
    with_query = Fee.query.filter_by(exchange=exchange,
                                     action='Withdrawal').all()
    dep_query = Fee.query.filter_by(exchange=exchange,
                                    action='Deposit').all()
    for fee in with_query:
        coin_id = fee.scope
        coin = get_coin(coin_id)
        deposit_info = {"amount": '-', "comments": None}
        if coin:
            for item in dep_query:
                if item.scope == coin_id:
                    deposit_info = generate_fee_info(item)
                    break
            withdrawal_info = generate_fee_info(fee)
            return_list.append({"coin": coin,
                                "deposit": deposit_info,
                                "withdrawal": withdrawal_info})
    return_list = sorted(return_list, key=lambda x: x["coin"].ranking)
    return return_list


def get_coin_fees(coin_id):
    """Gets all the fees for the coin given as argument.
    Returns a list of dics: [{"exchange": x,
                              "deposit": {"amount": y,
                                          "comments": z},
                              "trade": {"amount": y,
                                        "comments": z},
                              "withdrawal": {"amount": y,
                                             "comments": z}]
    """
    return_list = list()
    with_query = Fee.query.filter_by(scope=coin_id,
                                     action='Withdrawal').all()
    dep_query = Fee.query.filter_by(scope=coin_id,
                                    action='Deposit').all()
    for fee in with_query:
        exch_id = fee.exchange
        exch = get_exchange(exch_id)
        deposit_info = {"amount": '-', "comments": None}
        if exch:
            for item in dep_query:
                if item.exchange == exch_id:
                    deposit_info = generate_fee_info(item)
                    break
            withdrawal_info = generate_fee_info(fee)
            # Get Trading fees
            maker_fee = Fee.query.filter_by(exchange=exch_id,
                                            action='Trade',
                                            scope='(Maker)').first()
            taker_fee = Fee.query.filter_by(exchange=exch_id,
                                            action='Trade',
                                            scope='(Taker)').first()
            if maker_fee.amount == taker_fee.amount:
                trade_fee = "{}%".format(maker_fee.amount)
            else:
                trade_fee = "{}% / {}%".format(maker_fee.amount,
                                               taker_fee.amount)
            trade_info = {"amount": trade_fee, "comments": None}
            # Generate return item
            return_list.append({"exchange": exch,
                                "deposit": deposit_info,
                                "trade": trade_info,
                                "withdrawal": withdrawal_info})
    return_list = sorted(return_list, key=lambda x: x["exchange"].name)
    return return_list


def calc_fee(action, exchange, coin, amt, logger):
    """Gets the deposit or withdrawal fee of 'exchange'/'coin'.
    Returns: [<fee_amt>, <fee_details>]
    """
    fee_query = Fee.query.filter_by(exchange=exchange,
                                    action=action,
                                    scope=coin).first()
    if fee_query and (fee_query.amount is not None):
        # If Type == 'Absolute', just return value
        if fee_query.type == 'Absolute':
            lit = "{} {} (fixed amount)".format(fee_query.amount,
                                                coin)
            return [fee_query.amount, lit]
        # If Type == 'Percentage', calc fee and check minimum quantity
        elif fee_query.type == 'Percentage':
            wd_fee = fee_query.amount / 100 * amt
            if fee_query.min_amount:
                lit = "{}% (minimum fee of {} {})"\
                    .format(fee_query.amount,
                            fee_query.min_amount,
                            coin)
                return [max(wd_fee, fee_query.min_amount), lit]
            else:
                lit = "{}%".format(fee_query.amount)
                return [wd_fee, lit]
        # If Type == 'Less1kUSD', get amount in USD and check if less than 1k
        elif fee_query.type == 'Less1kUSD':
            amount_usd = fx_exchange(coin, 'USD', amt, logger)
            if amount_usd < 1000:
                lit = "{} {} (fixed amount for deposits of less than $1000)"\
                    .format(fee_query.amount, coin)
                return [fee_query.amount, lit]
        # If Type == '1%+20', calc 1% and then add 20 units
        elif fee_query.type == '1%+20':
            wd_fee = round(0.01 * amt + 20, 2)
            lit = "1% + 20 {}".format(coin)
            return [wd_fee, lit]
    return [None, None]


def is_crypto(crypto):
    """Checks whether a coin is a crypto(True) or a fiat coin(False).
    """
    coin = Coin.query.filter_by(id=crypto).first()
    if coin and coin.type == 'Crypto':
        return True
    else:
        return False


def set_default_exch(coin_id):
    """ Set default exchange ('Wallet' or 'Bank') depending on the coin
    provided.
    """
    if is_crypto(coin_id):
        return 'Wallet'
    else:
        return 'Bank'


def fx_exchange(orig_coin, dest_coin, amount, logger):
    if amount is None:
        logger.warning("fx_exchange: FX could not be calculated for '{}"
                       "-{}' (amount=None)".format(orig_coin, dest_coin))
        return None
    # If 'orig_coin'='dest_coin', return 'amount' directly
    if orig_coin == dest_coin:
        return amount
    # If Price is found & 'dest_coin' is a 'base_coin', return price
    prc = Price.query.filter_by(coin=orig_coin, base_coin=dest_coin)\
                     .first()
    if prc:
        return round(prc.price * amount, 8)
    # If Price is found & 'dest_coin' is a 'coin', return 1/price
    prc = Price.query.filter_by(coin=dest_coin, base_coin=orig_coin)\
                     .first()
    if prc:
        return round(1 / prc.price * amount, 8)
    # Else, triangulate FX using BTC prices (Case if Type=Crypto)
    prc_orig_btc = Price.query.filter_by(coin=orig_coin, base_coin='BTC')\
                              .first()
    prc_dest_btc = Price.query.filter_by(coin=dest_coin, base_coin='BTC')\
                              .first()
    if prc_orig_btc and prc_dest_btc:
        return round(prc_orig_btc.price / prc_dest_btc.price * amount, 8)
    # Else, triangulate FX using BTC prices (Case if Type=Fiat)
    prc_orig_fiat = Price.query.filter_by(coin='BTC', base_coin=orig_coin)\
        .first()
    prc_dest_fiat = Price.query.filter_by(coin='BTC', base_coin=dest_coin)\
        .first()
    if prc_orig_fiat and prc_dest_fiat:
        return round(prc_dest_fiat.price / prc_orig_fiat.price * amount, 8)
    # If the FX could not be calculated, return 'None'
    logger.warning("fx_exchange: FX could not be calculated for '{}"
                   "-{}'".format(orig_coin, dest_coin))
    return None
