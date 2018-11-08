import json
import urllib.request
from urllib.request import urlopen
from crypto_exchange_path import db
from crypto_exchange_path.models import Coin, TradePair, Exchange, Price, Fee
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import (get_active_coins, get_exch_by_coin,
                                           get_coin_by_price_id, get_exchanges)
from crypto_exchange_path.utils import generate_file_path, resize_image


def update_coins(logger):
    """Gets all the coins available in Provider.
    ONLY TO BE USED IN TEST DATABASES TO LATER DOWNLOAD AND EDIT COINS.
    """
    return None
    logger.info("update_coins(): Starting process")
    try:
        url = Params.URL_COINS
        with urlopen(url) as response:
            source = response.read()
        coins = json.loads(source)
        # If Provider responds successfully, process data:
        if coins["Response"] != 'Success':
            error = coins["Response"]
            logger.error("update_coins: Provider error: '{}'"
                         .format(error))
            return
    except Exception as e:
        logger.error("update_coins: Error fetching coins from "
                     "source. URL='{}' [{}]".format(url, e))
        return 1
    # Compare size of query with coins currently in DB
    cryptos_in_db = Coin.query.filter_by(type="Crypto").all()
    coins = coins["Data"]
    if len(coins) < len(cryptos_in_db) * 0.8:
        logger.error("update_coins(): Did not update coins because there are "
                     "much less coins than currently in DB: {} Vs {}."
                     .format(len(coins), len(cryptos_in_db)))
        return 1
    else:
        # Delete table contents
        Coin.query.filter_by(type="Crypto").delete()
        db.session.commit()
    for coin in coins:
        try:
            # Get symbol and long_name
            symbol = coins[coin]["Symbol"]
            long_name = coins[coin]["CoinName"]
            # If Symbol has blank spaces, don't store coin (bad format)
            if " " in symbol:
                logger.warning("update_coins: Coin '{}' not stored due to "
                               "wrong symbol format (blank spaces)"
                               "".format(symbol))
                continue
            # Get Image URL
            try:
                image_url = coins[coin]["ImageUrl"]
            except KeyError as e:
                image_url = None
            if image_url == 'N/A':
                image_url = None
            # Generate local filename
            local_fn = None
            if image_url:
                local_fn = image_url.replace('/media/', '').replace('/', '_')
            # Insert coin in DB
            c = Coin(symbol=symbol,
                     long_name=long_name,
                     market_cap=None,
                     image_url=image_url,
                     local_fn=local_fn,
                     type="Crypto",
                     status="Active")
            db.session.add(c)
            db.session.commit()
        # Warning if unicode characters are found in the JSON
        except UnicodeEncodeError as e:
            logger.warning("update_coins() [UnicodeEncodeError] [{}]: {}"
                           .format(symbol, e))
            continue
        except KeyError as e:
            logger.warning("update_coins() [KeyError] [{}]: {}"
                           .format(symbol, e))
            continue
    logger.info("update_coins(): 'COINS' updated")
    return 0


def store_coin_images(logger):
    """Stores the coin images from Provider and resizes them.
    """
    logger.info("store_coin_images: Starting process...")
    coins = Coin.query.all()
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36'
         ' (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
    urllib.request.install_opener(opener)
    index = 1
    for coin in coins:
        if coin.image_url and coin.local_fn:
            try:
                # Save original image in local drive
                url = Params.URL_COIN_IMG + coin.image_url
                path_300 = "crypto_exchange_path/static/img/coins/orig/" + \
                           coin.local_fn
                urllib.request.urlretrieve(url, path_300)
                # Save picture in 16x16
                size = 16
                dest_path = "crypto_exchange_path/static/img/coins/{}/{}"\
                            .format(size, coin.local_fn)
                resize_image(path_300, dest_path, size)
            except Exception as e:
                logger.warning("store_coin_images: Could not store images "
                               "for '{}'".format(coin.symbol))
                continue
        if index % 100 == 0:
            logger.info("store_coin_images: Processed {} of {} coins"
                        .format(index, len(coins)))
        index += 1
    logger.info("store_coin_images: Process finished!")


def update_pairs(logger):
    """
    *** DEPRECATED. WILL BE UPDATED MANUALLY ***
    Gets the pairs available in each exchange from Provider.
    """
    # Get information from the source
    logger.info("get_pair_info(): Starting process...")
    try:
        url = Params.URL_PAIRS
        with urlopen(url) as response:
            source = response.read()
        exchange_pairs = json.loads(source)
        logger.info("update_pairs: PAIRS info downloaded from source")
    except Exception as e:
        logger.error("update_pairs: Error fetching pairs from "
                     "source. URL='{}' [{}]".format(url, e))
        return 1
    # Get Exchanges in DB
    db_exchanges = Exchange.query.all()
    db_exchanges = [item.id for item in db_exchanges]
    # Delete PAIRS table contents
    TradePair.query.delete()
    # Get all the coins currently in the DB:
    coin_list = get_active_coins()
    # Insert new information in the table
    for exchange in exchange_pairs:
        if exchange not in db_exchanges:
            continue
        for coin in exchange_pairs[exchange]:
            # If coin is not in the DB, skip coin
            if coin not in coin_list:
                logger.info("update_pairs_table: Coin '{}' skipped. It does "
                            "not exist in the DB.".format(coin))
                continue
            for base_coin in exchange_pairs[exchange][coin]:
                # If baseCoin is not in the DB, skip coin:
                if base_coin not in coin_list:
                    logger.info("update_pairs_table: BaseCoin '{}' skipped. It"
                                " does not exist in the DB.".format(base_coin))
                    continue
                # If Coin==BaseCoin, skip pair:
                elif coin == base_coin:
                    logger.debug("update_pairs_table: Coin and BaseCoin are "
                                 "the same coin: '{}'. Pair skipped."
                                 .format(base_coin))
                    continue
                # Insert row:
                pair = TradePair(exchange=exchange,
                                 coin=coin,
                                 base_coin=base_coin,
                                 volume=-1)
                db.session.add(pair)
    db.session.commit()
    logger.info("update_pairs_table: PAIRS table updated")
    return 0


def update_trading_vol(logger):
    """Updates the trading volume of table 'TradePair' for all the pairs.
    *** DEPRECATED. WILL BE UPDATED MANUALLY ***
    """
    # Get pairs in DB
    pairs = db.session.query(TradePair.coin, TradePair.base_coin)\
                      .filter_by(volume=-1)\
                      .distinct(TradePair.coin, TradePair.base_coin).all()
    # Loop for each pair in DB:
    for pair in pairs:
        logger.info("STARTING FOR {}".format(pair))
        coin = pair[0]
        base_coin = pair[1]
        try:
            with urlopen(Params.URL_PAIR_VOL
                         .format(coin, base_coin)) as response:
                source = response.read()
            vol_data = json.loads(source)
        except Exception as e:
            logger.error("update_trading_vol: {} [coin={}, base_coin={}]"
                         .format(e, coin, base_coin))
            continue
        # If Provider responded successfully, process data:
        if vol_data["Response"] == 'Success':
            for exch in vol_data["Data"]:
                try:
                    exchange = exch["exchange"]
                    vol = exch["volume24h"]
                    # Find row and update
                    db_pair = TradePair.query.filter_by(exchange=exchange,
                                                        coin=coin,
                                                        base_coin=base_coin)\
                        .first()
                    if db_pair:
                        db_pair.volume = vol
                except KeyError as e:
                    logger.warning("update_trading_vol: No JSON keys found"
                                   " for '{}-{}-{}'"
                                   .format(exchange, coin, base_coin))
                    continue
            db.session.commit()
            logger.debug("update_trading_vol: volumes updated for {}-{}"
                         .format(coin, base_coin))
        # If Provider responds with an error, handle it:
        elif vol_data["Response"] == 'Error':
            error = vol_data["Message"]
            logger.error("Provider error: '{}'".format(error))
            return 1
    logger.debug("update_trading_vol: volumes updated")


def update_prices(logger):
    """Fetches the prices of all the cryptos in database.
    If no price is found for any of them, they are flagged as 'Inactive'.
    """
    # File where prices will be temporaly stored
    dest_file = generate_file_path('static/imports', 'prices')
    # Get cryptos and Fiat to fetch prices from
    cryptos = get_active_coins("Crypto", True)
    # Get Coins to request prices against and generate string
    fiats = get_active_coins("Fiat", True)
    currencies = "BTC,ETH"
    for fiat in fiats:
        currencies += "," + fiat
    # Generate a string of less than 'max_len' to fetch the data
    max_len = Params.PRICE_FETCH_LENGTH
    next_coins = ""
    next_coins_lst = []
    is_compl = False
    for index, coin in enumerate(cryptos):
        # While list is not complete (or not last item), append coins
        if ((len(next_coins) + len(coin) + 1 < max_len) or
                (index == len(cryptos) - 1)):
            next_coins += coin + ","
            next_coins_lst.append(coin)
        else:
            is_compl = True
        # If the loop is finished, time to fetch data as well
        if index == len(cryptos) - 1:
            is_compl = True
        # Fetch data if list is generated or loop is finished
        if is_compl:
            try:
                url = Params.URL_PRICES.format(next_coins, currencies)
                with urlopen(url) as response:
                    source = response.read()
                prices = json.loads(source)
            except Exception as e:
                logger.error("update_prices: Error fetching prices from "
                             "source. URL='{}' [{}]".format(url, e))
                return 1
            # Store data in file
            with open(dest_file, "a") as f:
                for crypto in prices:
                    try:
                        for currency in prices[crypto]:
                            prc = prices[crypto][currency]
                            crypto_id = get_coin_by_price_id(crypto)
                            if crypto_id:
                                f.write(("{};{};{}\n").format(crypto_id.id,
                                                              currency,
                                                              prc))
                            else:
                                logger.warning("update_prices: No coin found "
                                               "in DB for price_id={}"
                                               .format(crypto))
                        next_coins_lst.remove(crypto)
                    except KeyError as e:
                        logger.warning("update_prices: Bad JSON format for "
                                       "'{}'".format(crypto))
                        continue
                    except Exception as e:
                        logger.warning("update_prices: Unexpected error for "
                                       "'{}'. Prices not stored"
                                       .format(crypto))
                        continue
            # Flag as "Inactive" coins from which there are no prices
            # for item in next_coins_lst:
            #     db_crypto = Coin.query.filter_by(symbol=item).first()
            #     if db_crypto:
            #         db_crypto.status = "Inactive"
            #         logger.warning("fetch_prices: '{}' flagged as inactive as "
            #                        "no prices could be fetched".format(item))
            db.session.commit()
            # Initialize variables to start the process again
            is_compl = False
            next_coins = coin + ","
            next_coins_lst = [coin]
    # Read file to store contents in DB
    try:
        with open(dest_file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("update_prices: Could not read '{}'".format(dest_file))
        return 1
    # Compare sizes
    db_prices = Price.query.all()
    if len(f_contents) < len(db_prices) * 0.8:
        logger.error("update_prices: Fetched much less prices that previous "
                     "time ('{}' Vs '{}'). Not stored in DB."
                     .format(len(f_contents), len(db_prices)))
        return 1
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
    # Finally, update coins in JSON file
    update_coins_file("crypto_exchange_path/static/data/coins.json")
    return


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
        return 1
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
    exchs = get_exchanges(['Wallet', 'Exchange'])
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
        wallet_bank = 'Wallet'
        if coin.type == 'Fiat':
            wallet_bank = 'Bank'
        try:
            exchs = list(get_exch_by_coin(coin.symbol))
            exchs.append(wallet_bank)
            result_dict[coin.long_name] = exchs
        except Exception as e:
            result_dict[coin.long_name] = [wallet_bank]
    # Repleace data in JSON with merged data and save to file:
    with open(file, "w") as f:
        json.dump(result_dict, f)


def import_exchanges(logger, file):
    """Imports 'Exchange' table from file.
    Example: import_exchanges(logger, "./.../static/inputs/exchanges.txt")
    """
    try:
        with open(file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("import_exchanges: Could not read file '{}'".format(file))
        return 1
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
        return 1
    # Delete previous records
    db_fee = Fee.query.all()
    if len(f_contents) > len(db_fee) * 0.8:
        Fee.query.delete()
    else:
        logger.warning("import_fees: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents), len(db_fee)))
    # Loop for each line
    for line in f_contents:
        exch, action, scope, amt, min_amt, fee_coin, type = line\
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
                  type=type)
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
        return 1
    # Delete previous records
    db_coin = Coin.query.all()
    if len(f_contents) > len(db_coin) * 0.8:
        Coin.query.delete()
    else:
        logger.warning("import_coins: Much less rows in new version."
                       " '{}' Vs '{}'.".format(len(f_contents), len(db_coin)))
    # Loop for each line
    for line in f_contents:
        id, symbol, ln, prc_id, rank, url, loc_fn, type, stat = line\
            .replace("\n", "").split("¬")
        coin = Coin(id=id,
                    symbol=symbol,
                    long_name=ln,
                    price_id=prc_id,
                    ranking=rank,
                    image_url=url,
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
        return 1
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
