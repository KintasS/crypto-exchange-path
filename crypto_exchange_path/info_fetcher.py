import json
import traceback
import urllib.request
from urllib.request import urlopen
from crypto_exchange_path import db, mail
from crypto_exchange_path.models import Coin, TradePair, Exchange, Price, Fee
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import (get_active_coins,
                                           get_exch_by_coin,
                                           get_coin_by_price_id,
                                           get_exchanges,
                                           get_coins)
from crypto_exchange_path.utils import (generate_file_path,
                                        resize_image,
                                        error_notifier)


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
            error_desc = ("update_coins: Provider error: '{}'"
                          .format(error))
            logger.error(error_desc)
            error_notifier("update_coins",
                           error_desc,
                           mail,
                           logger)
            return error_desc
    except Exception as e:
        logger.error("update_coins: Error fetching coins from "
                     "source. URL='{}' [{}]".format(url, e))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Compare size of query with coins currently in DB
    cryptos_in_db = Coin.query.filter_by(type="Crypto").all()
    coins = coins["Data"]
    if len(coins) < len(cryptos_in_db) * 0.8:
        error_desc = ("update_coins(): Did not update coins because there are "
                      "much less coins than currently in DB: {} Vs {}."
                      "".format(len(coins), len(cryptos_in_db)))
        logger.error(error_desc)
        error_notifier("update_coins",
                       error_desc,
                       mail,
                       logger)
        return error_desc
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
                error_notifier(type(e).__name__,
                               traceback.format_exc(),
                               mail,
                               logger)
                return traceback.format_exc()
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
            #         logger.warning("fetch_prices: '{}' flagged inactive as "
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
    # Finally, update coins in JSON file
    update_coins_file("crypto_exchange_path/static/data/coins.json")
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
        print("New tag added: {} ({})".format(id, index+1))
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
    coins = get_coins(type="Crypto")
    print("update_coins_info: Processing '{}' coins. Starting...")
    # Create return dictionary
    coins_dict = {}
    # Loop for each coin
    for index, coin in enumerate(coins):
        print("update_coins_info: Processing coin '{}' --> {}"
              "".format(index+1, coin))
        # Fetch JSON file from site
        try:
            coin_id = coin.paprika_id
            if not coin_id:
                continue
            with urlopen("https://api.coinpaprika.com/v1/coins/{}"
                         "".format(coin_id)) as response:
                source = response.read()
            coin_data = json.loads(source)
        except Exception as e:
            error_desc = ("update_coins_info: Could not fetch json for"
                          " {} [{}]".format(coin.symbol, coin.paprika_id))
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
                                                  coin.paprika_id))
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


def get_coins_from_paprika(logger):
    """Gets list of coins from paprika and store them in file.
    File just to MANUALLY map coins with Coinpaprika ID.
    """
    dest_file = generate_file_path('static/imports', 'paprika_coins')
    # Fetch JSON file from site
    try:
        with urlopen("https://api.coinpaprika.com/v1/coins") as response:
            source = response.read()
        coins_data = json.loads(source)
    except Exception as e:
        logger.error("get_coins_from_paprika: Could not fetch json")
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
    # Check if JSON is a list. Throw error otherwise
    if not isinstance(coins_data, list):
        logger.error("get_coins_from_paprika: The JSON is not a list")
        error_notifier("get_coins_from_paprika",
                       "The JSON is not a list",
                       mail,
                       logger)
        return "get_coins_from_paprika: The JSON is not a list"
    # Read JSON and generate file
    with open(dest_file, "a") as f:
        for crypto in coins_data:
            try:
                id = crypto["id"]
                name = crypto["name"]
                symbol = crypto["symbol"]
                rank = crypto["rank"]
                type = crypto["type"]
                f.write(("{};{};{};{};{}\n").format(id,
                                                    name,
                                                    symbol,
                                                    rank,
                                                    type))
            except KeyError as e:
                logger.warning("get_coins_from_paprika: Bad JSON format for "
                               "'{}'".format(crypto))
                continue
            except Exception as e:
                logger.error("get_coins_from_paprika: Unexpected error for "
                             "'{}'. Coin not stored"
                             .format(crypto))
                error_notifier(type(e).__name__,
                               traceback.format_exc(),
                               mail,
                               logger)
                continue
    logger.debug("get_coins_from_paprika: Coins updated")
    return "ok"


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
        id, symbol, ln, url_ln, prc_id, p_id, rank, url, loc_fn, type, stat = line\
            .replace("\n", "").split("¬")
        coin = Coin(id=id,
                    symbol=symbol,
                    long_name=ln,
                    url_name=url_ln,
                    price_id=prc_id,
                    paprika_id=p_id,
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
