import os
import json
import traceback
import urllib.request
from urllib.request import urlopen
from crypto_exchange_path import db, mail
from crypto_exchange_path.models import Coin, TradePair, Exchange, Price, Fee
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import (get_exch_by_coin,
                                           get_coin,
                                           get_exchanges,
                                           get_fees,
                                           get_coins,
                                           get_coins_in_pairs,
                                           get_coins_by_exchange,
                                           add_mapping,
                                           make_unique_field)
from crypto_exchange_path.utils import (generate_file_path,
                                        resize_image,
                                        error_notifier)
from crypto_exchange_path.fx_manager import reset_fx

""" ***********************************************************************
***************************************************************************
DB UPDATE FUNCTIONS
***************************************************************************
*********************************************************************** """


def update_coins(logger):
    """Updates the coins table in the DB using the coins available in
    TradePairs.
    """
    # Get coins in TradePair
    coins_in_pairs = get_coins_in_pairs()
    # Get current coins
    current_coins = get_coins()
    removed_coins = ""
    removed_coins_count = 0
    inactive_coins = ""
    inactive_coins_count = 0
    edited_coins = ""
    edited_coins_count = 0
    for crypto in current_coins:
        logger.info("Checking {}".format(crypto.id))
        # Review coins that do not exist in pairs --> 'Inactive' or 'Deleted'
        if crypto.id not in coins_in_pairs:
            # Check if coin still exists in Coinpaprika
            try:
                url = Params.URL_COINS.format(crypto.id)
                with urlopen(url) as response:
                    source = response.read()
                coin_info = json.loads(source)
            except Exception as e:
                # If coin does not exist in Coinpaprika, flag as 'Deleted'
                coin = Coin.query.filter_by(id=crypto.id).first()
                if coin.status != 'Deleted':
                    removed_coins += "Deleted coin --> {} | {} | {} | {}\n"\
                        "".format(crypto.id,
                                  crypto.symbol,
                                  crypto.long_name,
                                  crypto.id)
                    removed_coins_count += 1
                    coin.status = 'Deleted'
                    db.session.commit()
                continue
            # If coin does exist in Coinpaprika, flag as 'Inactive'
            inactive_coins += "Flagged inactive --> {} | {} | {} | {}\n"\
                "".format(crypto.id,
                          crypto.symbol,
                          crypto.long_name,
                          crypto.id)
            inactive_coins_count += 1
            coin = Coin.query.filter_by(id=crypto.id).first()
            coin.status = 'Inactive'
            db.session.commit()
        # In crypto exists in Pairs, update its information
        else:
            if crypto.type == 'Fiat':
                coins_in_pairs.remove(crypto.id)
                continue
            Coin.query.filter_by(id=crypto.id).first()
            try:
                url = Params.URL_COINS.format(crypto.id)
                with urlopen(url) as response:
                    source = response.read()
                coin_info = json.loads(source)
            except Exception as e:
                error_desc = ("update_coins: Could not fetch info for"
                              " {}".format(crypto.id))
                logger.error(error_desc)
                error_notifier(type(e).__name__,
                               traceback.format_exc(),
                               mail,
                               logger)
                coins_in_pairs.remove(crypto.id)
                continue
            try:
                symbol = coin_info["symbol"]
                long_name = coin_info["name"]
                ranking = coin_info["rank"]
            except KeyError as e:
                logger.warning("update_coins: Could not fetch fields for {}"
                               " [{}]".format(crypto.id, e))
                coins_in_pairs.remove(crypto.id)
                continue
            is_edited = False
            old_symbol = crypto.symbol
            old_long_name = crypto.long_name
            old_url_name = crypto.url_name
            symbol_str = ""
            long_name_str = ""
            status_str = ""
            if crypto.symbol != symbol:
                if not (symbol in crypto.symbol and "*" in crypto.symbol):
                    crypto.symbol = make_unique_field("symbol", symbol)
                    add_mapping("Coin", "symbol", old_symbol, symbol)
                    is_edited = True
                    symbol_str = "symbol: '{}' to '{}' | "\
                                 "".format(old_symbol,
                                           crypto.symbol)
            if crypto.long_name != long_name:
                if not (long_name in crypto.long_name and
                        "+" in crypto.long_name):
                    crypto.long_name = make_unique_field("long_name",
                                                         long_name)
                    delete_coin_image(crypto.url_name, logger)
                    crypto.url_name = crypto.long_name.lower()\
                        .replace("-", "")\
                        .replace("/", "")\
                        .replace(" ", "-")
                    crypto.local_fn = crypto.url_name + ".png"
                    add_mapping("Coin",
                                "url_name",
                                old_url_name,
                                crypto.url_name)
                    is_edited = True
                    long_name_str = "long_name: '{}' to '{}' | "\
                        "".format(old_long_name,
                                  crypto.long_name)
            if crypto.status != 'Active':
                crypto.status = 'Active'
                is_edited = True
                status_str = "status: '{}' to '{}'".format('Inactive',
                                                           'Active')
            if is_edited:
                edited_coins += "Edited coin --> {}: {}{}{}\n"\
                                "".format(crypto.id,
                                          symbol_str,
                                          long_name_str,
                                          status_str)
                edited_coins_count += 1
            if ranking > 0:
                crypto.ranking = ranking
            res = store_coin_image(crypto.id, crypto.url_name, logger)
            if not res:
                crypto.local_fn = "__default.png"
            db.session.commit()
            coins_in_pairs.remove(crypto.id)
    # Add new pairs
    added_coins = ""
    added_coins_count = 0
    for crypto in coins_in_pairs:
        logger.info("Adding coin '{}'".format(crypto))
        try:
            url = Params.URL_COINS.format(crypto)
            with urlopen(url) as response:
                source = response.read()
            coin_info = json.loads(source)
        except Exception as e:
            error_desc = ("update_coins: Could not fetch pairs for"
                          " {}".format(crypto))
            logger.error(error_desc)
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            continue
        try:
            id = coin_info["id"]
            symbol = make_unique_field("symbol", coin_info["symbol"])
            long_name = make_unique_field("long_name", coin_info["name"])
            ranking = coin_info["rank"]
            if ranking == 0:
                ranking = 1000
        except KeyError as e:
            logger.warning("update_coins: Could not fetch fields for {}"
                           " [{}]".format(crypto, e))
            continue
        url_name = long_name.lower()\
            .replace("-", "")\
            .replace("/", "")\
            .replace(" ", "-")
        local_fn = url_name + ".png"
        res = store_coin_image(id, url_name, logger)
        if not res:
            local_fn = "__default.png"
        c = Coin(id=id,
                 symbol=symbol,
                 long_name=long_name,
                 url_name=url_name,
                 ranking=ranking,
                 local_fn=local_fn,
                 type="Crypto",
                 status="Active")
        db.session.add(c)
        db.session.commit()
        added_coins += "Added coin --> {} | {} | {} | {}\n"\
                       "".format(c.id,
                                 c.symbol,
                                 c.long_name,
                                 c.id)
        added_coins_count += 1
    # Notify changes
    body = added_coins + removed_coins + inactive_coins + edited_coins
    print(body)
    # send_email_notification("'Coin' table", body, mail, logger)
    # Finish function
    logger.info("update_coins: Coins updated [{} removed / {} inactive / "
                "{} added / {} modified]".format(removed_coins_count,
                                                 inactive_coins_count,
                                                 added_coins_count,
                                                 edited_coins_count))
    return "ok"


def store_coin_image(id, url_name, logger):
    """Stores the coin image from Coinpaprika.
    """
    local_fn = url_name + ".png"
    logger.debug("store_coin_images: Starting process for '{}'".format(id))
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36'
         ' (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
    urllib.request.install_opener(opener)
    try:
        # Save original image in local drive
        url = Params.URL_COIN_IMG.format(id)
        path_orig = "doc/img/coins/orig/" + local_fn
        urllib.request.urlretrieve(url, path_orig)
        # Save picture in other resizes
        sizes = [16, 64]
        for size in sizes:
            dest_path = "crypto_exchange_path/static/img/coins/{}/{}"\
                        .format(size, local_fn)
            resize_image(path_orig, dest_path, size)
    except Exception as e:
        logger.warning("store_coin_images: Could not store images "
                       "for '{}'".format(id))
        return False
    logger.debug("store_coin_images: Process finished!")
    return True


def delete_coin_image(url_name, logger):
    local_fn = url_name + ".png"
    dest_path = "doc/img/coins/orig/" + local_fn
    if os.path.exists(dest_path):
        os.remove(dest_path)
        logger.info("delete_coin_image: '{}' removed".format(dest_path))
    sizes = [16, 64]
    for size in sizes:
        dest_path = "crypto_exchange_path/static/img/coins/{}/{}"\
                    .format(size, local_fn)
        if os.path.exists(dest_path):
            os.remove(dest_path)
            logger.info("delete_coin_image: '{}' removed".format(dest_path))


def update_pairs(logger):
    """Gets the trading pairs for each exchange from Coinpaprika.
    """
    # File where pairs will be temporaly stored
    dest_file = generate_file_path('static/imports', 'pairs')
    exchanges = get_exchanges(["Exchange"])
    for exch in exchanges:
        # Fetch JSON file from Coinpaprika
        try:
            url = Params.URL_PAIRS.format(exch.id)
            with urlopen(url) as response:
                source = response.read()
            exch_pairs = json.loads(source)
        except Exception as e:
            if exch.status == 'Inactive':
                continue
            error_desc = ("update_pairs: Could not fetch pairs for"
                          " {}".format(exch.id))
            logger.error(error_desc)
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            return traceback.format_exc()
        # Store data in file
        with open(dest_file, "a") as f:
            for pair in exch_pairs:
                try:
                    base_crypto = pair["base_currency_id"]
                    quote_crypto = pair["quote_currency_id"]
                    try:
                        volume = pair["reported_volume_24h_share"]
                    except KeyError as e:
                        volume = 0
                    f.write(("{};{};{};{}\n").format(exch.id,
                                                     base_crypto,
                                                     quote_crypto,
                                                     volume))
                except KeyError as e:
                    logger.warning("update_pairs: Bad JSON format for "
                                   "'{}/{}'".format(exch.id, pair["pair"]))
                    continue
                except Exception as e:
                    logger.warning("update_pairs: Unexpected error for "
                                   "'{}/{}'".format(exch.id, pair["pair"]))
                    continue
    # Read file to store contents in DB
    try:
        with open(dest_file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("update_pairs: Could not read '{}'".format(dest_file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Compare sizes
    db_pairs = TradePair.query.all()
    if len(f_contents) < len(db_pairs) * 0.8:
        error_desc = ("update_pairs: Fetched much less pairs than previous "
                      "time ('{}' Vs '{}'). Not stored in DB."
                      .format(len(f_contents), len(db_pairs)))
        logger.error(error_desc)
        error_notifier("update_pairs",
                       error_desc,
                       mail,
                       logger)
        return error_desc
    # Generate dictionary to track changes in 'TradePair'
    current_pairs = {}
    for i in db_pairs:
        try:
            current_pairs[i.exchange][i.coin][i.base_coin] = i.volume
        except KeyError as e:
            try:
                current_pairs[i.exchange][i.coin] = {}
                current_pairs[i.exchange][i.coin][i.base_coin] = i.volume
            except KeyError as e:
                current_pairs[i.exchange] = {}
                current_pairs[i.exchange][i.coin] = {}
                current_pairs[i.exchange][i.coin][i.base_coin] = i.volume
    added_pairs = ""
    # Delete prices from DB
    TradePair.query.delete()
    # Store prices in DB
    for line in f_contents:
        exchange, coin, base_coin, vol = (line.replace("\n", "")).split(";")
        # Track changes
        try:
            _ = current_pairs[exchange][coin][base_coin]
            del current_pairs[exchange][coin][base_coin]
        except KeyError as e:
            added_pairs += "Added pair --> {} | {} | {}\n".format(exchange,
                                                                  coin,
                                                                  base_coin)
        # Store prices in DB
        trade_pair = TradePair(exchange=exchange,
                               coin=coin,
                               base_coin=base_coin,
                               volume=vol)
        db.session.add(trade_pair)
    db.session.commit()
    # Add manual pairs
    manual_pairs_file = "./crypto_exchange_path/static/imports/"\
                        "manual/manual_pairs.txt"
    try:
        with open(manual_pairs_file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("update_pairs: Could "
                     "not read '{}'".format(manual_pairs_file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    for line in f_contents:
        exchange, coin, base_coin, vol = (line.replace("\n", "")).split(";")
        pair_in_db = TradePair.query.filter_by(exchange=exchange,
                                               coin=coin,
                                               base_coin=base_coin).first()
        if not pair_in_db:
            trade_pair = TradePair(exchange=exchange,
                                   coin=coin,
                                   base_coin=base_coin,
                                   volume=vol)
            db.session.add(trade_pair)
    db.session.commit()
    # Notify changes
    removed_pairs = ""
    for exch in current_pairs:
        for coin in current_pairs[exch]:
            for base_coin in current_pairs[exch][coin]:
                removed_pairs += "Removed pair --> {} | {} | {}\n"\
                                 "".format(exch,
                                           coin,
                                           base_coin)
    body = added_pairs + removed_pairs
    print(body)
    # send_email_notification("'TradePair' table", body, mail, logger)
    # Finish function
    logger.info("update_pairs: Pairs updated [{} rows inserted]"
                .format(len(f_contents)))
    return "ok"


def update_fees(logger):
    """Updates the 'Fee' table using the info in 'TradePair' table.
    """
    exchanges = get_exchanges(['Exchange'])
    active_fees = ""
    active_fees_count = 0
    inactive_fees = ""
    inactive_fees_count = 0
    added_fees = ""
    added_fees_count = 0
    for exch in exchanges:
        logger.info("update_fees: Checking '{} ({})'".format(exch.id,
                                                             exch.name))
        # If Exchange is 'Inactive', flag all its fees as inactive
        if exch.status == 'Inactive':
            fees = get_fees(exchange=exch.id)
            for fee in fees:
                fee.status = 'Inactive'
        else:
            exch_coins = get_coins_by_exchange(exch.id)
            # Withdrawal fees - Review fees
            fees = get_fees(exchange=exch.id, action='Withdrawal')
            for fee in fees:
                # If coin not in 'TradePair', mark as inactive
                if fee.scope not in exch_coins:
                    if fee.status != 'Inactive':
                        fee.status = 'Inactive'
                        inactive_fees += "Changed to inactive --> {} | {} | {}"\
                                         "\n".format(fee.exchange,
                                                     fee.action,
                                                     fee.scope)
                        inactive_fees_count += 1
                else:
                    if fee.status == 'Inactive':
                        fee.status = 'Reactivated'
                        active_fees += "Changed to active --> {} | {} | {}"\
                            "\n".format(fee.exchange,
                                        fee.action,
                                        fee.scope)
                        active_fees_count += 1
                    exch_coins.remove(fee.scope)
            # Add new 'Withdrawal' fees to 'Fee' table
            for coin in exch_coins:
                f = Fee(exchange=exch.id,
                        action="Withdrawal",
                        scope=coin,
                        amount=None,
                        min_amount=None,
                        fee_coin="-",
                        type="Absolute",
                        status="Pending")
                db.session.add(f)
                added_fees += "Added fee --> {} | {} | {}\n".format(f.exchange,
                                                                    f.action,
                                                                    f.scope)
                added_fees_count += 1
            # Deposit fees - Review fees (Only for Bitfinex!)
            if exch.id == 'bitfinex':
                exch_coins = get_coins_by_exchange(exch.id)
                fees = get_fees(exchange=exch.id, action='Deposit')
                for fee in fees:
                    # If coin not in 'TradePair', mark as inactive
                    if fee.scope not in exch_coins:
                        if fee.status != 'Inactive':
                            fee.status = 'Inactive'
                            inactive_fees += "Changed to inactive --> "\
                                "{} | {} | {}\n".format(fee.exchange,
                                                        fee.action,
                                                        fee.scope)
                            inactive_fees_count += 1
                    else:
                        if fee.status == 'Inactive':
                            fee.status = 'Reactivated'
                            active_fees += "Changed to active --> {} | {} | {}"\
                                "\n".format(fee.exchange,
                                            fee.action,
                                            fee.scope)
                            active_fees_count += 1
                        exch_coins.remove(fee.scope)
                # Add new 'Deposit' fees to 'Fee' table
                for coin in exch_coins:
                    f = Fee(exchange=exch.id,
                            action="Deposit",
                            scope=coin,
                            amount=None,
                            min_amount=None,
                            fee_coin="-",
                            type="Less1kUSD",
                            status="Pending")
                    db.session.add(f)
                    added_fees += "Added fee --> {} | {} | {}\n"\
                        "".format(f.exchange,
                                  f.action,
                                  f.scope)
                    added_fees_count += 1
        db.session.commit()
    # Notify changes
    body = added_fees + inactive_fees + active_fees
    logger.info("*****************************")
    logger.info(body)
    logger.info("*****************************")
    # send_email_notification("'Coin' table", body, mail, logger)
    # Finish function
    logger.info("update_fees: Fees updated [{} added / "
                "{} flagged as inactive / "
                "{} flagged as active]".format(added_fees_count,
                                               inactive_fees_count,
                                               active_fees_count))
    return "ok"


def update_prices(logger):
    """Fetches the prices of all the cryptos in database.
    """
    # File where prices will be temporaly stored
    dest_file = generate_file_path('static/imports', 'prices')
    # Get cryptos and Fiat to fetch prices from
    cryptos = get_coins(type='Crypto', status='Active')
    crypto_list = set()
    for crypto in cryptos:
        crypto_list.add(crypto.id)
    # Get Coins to request prices against and generate string
    fiats = get_coins(type='Fiat', status='Active')
    fiats.append(get_coin('btc-bitcoin'))
    fiats.append(get_coin('eth-ethereum'))
    fiat_str = ""
    first = True
    for index, fiat in enumerate(fiats):
        if first:
            fiat_str += fiat.symbol
            first = False
        else:
            fiat_str += ',' + fiat.symbol
    # Fetch prices for all coins available in Coinpaprika
    try:
        url = Params.URL_PRICES.format(fiat_str)
        with urlopen(url) as response:
            source = response.read()
        prices = json.loads(source)
    except Exception as e:
        logger.error("update_prices: Error fetching prices from "
                     "source. URL='{}' [{}]".format(url, e))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Store data in file
    with open(dest_file, "a") as f:
        for crypto in prices:
            try:
                if crypto["id"] in crypto_list:
                    for curr in fiats:
                        try:
                            prc = crypto["quotes"][curr.symbol]["price"]
                            f.write(("{};{};{}\n").format(crypto["id"],
                                                          curr.id,
                                                          prc))
                        except KeyError as e:
                            logger.warning("update_prices: No coin found "
                                           "in DB for id={}"
                                           .format(crypto["id"]))
            except KeyError as e:
                logger.warning("update_prices: Bad JSON format for "
                               "'{}'".format(crypto))
                continue
            except Exception as e:
                logger.warning("update_prices: Unexpected error for "
                               "'{}'. Prices not stored"
                               .format(crypto))
                continue
    # Read file to store contents in DB
    try:
        with open(dest_file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("update_prices: Could not read '{}'".format(dest_file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Compare sizes
    db_prices = Price.query.all()
    if len(f_contents) < len(db_prices) * 0.8:
        error_desc = ("update_prices: Fetched much less prices that previous "
                      "time ('{}' Vs '{}'). Not stored in DB."
                      .format(len(f_contents), len(db_prices)))
        logger.error(error_desc)
        error_notifier("update_prices",
                       error_desc,
                       mail,
                       logger)
        return error_desc
    # Delete prices from DB
    Price.query.delete()
    # Store prices in DB
    for line in f_contents:
        coin, currency, price = (line.replace("\n", "")).split(";")
        prc = Price(coin=coin,
                    base_coin=currency,
                    price=price)
        db.session.add(prc)
    db.session.commit()
    logger.info("update_prices: Prices updated [{} rows inserted]"
                .format(len(f_contents)))
    # reset FX dictionary
    reset_fx()
    # Finally, update coins in JSON file
    update_coins_file("crypto_exchange_path/static/data/coins.json")
    return "ok"


""" ***********************************************************************
***************************************************************************
JSON FILES UPDATE FUNCTIONS
***************************************************************************
*********************************************************************** """


def update_exchanges_info(logger):
    """Gets the Exchanges info from Coinpaprika.
    """
    # Create return dictionary
    exchs_dict = {}
    # Loop for Each active Exchange in the DB
    exchanges = get_exchanges(types=['Exchange'], status='Active')
    for index, exchange in enumerate(exchanges):
        # Fetch JSON file from site
        try:
            url = "https://api.coinpaprika.com/v1/exchanges/{}"\
                .format(exchange.id)
            with urlopen(url) as response:
                source = response.read()
            exch_data = json.loads(source)
        except Exception as e:
            logger.error("update_exchanges_info: Could not fetch "
                         "json for {}".format(exchange.id))
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            return traceback.format_exc()
        # Check if JSON is a list. Throw error otherwise
        if not isinstance(exch_data, dict):
            error_desc = "update_exchanges_info: The JSON is not a dictionary"
            logger.error(error_desc)
            error_notifier("update_exchanges_info",
                           error_desc,
                           mail,
                           logger)
            return error_desc
        # Read JSON file
        try:
            id = exch_data["id"]
        except KeyError as e:
            error_desc = ("update_exchanges_info: No key found for {}"
                          "".format(exchange.id))
            print(error_desc)
            logger.warning(error_desc)
            break
        except Exception as e:
            error_desc = ("update_exchanges_info: Error reading '{}': {}"
                          "".format(exchange.id, exch_data))
            print(error_desc)
            logger.error(error_desc)
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            return traceback.format_exc()
        exchs_dict[id] = exch_data
        logger.debug("New exchange added: {} ({})".format(exchange.name,
                                                          index+1))
        print("New exchange added: {} ({})".format(exchange.name,
                                                   index+1))
    # Repleace data in JSON with merged data and save to file:
    file = Params.EXCHANGE_INFO_FILE
    with open(file, "w") as f:
        json.dump(exchs_dict, f)
    logger.debug("update_exchanges_info: Exchanges updated")
    print("update_exchanges_info: Exchanges updated")
    return "ok"


def update_tags_info(logger):
    """Gets the tag info from Coinpaprika.
    """
    # Fetch JSON file from site
    try:
        with urlopen("https://api.coinpaprika.com/v1/tags") as response:
            source = response.read()
        tags_data = json.loads(source)
    except Exception as e:
        logger.error("update_tags_info: Could not fetch json")
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Check if JSON is a list. Throw error otherwise
    if not isinstance(tags_data, list):
        error_desc = "update_tags_info: The JSON is not a list"
        logger.error(error_desc)
        error_notifier("update_tags_info",
                       error_desc,
                       mail,
                       logger)
        return error_desc
    # Create return dictionary
    tags_dict = {}
    # Read JSON file
    for index, tag in enumerate(tags_data):
        try:
            id = tag["id"]
        except KeyError as e:
            logger.warning("update_tags_info: No key found for {}".format(tag))
            continue
        tags_dict[id] = tag
    # Repleace data in JSON with merged data and save to file:
    file = Params.TAG_INFO_FILE
    with open(file, "w") as f:
        json.dump(tags_dict, f)
    logger.debug("update_tags_info: Tags updated")
    return "ok"


def update_coins_info(logger):
    """Gets the coin info from Coinpaprika.
    """
    # Get coins
    coins = get_coins(type="Crypto", status="Active")
    logger.info("update_coins_info: Processing '{}' coins. Starting...")
    # Create return dictionary
    coins_dict = {}
    # Loop for each coin
    for index, coin in enumerate(coins):
        logger.info("update_coins_info: Processing coin '{}' --> {}"
                    "".format(index+1, coin))
        # Fetch JSON file from site
        try:
            coin_id = coin.id
            if not coin_id:
                continue
            with urlopen("https://api.coinpaprika.com/v1/coins/{}"
                         "".format(coin_id)) as response:
                source = response.read()
            coin_data = json.loads(source)
        except Exception as e:
            error_desc = ("update_coins_info: Could not fetch json for"
                          " {} [{}]".format(coin.symbol, coin.id))
            print(error_desc)
            logger.error(error_desc)
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            return traceback.format_exc()
        # Check if JSON is a list. Throw error otherwise
        if not isinstance(coin_data, dict):
            error_desc = ("update_coins_info: The JSON for coin '{} [{}]'"
                          " is not a list".format(coin.symbol,
                                                  coin.id))
            print(error_desc)
            logger.error(error_desc)
            error_notifier("update_coins_info",
                           error_desc,
                           mail,
                           logger)
            return error_desc
        # Read JSON file
        try:
            id = coin_data["id"]
        except KeyError as e:
            error_desc = ("update_coins_info: No key found for {}"
                          "".format(coin.symbol))
            print(error_desc)
            logger.warning(error_desc)
            break
        except Exception as e:
            error_desc = ("update_coins_info: Error reading '{}': {}"
                          "".format(coin.id, coin_data))
            print(error_desc)
            logger.error(error_desc)
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            return traceback.format_exc()
        coins_dict[id] = coin_data
        logger.debug("New coin added: {} ({})".format(coin.symbol, index+1))
        print("New coin added: {} ({})".format(coin.symbol, index+1))
    # Repleace data in JSON with merged data and save to file:
    file = Params.COIN_INFO_FILE
    with open(file, "w") as f:
        json.dump(coins_dict, f)
    logger.debug("update_coins_info: Tags updated")
    print("update_coins_info: Tags updated")
    return "ok"


def update_people_info(logger):
    """Gets the people info from Coinpaprika.
    """
    # Read coins file
    coin_info_file = Params.COIN_INFO_FILE
    try:
        with open(coin_info_file) as f:
            coin_info = json.load(f)
    except Exception as e:
        logger.error("update_prices: Could not read '{}'"
                     "".format(coin_info_file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    coins = coin_info.keys()
    # Create return dictionary
    people_dict = {}
    # Loop for each coin
    for coin in coins:
        # Fetch JSON file from site
        try:
            team = coin_info[coin]["team"]
            # Check if 'team' is a list
            if not isinstance(team, list):
                logger.info("update_people_info: No team list found for "
                            "coin '{} []'".format(coin_info[coin]["symbol"],
                                                  coin_info[coin]["id"]))
                continue
            # Loop for each person in the list
            for person in team:
                person_id = person["id"]
                # Fetch info from people
                try:
                    with urlopen("https://api.coinpaprika.com/v1/people/{}"
                                 "".format(person_id)) as response:
                        source = response.read()
                    person_data = json.loads(source)
                except Exception as e:
                    logger.warning("update_people_info: Could not fetch json"
                                   " for person_id='{}''".format(person_id))
                    continue
                # Check if JSON is a list. Throw error otherwise
                if not isinstance(person_data, dict):
                    error_desc = "update_people_info: The JSON is not a list"
                    logger.error(error_desc)
                    error_notifier("update_people_info",
                                   error_desc,
                                   mail,
                                   logger)
                    return error_desc
                # Read JSON file
                try:
                    id = person_data["id"]
                except KeyError as e:
                    logger.warning("update_people_info: No ID found for {}"
                                   "[{}]-{}".format(coin_info[coin]["symbol"],
                                                    coin_info[coin]["id"],
                                                    person_id))
                    continue
                except Exception as e:
                    logger.error("update_people_info: Error reading {}[{}]-{}"
                                 "".format(coin_info[coin]["symbol"],
                                           coin_info[coin]["id"],
                                           person_id))
                    error_notifier(type(e).__name__,
                                   traceback.format_exc(),
                                   mail,
                                   logger)
                    return traceback.format_exc()
                if person_id not in people_dict:
                    people_dict[person_id] = person_data
                    logger.debug("New person added: {}".format(person_id))
                    print("New person added: {}".format(person_id))
        except KeyError as e:
            logger.warning("update_people_info: No key found for {}"
                           "".format(coin_info[coin]))
            continue
    # Repleace data in JSON with merged data and save to file:
    file = Params.PEOPLE_INFO_FILE
    with open(file, "w") as f:
        json.dump(people_dict, f)
    logger.debug("update_people_info: Tags updated")
    return "ok"


# def get_coins_from_paprika(logger):
#     """Gets list of coins from paprika and store them in file.
#     File just to MANUALLY map coins with Coinpaprika ID.
#     """
#     dest_file = generate_file_path('static/imports', 'paprika_coins')
#     # Fetch JSON file from site
#     try:
#         with urlopen("https://api.coinpaprika.com/v1/coins") as response:
#             source = response.read()
#         coins_data = json.loads(source)
#     except Exception as e:
#         logger.error("get_coins_from_paprika: Could not fetch json")
#         error_notifier(type(e).__name__,
#                        traceback.format_exc(),
#                        mail,
#                        logger)
#         return traceback.format_exc()
#     # Check if JSON is a list. Throw error otherwise
#     if not isinstance(coins_data, list):
#         logger.error("get_coins_from_paprika: The JSON is not a list")
#         error_notifier("get_coins_from_paprika",
#                        "The JSON is not a list",
#                        mail,
#                        logger)
#         return "get_coins_from_paprika: The JSON is not a list"
#     # Read JSON and generate file
#     with open(dest_file, "a") as f:
#         for crypto in coins_data:
#             try:
#                 id = crypto["id"]
#                 name = crypto["name"]
#                 symbol = crypto["symbol"]
#                 rank = crypto["rank"]
#                 type = crypto["type"]
#                 f.write(("{};{};{};{};{}\n").format(id,
#                                                     name,
#                                                     symbol,
#                                                     rank,
#                                                     type))
#             except KeyError as e:
#                 logger.warning("get_coins_from_paprika: Bad JSON format for "
#                                "'{}'".format(crypto))
#                 continue
#             except Exception as e:
#                 logger.error("get_coins_from_paprika: Unexpected error for "
#                              "'{}'. Coin not stored"
#                              .format(crypto))
#                 error_notifier(type(e).__name__,
#                                traceback.format_exc(),
#                                mail,
#                                logger)
#                 continue
#     logger.debug("get_coins_from_paprika: Coins updated")
#     return "ok"


def get_bittrex_fees(logger):
    """Fetches the fees from Bittrex API and stores them in a TXT file..
    """
    # File where prices will be temporaly stored
    dest_file = generate_file_path('static/imports', 'bittrex_fees')
    try:
        url = Params.URL_BITTREX_FEES
        with urlopen(url) as response:
            source = response.read()
        bittrex_fees = json.loads(source)
    except Exception as e:
        logger.error("get_bittrex_fees [1]: Error fetching Bittrex fees from "
                     "source. URL='{}' [{}]".format(url, e))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Check if response success returns True
    if not bittrex_fees["success"]:
        logger.error("get_bittrex_fees [2]: Error fetching Bittrex fees from "
                     "source. URL='{}'".format(url))
        return 2
    if 'result' in bittrex_fees.keys():
        fee_info = bittrex_fees['result']
        with open(dest_file, "a") as f:
            # Write header
            header = ""
            for item in fee_info[0].keys():
                header += str(item) + ";"
            f.write(header + "\n")
            # Write info for each coin
            for coin in fee_info:
                currency = coin['Currency']
                currencyLong = coin['CurrencyLong']
                minConfirmation = coin['MinConfirmation']
                txFee = coin['TxFee']
                isActive = coin['IsActive']
                isRestricted = coin['IsRestricted']
                coinType = coin['CoinType']
                baseAddress = coin['BaseAddress']
                notice = coin['Notice']
                f.write("{};{};{};{};{};{};{};{};{}\n".format(currency,
                                                              currencyLong,
                                                              minConfirmation,
                                                              txFee,
                                                              isActive,
                                                              isRestricted,
                                                              coinType,
                                                              coinType,
                                                              baseAddress,
                                                              notice))
    logger.info("get_bittrex_fees: Process finished!")


def update_coins_file(file):
    """Updates the JSON file that is later used to prompt coin suggestions
    to the user.
    """
    result_list = []
    coins = Coin.query.filter_by(status='Active')
    for coin in coins:
        coin_dic = {"id": coin.symbol,
                    "name": coin.symbol,
                    "long_name": coin.long_name,
                    "img": coin.local_fn,
                    "ranking": coin.ranking}
        result_list.append(coin_dic)
    # Repleace data in JSON with merged data and save to file:
    with open(file, "w") as f:
        json.dump(result_list, f)


def generate_exchs_file(file):
    """Updates the JSON file that is used to populate locations in
    the exchange search form.
    """
    result_dict = {}
    exchs = get_exchanges(['Wallet', 'Exchange'], status='Active')
    exch_order = 1
    for exch in exchs:
        exch_dic = {"id": exch.id,
                    "name": exch.name,
                    "img": exch.img_fn,
                    "ranking": exch_order}
        result_dict[exch.id] = exch_dic
        exch_order = exch_order + 1
    # Repleace data in JSON with merged data and save to file:
    with open(file, "w") as f:
        json.dump(result_dict, f)


def generate_exchs_by_coin_file(file):
    """Updates the JSON file that is used by Javascript for tests.
    """
    result_dict = {}
    coins = Coin.query.filter_by(status='Active')
    for coin in coins:
        wallet_bank = 'wallet'
        if coin.type == 'Fiat':
            wallet_bank = 'bank'
        try:
            exchs = list(get_exch_by_coin(coin.id))
            exchs.append(wallet_bank)
            result_dict[coin.long_name] = exchs
        except Exception as e:
            result_dict[coin.long_name] = [wallet_bank]
    # Repleace data in JSON with merged data and save to file:
    with open(file, "w") as f:
        json.dump(result_dict, f)


""" ***********************************************************************
***************************************************************************
IMPORT TO DB FUNCTIONS
***************************************************************************
*********************************************************************** """


def import_exchanges(logger, file):
    """Imports 'Exchange' table from file.
    Example: import_exchanges(logger, "./.../static/inputs/exchanges.txt")
    """
    try:
        with open(file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("import_exchanges: Could not read file '{}'".format(file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Delete previous records
    db_exch = Exchange.query.all()
    if len(f_contents) > len(db_exch) * 0.8:
        Exchange.query.delete()
    else:
        logger.warning("import_exchanges: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents), len(db_exch)))
    # Loop for each line
    for line in f_contents:
        id, name, type, img, url, af, lan = (line.replace("\n", "")).split("¬")
        exch = Exchange(id=id,
                        name=name,
                        type=type,
                        img_fn=img,
                        site_url=url,
                        affiliate=af,
                        language=lan)
        db.session.add(exch)
    db.session.commit()
    logger.info("import_exchanges: {} rows inserted".format(len(f_contents)))
    return


def import_fees(logger, file):
    """Imports 'Exchange' table from file.
    Example: import_fees(logger, "./.../static/inputs/fees.txt")
    """
    try:
        with open(file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("import_fees: Could not read file '{}'".format(file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Delete previous records
    db_fee = Fee.query.all()
    if len(f_contents) > len(db_fee) * 0.8:
        Fee.query.delete()
    else:
        logger.warning("import_fees: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents), len(db_fee)))
    # Loop for each line
    for line in f_contents:
        exch, action, scope, amt, min_amt, fee_coin, type, status = line\
            .replace("\n", "").split("¬")
        if amt == '':
            amt = None
        if min_amt == '':
            min_amt = None
        fee = Fee(exchange=exch,
                  action=action,
                  scope=scope,
                  amount=amt,
                  min_amount=min_amt,
                  fee_coin=fee_coin,
                  type=type,
                  status=status)
        db.session.add(fee)
        db.session.commit()
    logger.info("import_fees: {} rows inserted".format(len(f_contents)))
    return


def import_coins(logger, file):
    """Imports 'Coin' table from file.
    Example: import_coins(logger, "./.../static/inputs/coins.txt")
    """
    try:
        with open(file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("import_coins: Could not read file '{}'".format(file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Delete previous records
    db_coin = Coin.query.all()
    if len(f_contents) > len(db_coin) * 0.8:
        Coin.query.delete()
    else:
        logger.warning("import_coins: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents), len(db_coin)))
    # Loop for each line
    for line in f_contents:
        id, symbol, ln, url_ln, rank, loc_fn, type, stat = line\
            .replace("\n", "").split("¬")
        coin = Coin(id=id,
                    symbol=symbol,
                    long_name=ln,
                    url_name=url_ln,
                    ranking=rank,
                    local_fn=loc_fn,
                    type=type,
                    status=stat)
        db.session.add(coin)
    db.session.commit()
    logger.info("import_coins: {} rows inserted".format(len(f_contents)))
    return


def import_pairs(logger, file):
    """Imports 'TradePair' table from file.
    Example: import_coins(logger, "./.../static/inputs/pairs.txt")
    """
    try:
        with open(file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("import_pairs: Could not read file '{}'".format(file))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Delete previous records
    db_pair = TradePair.query.all()
    if len(f_contents) > len(db_pair) * 0.8:
        TradePair.query.delete()
    else:
        logger.warning("import_pairs: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents),
                                               len(db_pair)))
    # Loop for each line
    for line in f_contents:
        exchange, coin, base_coin, volume = line.replace("\n", "").split("¬")
        pair = TradePair(exchange=exchange,
                         coin=coin,
                         base_coin=base_coin,
                         volume=volume)
        db.session.add(pair)
        db.session.commit()
    logger.info("import_pairs: {} rows inserted".format(len(f_contents)))
    return
