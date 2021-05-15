from flask import Markup
from crypto_exchange_path.models import (Coin, TradePair, Fee, Price,
                                         Exchange, Mappings, Subscriber)
from crypto_exchange_path import db
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils import (is_number,
                                        float_to_str)
from crypto_exchange_path.fx_manager import set_fx, get_fx


def get_coins(pos_limit=999999, type=None, status=None, return_ids=False):
    """Returns the active coins available in 'Coin' table.
    If type is given, only those coins are retrieved (Cryptos o Fiat)
    If a position limit is given, only coins ranked below that figure are
    retrieved.
    """
    if type and status:
        coin_in_db = db.session.query(Coin)\
            .filter((Coin.type == type) &
                    (Coin.ranking <= pos_limit) &
                    (Coin.status == status)).all()
    elif type:
        coin_in_db = db.session.query(Coin)\
            .filter((Coin.type == type) &
                    (Coin.ranking <= pos_limit)).all()
    elif status:
        coin_in_db = db.session.query(Coin)\
            .filter((Coin.ranking <= pos_limit) &
                    (Coin.status == status)).all()
    else:
        coin_in_db = db.session.query(Coin)\
            .filter(Coin.ranking <= pos_limit).all()
    coin_in_db = sorted(coin_in_db, key=lambda x: x.ranking)
    if return_ids:
        list_of_ids = []
        for coin in coin_in_db:
            list_of_ids.append(coin.id)
        return list_of_ids
    return coin_in_db


def get_coin(id):
    """Returns a Coin object given its symbol.
    """
    coin = Coin.query.filter_by(id=id).first()
    return coin


def get_coin_by_symbol(symbol):
    """Returns a Coin object given its symbol.
    """
    coin = Coin.query.filter_by(symbol=symbol).first()
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


def get_exchanges(types=[], status=None):
    """Returns the list of exchanges available in 'Exchange' table.
    """
    exchanges = []
    if types and status:
        for type in types:
            exchanges += Exchange.query\
                .filter_by(type=type, status=status).all()
    elif types:
        for type in types:
            exchanges += Exchange.query.filter_by(type=type).all()
    elif status:
        exchanges += Exchange.query.filter_by(status=status).all()
    else:
        exchanges = Exchange.query.all()
    return sorted(exchanges, key=lambda x: x.id)


def get_exchange_choices(types=[], status=None):
    """Returns the list of exchanges available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    exchanges = get_exchanges(types, status)
    choices = []
    for exch in exchanges:
        choices.append((exch.id, exch.name))
    return choices


def get_currency_choices():
    """Returns the list of currencies available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    currencies = get_coins(type='Fiat', status='Active')
    choices = []
    for currency in currencies:
        choices.append((currency.id, currency.id))
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


def get_coins_in_pairs():
    """Gets all the coins available in 'TradePair' table.
    """
    pairs = db.session.query(TradePair).all()
    coins_in_pairs = set()
    for pair in pairs:
        coins_in_pairs.add(pair.coin)
        coins_in_pairs.add(pair.base_coin)
    return coins_in_pairs


def get_coins_by_exchange(exchange):
    """Gets the coins available in 'TradePair' for a given exchange.
    """
    pairs = TradePair.query.filter_by(exchange=exchange).all()
    coins_in_exchange = set()
    for pair in pairs:
        coins_in_exchange.add(pair.coin)
        coins_in_exchange.add(pair.base_coin)
    return coins_in_exchange


def get_exch_by_coin(coin):
    """Gets the exchanges that allows deposit or withdrawal of 'coin'.
    It is assumed that, in order for an exchange to allow the deposit of a
    coin, it must allow the withdrawal of that coin (which should be the case).
    """
    exchs = db.session.query(Fee.exchange)\
                      .filter((Fee.action == 'Withdrawal') &
                              (Fee.status == 'Active') &
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
            coins = fee.scope.split("/")
            if len(coins) == 2:
                coin_id_a = get_coin(coins[0]).symbol
                coin_id_b = get_coin(coins[1]).symbol
                scope = "{}/{}".format(coin_id_a, coin_id_b)
            else:
                scope = fee.scope
            return_list.append({"order": 9,
                                "scope": scope,
                                "amount": str(fee.amount) + '%'})
    return_list = sorted(return_list, key=lambda x: x["order"])
    return return_list


def get_subscriber(email, subscription=None):
    """Gets the subscriber object for the given email.
    A type can optionally be returned.
    """
    if subscription:
        subscriber = Subscriber.query.filter_by(email=email,
                                                subscription=subscription)\
            .first()
    else:
        subscriber = Subscriber.query.filter_by(email=email).all()
    return subscriber


def generate_fee_info(fee):
    """Aux function for 'dep_get_with_fees_by_exch(exchange)' and
    'get_coin_fees(coin_id)'.
    Generates the formated content to be provided.
    """
    # If Fee Amount == None, return n/a
    if not is_number(fee.amount):
        return {"amount": 'n/a', "comments": None}
    coin = get_coin(fee.scope)
    # Generate fee string
    fee_str = fee.amount
    # Calculate fee info
    if fee.type == 'Percentage':
        fee_str = "{}%".format(fee.amount)
    else:
        # Check in which coin the fee is paid
        if fee.fee_coin and fee.fee_coin != "-":
            fee_coin = get_coin(fee.fee_coin)
            if fee_coin:
                fee_str = "{} {}".format(float_to_str(fee.amount),
                                         fee_coin.symbol)
            else:
                fee_str = "{} {}".format(float_to_str(fee.amount),
                                         coin.symbol)
        else:
            fee_str = "{} {}".format(float_to_str(fee.amount),
                                     coin.symbol)
    if fee.min_amount and is_number(fee.min_amount):
        try:
            symbol = Params.CURRENCY_SYMBOLS[fee.scope]
        except Exception as e:
            symbol = " {}".format(coin.symbol)
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


def get_fees(exchange=None, action=None, status=None):
    """ Gets the Fees for the given exchange and status.
    """
    if exchange and action and status:
        fees = Fee.query.filter_by(exchange=exchange,
                                   action=action,
                                   status=status).all()
    elif exchange and action:
        fees = Fee.query.filter_by(exchange=exchange, action=action).all()
    elif exchange and status:
        fees = Fee.query.filter_by(exchange=exchange, status=status).all()
    elif action and status:
        fees = Fee.query.filter_by(action=action, status=status).all()
    elif exchange:
        fees = Fee.query.filter_by(exchange=exchange).all()
    elif status:
        fees = Fee.query.filter_by(status=status).all()
    else:
        fees = Fee.query.all()
    return fees


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
                                     status='Active',
                                     action='Withdrawal').all()
    dep_query = Fee.query.filter_by(exchange=exchange,
                                    status='Active',
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
                                     status='Active',
                                     action='Withdrawal').all()
    dep_query = Fee.query.filter_by(scope=coin_id,
                                    status='Active',
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
                                    scope=coin.id,
                                    status='Active').first()
    if fee_query and (fee_query.amount is not None):
        # If Type == 'Absolute', just return value
        if fee_query.type == 'Absolute':
            # Check if fee is provided in another coin
            if ((fee_query.fee_coin != '-') and
                    (fee_query.fee_coin != fee_query.scope)):
                fee_coin = get_coin(fee_query.fee_coin)
                if fee_coin:
                    fx_amt = fx_exchange(fee_coin.id,
                                         coin.id,
                                         fee_query.amount,
                                         logger)
                    fx_amt = round(fx_amt, 2)
                    lit = "{} {} ({} {} equivalent)".format(fx_amt,
                                                            coin.symbol,
                                                            fee_query.amount,
                                                            fee_coin.symbol)
                    return [fx_amt, lit]
            lit = "{} {} (fixed amount)".format(fee_query.amount,
                                                coin.symbol)
            return [fee_query.amount, lit]
        # If Type == 'Percentage', calc fee and check minimum quantity
        elif fee_query.type == 'Percentage':
            wd_fee = fee_query.amount / 100 * amt
            if fee_query.min_amount:
                lit = "{}% (minimum fee of {} {})"\
                    .format(fee_query.amount,
                            fee_query.min_amount,
                            coin.symbol)
                return [max(wd_fee, fee_query.min_amount), lit]
            else:
                lit = "{}%".format(fee_query.amount)
                return [wd_fee, lit]
        # If Type == 'Less1kUSD', get amount in USD and check if less than 1k
        elif fee_query.type == 'Less1kUSD':
            amount_usd = fx_exchange(coin.id, 'usd-us-dollars', amt, logger)
            if amount_usd < 1000:
                lit = "{} {} (fixed amount for deposits of less than $1000)"\
                    .format(fee_query.amount, coin.symbol)
                return [fee_query.amount, lit]
        # If Type == '1%+20', calc 1% and then add 20 units
        elif fee_query.type == '1%+20':
            wd_fee = round(0.01 * amt + 20, 2)
            lit = "1% + 20 {}".format(coin.symbol)
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


def add_mapping(table, field, old_value, new_value):
    """ Adds a new entry to 'Mappings' table.
    """
    if old_value == new_value:
        return
    # If there is an entry with 'new_value', delete that entry
    mapping_in_db = Mappings.query.filter_by(table=table,
                                             field=field,
                                             old_value=new_value).delete()
    # If 'old_value' was once a 'new_value', update that entry
    mapping_in_db = Mappings.query.filter_by(table=table,
                                             field=field,
                                             new_value=old_value).all()
    for mapping in mapping_in_db:
        mapping.new_value = new_value
    # If there is already an entry for 'old_value', update it
    mapping_in_db = Mappings.query.filter_by(table=table,
                                             field=field,
                                             old_value=old_value).first()
    if mapping_in_db:
        mapping_in_db.new_value = new_value
    # Else, add new entry
    else:
        map = Mappings(table=table,
                       field=field,
                       old_value=old_value,
                       new_value=new_value)
        db.session.add(map)
    db.session.commit()


def make_unique_field(field, value):
    """Creates a unique 'symbol' or 'long_name' for a coin.
    """
    is_unique = False
    if field == "symbol":
        while(not is_unique):
            coin_id_db = Coin.query.filter_by(symbol=value).first()
            if coin_id_db:
                value += "+"
            else:
                is_unique = True
    elif field == "long_name":
        while(not is_unique):
            coin_id_db = Coin.query.filter_by(long_name=value).first()
            if coin_id_db:
                value += "+"
            else:
                is_unique = True
    return value


def fx_exchange(orig_coin, dest_coin, amount, logger):
    if amount is None:
        logger.warning("fx_exchange: FX could not be calculated for '{}"
                       "-{}' (amount=None)".format(orig_coin, dest_coin))
        return None
    stored_fx = get_fx(orig_coin, dest_coin)
    if stored_fx:
        return round(stored_fx * amount, 8)
    # If 'orig_coin'='dest_coin', return 'amount' directly
    if orig_coin == dest_coin:
        return amount
    # If Price is found & 'dest_coin' is a 'base_coin', return price
    prc = Price.query.filter_by(coin=orig_coin, base_coin=dest_coin)\
                     .first()
    if prc:
        set_fx(orig_coin, dest_coin, prc.price)
        return round(prc.price * amount, 8)
    # If Price is found & 'dest_coin' is a 'coin', return 1/price
    prc = Price.query.filter_by(coin=dest_coin, base_coin=orig_coin)\
                     .first()
    if prc and (prc.price != 0):
        set_fx(orig_coin, dest_coin, 1 / prc.price)
        return round(1 / prc.price * amount, 8)
    # Else, triangulate FX using USD prices (Case if Type=Crypto)
    prc_orig_usd = Price.query.filter_by(coin=orig_coin,
                                         base_coin='usd-us-dollars')\
        .first()
    prc_dest_usd = Price.query.filter_by(coin=dest_coin,
                                         base_coin='usd-us-dollars')\
        .first()
    fx_triangulation = 0
    if prc_dest_usd and (prc_dest_usd.price != 0):
        fx_triangulation = prc_orig_usd.price / prc_dest_usd.price
    if prc_orig_usd and prc_dest_usd:
        set_fx(orig_coin, dest_coin, fx_triangulation)
        return round(prc_orig_usd.price / prc_dest_usd.price * amount, 8)
    # Else, triangulate FX using BTC prices (Case if Type=Fiat)
    prc_orig_fiat = Price.query.filter_by(coin='btc-bitcoin',
                                          base_coin=orig_coin)\
        .first()
    prc_dest_fiat = Price.query.filter_by(coin='btc-bitcoin',
                                          base_coin=dest_coin)\
        .first()
    fx_triangulation = 0
    if prc_dest_fiat and (prc_dest_fiat.price != 0):
        fx_triangulation = prc_dest_fiat.price / prc_orig_fiat.price
    if prc_orig_fiat and prc_dest_fiat:
        set_fx(orig_coin,
               dest_coin,
               fx_triangulation)
        return round(prc_dest_fiat.price / prc_orig_fiat.price * amount, 8)
    # If the FX could not be calculated, return 'None'
    logger.warning("fx_exchange: FX could not be calculated for '{}"
                   "/{}'".format(orig_coin, dest_coin))
    return None


def get_mapping(table, field, old_value):
    """Gets the new value of a field that has been changed.
    """
    mapping = Mappings.query.filter_by(table=table,
                                       field=field,
                                       old_value=old_value).first()
    if mapping:
        return mapping.new_value
    return None


def get_promos(exchange=None):
    user_promos = Params.USER_PROMOS
    promos = []
    for promo in user_promos:
        promo_exch = get_exchange(promo)
        if promo_exch:
            if exchange is None or promo_exch.id == exchange:
                promos.append({'exchange': promo_exch,
                               'promo_text': Markup(user_promos[promo])})
    return promos
