import os
import json
import logging
import datetime
import traceback
from secrets import token_hex
from PIL import Image
from crypto_exchange_path import app
from crypto_exchange_path.config import Params
from flask_mail import Message
from crypto_exchange_path.models import Price


def set_logger(logger_name, level="INFO"):
    """Sets logging configuration.
    """
    logger = logging.getLogger(logger_name)
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    # Set-up logger in log file
    # dt_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # file_handler = logging.FileHandler("logs/{}_{}.log".format(logger_name,
    #                                                            dt_str))
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
    # Set-up looger in console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # Return logger to allow it to be called from outside
    return logger


def error_notifier(error_type, error_traceback, mail, logger):
    # Log error
    logger.error("Unexpected error: {}".format(error_traceback))
    # Send email
    try:
        msg = Message('App ERROR - {}'.format(error_type),
                      sender=Params.SENDER_EMAIL,
                      recipients=[Params.ERROR_RECIPIENT_EMAIL])
        msg.body = f'''Error en la aplicación. Traza:

        {error_traceback}

        '''
        mail.send(msg)
    except Exception as e:
        logger.error("error_notifier: {}".format(traceback.format_exc()))


def feedback_notifier(text, page, mail, logger):
    # Send email
    try:
        msg = Message("App FEEDBACK - Page '{}'".format(page),
                      sender=Params.SENDER_EMAIL,
                      recipients=[Params.ERROR_RECIPIENT_EMAIL])
        msg.body = f'''Feedback recibido:

        Page: {page}

        Detail: {text}

        '''
        mail.send(msg)
    except Exception as e:
        logger.error("feedback_notifier: {}".format(page))


def send_email_notification(subject, body, mail, logger):
    # Send email
    try:
        msg = Message('App UPDATE - {}'.format(subject),
                      sender=Params.SENDER_EMAIL,
                      recipients=[Params.ERROR_RECIPIENT_EMAIL])
        if body == "":
            body = "(Empty body)"
        msg.body = body
        mail.send(msg)
    except Exception as e:
        logger.error("send_email_notification: {}".format(e))


def warning_notifier(topic, args_dic, mail, logger):
    # Send email
    try:
        msg = Message('App WARNING - {}'.format(topic),
                      sender=Params.SENDER_EMAIL,
                      recipients=[Params.ERROR_RECIPIENT_EMAIL])
        message = "Warning:\n\nTopic: {}\n\n".format(topic)
        for arg in args_dic.keys():
            message += "{}: {}\n".format(arg, args_dic[arg])
        msg.body = message
        mail.send(msg)
    except Exception as e:
        logger.error("warning_notifier: {}".format(topic))


def generate_file_path(relative_path, keyword):
    """Creates a filename that contains the provided 'keyword', plus the
    current time and some random characters.
    Returns the complete project path of the generated file.
    """
    now = datetime.datetime.now()
    now_str = now.strftime('%Y%m%d_%H%M%S')
    random_hex = token_hex(4)
    random_fn = keyword + '_' + now_str + '_' + random_hex + ".txt"
    dest_file = os.path.join(app.root_path, relative_path, random_fn)
    return dest_file


def generate_paths_file(paths, currency, logger):
    dest_file = generate_file_path('static/results', 'paths')
    with open(dest_file, 'w') as paths_file:
        # Header
        paths_file.write('PathID;PathType;Origin;Orig_Coin;Orig_Amount;'
                         'WithdrawFee;Connection (1);In_Amount (1);'
                         'In_Coin (1);TradeFee (1);'
                         'TradeFeeCoin (1);Out_Amount (1);Out_Coin (1);'
                         'WithdrawFee (1);TradeVolume(1);Connection (2);'
                         'In_Amount (2);In_Coin (2);TradeFee (2);'
                         'TradeFeeCoin (2);Out_Amount (2);Out_Coin (2);'
                         'WithdrawFee (2);TradeVolume (2);Destination (2);'
                         'Dest_Amount;Dest_Coin (2);total_fees\n')
        for path in paths:
            # Handle result depending on Origin Withdraw fee
            if path.origin.withdraw_fee:
                origin_withdraw_fee = path.origin.withdraw_fee
            else:
                origin_withdraw_fee = "-"
            # Handle result depending on Hop 2
            if path.hop_2:
                hop2_exchange = path.hop_2.exchange.id
                hop2_trade_sell_amt = path.hop_2.trade.sell_amt
                hop2_trade_sell_coin = path.hop_2.trade.sell_coin.symbol
                hop2_trade_fee_amt = path.hop_2.trade.fee_amt
                hop2_trade_fee_coin = path.hop_2.trade.fee_coin.symbol
                hop2_trade_buy_amt = path.hop_2.trade.buy_amt
                hop2_trade_buy_coin = path.hop_2.trade.buy_coin.symbol
                hop2_withdraw_fee = path.hop_2.withdraw_fee
                hop2_volume = path.hop_2.volume
            else:
                hop2_exchange = "-"
                hop2_trade_sell_amt = "-"
                hop2_trade_sell_coin = "-"
                hop2_trade_fee_amt = "-"
                hop2_trade_fee_coin = "-"
                hop2_trade_buy_amt = "-"
                hop2_trade_buy_coin = "-"
                hop2_withdraw_fee = "-"
                hop2_volume = "-"
            line = ("{};{};{};{};{};{};{};{};{};{};{};{};{};{};"
                    "{};{};{};{};{};{};{};{};{};{};{};{};{};{}\n"
                    "").format(path.id,
                               path.type,
                               path.origin.exchange.id,
                               path.origin.amount,
                               path.origin.coin.symbol,
                               origin_withdraw_fee,
                               path.hop_1.exchange.id,
                               path.hop_1.trade.sell_amt,
                               path.hop_1.trade.sell_coin.symbol,
                               path.hop_1.trade.fee_amt,
                               path.hop_1.trade.fee_coin.symbol,
                               path.hop_1.trade.buy_amt,
                               path.hop_1.trade.buy_coin.symbol,
                               path.hop_1.withdraw_fee,
                               path.hop_1.volume,
                               hop2_exchange,
                               hop2_trade_sell_amt,
                               hop2_trade_sell_coin,
                               hop2_trade_fee_amt,
                               hop2_trade_fee_coin,
                               hop2_trade_buy_amt,
                               hop2_trade_buy_coin,
                               hop2_withdraw_fee,
                               hop2_volume,
                               path.destination.exchange.id,
                               path.destination.amount,
                               path.destination.coin.symbol,
                               path.total_fees)
            paths_file.write(line)


def num_2_str(number, currency):
    """Formats 'number' so that it has the appropriate number of decs
    depending on the amount of 'number'
    """
    try:
        symbol = Params.CURRENCY_SYMBOLS[currency]
    except Exception as e:
        symbol = '?'
    decs = 0
    format = "in_units"
    try:
        if number < 100:
            decs = 2
        elif number < 1000:
            decs = 1
        elif number < 10000:
            decs = 0
        elif number < 100000:
            number = number / 1000
            decs = 2
            format = "in_thousands"
        elif number < 1000000:
            number = number / 1000
            decs = 1
            format = "in_thousands"
        else:
            number = number / 1000
            decs = 0
            format = "in_thousands"
        if currency == 'USD':
            if format == "in_units":
                return "{}{:20,.{}f}".format(symbol, number, decs)
            else:
                return "{}{:20,.{}f}k".format(symbol, number, decs)
        else:
            if format == "in_units":
                return "{:20,.{}f} {}".format(number, decs, symbol)
            else:
                return "{:20,.{}f} k{}".format(number, decs, symbol)
    except ValueError as e:
        return number
    except TypeError as e:
        return number


def resize_image(input_image_path, output_image_path, size):
    original_image = Image.open(input_image_path)
    img_size = (size, size)
    original_image.thumbnail(img_size, Image.ANTIALIAS)
    original_image.save(output_image_path)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    except TypeError:
        return False


def float_to_str(f):
    """Converts a float to string solving the problem with
    scientific notation for very small numbers.
    """
    float_string = repr(f)
    if 'e' in float_string:  # detect scientific notation
        digits, exp = float_string.split('e')
        digits = digits.replace('.', '').replace('-', '')
        exp = int(exp)
        # minus 1 for decimal point in the sci notation
        zero_padding = '0' * (abs(int(exp)) - 1)
        sign = '-' if f < 0 else ''
        if exp > 0:
            float_string = '{}{}{}.0'.format(sign, digits, zero_padding)
        else:
            float_string = '{}0.{}{}'.format(sign, zero_padding, digits)
    return float_string


def round_amount_by_price(amount, coin):
    """Returns a rounded amount in FLOAT format that depends
    on the valuation of the coin.
    """
    if amount is None:
        return None
    if coin in Params.FIAT_COINS:
        try:
            decs = Params.STEPS_DECIMAL_POS[coin]
            return round(amount, decs)
        except Exception as e:
            return amount
    else:
        price = Price.query.filter_by(coin=coin, base_coin='USD').first()
        if price:
            price = price.price
            if price > 10000:
                decs = 7
            elif price > 1000:
                decs = 6
            elif price > 100:
                decs = 5
            elif price > 10:
                decs = 4
            elif price > 1:
                decs = 3
            elif price > 0.1:
                decs = 2
            elif price > 0.01:
                decs = 2
            elif price > 0.001:
                decs = 1
            else:
                decs = 0
            return round(amount, decs)
        return amount


def round_amount_by_price_str(amount, coin):
    """Returns a rounded amount in STRING format that depends
    on the valuation of the coin.
    """
    if amount is None:
        return "-"
    if coin.symbol in Params.FIAT_COINS:
        try:
            decs = Params.STEPS_DECIMAL_POS[coin]
            return round(amount, decs)
        except Exception as e:
            return amount
    else:
        price = Price.query.filter_by(coin=coin.id,
                                      base_coin='eur-euro').first()
        if price:
            price = price.price
            if price > 10000:
                decs = 7
            elif price > 1000:
                decs = 6
            elif price > 100:
                decs = 5
            elif price > 10:
                decs = 4
            elif price > 1:
                decs = 3
            elif price > 0.1:
                decs = 2
            elif price > 0.01:
                decs = 2
            elif price > 0.001:
                decs = 1
            else:
                decs = 0
            return "{:20,.{}f}".format(round(amount, decs), decs)
        return amount


def round_amount(number, decs=None):
    """Returns a rounded amount depending on the valuation of the coin.
    """
    if number is None:
        return None
    if decs is None:
        if number > 10000:
            decs = 1
        elif number > 1000:
            decs = 2
        elif number > 100:
            decs = 3
        elif number > 10:
            decs = 4
        elif number > 1:
            decs = 5
        else:
            decs = 8
    try:
        return "{:20,.{}f}".format(number, decs)
    except ValueError as e:
        return number
    except TypeError as e:
        return number


def str_2_float(str_number):
    """Converts a String in a float number.
    Solves the problem when casting a string with commas.
    """
    if str_number is None:
        return None
    str_number = str_number.replace(",", "")
    str_number = str_number.replace(" ", "")
    return float(str_number)


def get_meta_tags(page, tag, args=[]):
    """Returns the tag 'tag' for the page 'page'.
    The arg argument fills variables in the tag string.
    """
    meta_tags = Params.META_TAGS
    tag = meta_tags[page][tag]
    if args:
        return tag.format(*args)
    else:
        return tag


def get_exch_text(exchange, fee, args=[]):
    """Returns the text 'tag' for the page 'page'.
    The arg argument fills variables in the tag string.
    """
    texts = Params.FEE_EXCH_TEXTS
    try:
        text = texts[exchange][fee]
    except KeyError as e:
        return texts['Generic'][fee]
    if args:
        return text.format(*args)
    else:
        return text


def generate_sitemap_url(logger, coins_file):
    url = "https://www.cryptofeesaver.com/exchanges/search/"
    # Read file
    try:
        with open(coins_file, "r", encoding='utf-8') as f:
            f_contents = f.readlines()
    except Exception as e:
        logger.error("update_prices: Could not read '{}'".format(coins_file))
        return 1
    # Store prices in DB
    for coinA in f_contents:
        for coinB in f_contents:
            if coinA == coinB:
                continue
            print("{}{}-to-{}".format(url,
                                      coinA.replace("\n", ""),
                                      coinB.replace("\n", "")))
    return


def load_json_file(file, logger):
    file_info = {}
    try:
        with open(file) as f:
            file_info = json.load(f)
    except Exception as e:
        logger.error("routes: Could not read '{}'".format(file))
    return file_info


def get_exchange_data(id, exchange_info_file, logger):
    """Gets the Exchange information retrieved from Coinpaprika
    for the exchange with 'id'.
    """
    exch_data = None
    if id:
        try:
            exch_data = exchange_info_file[id]
        except KeyError as e:
            logger.warning("routes: No exchange info found for '{}'"
                           "".format(id))
    # Format Adjusted Volume
    if exch_data["quotes"]["USD"]["adjusted_volume_24h"]:
        no_formatted = exch_data["quotes"]["USD"]["adjusted_volume_24h"]
        formatted = num_2_str(no_formatted, 'usd-us-dollars')
        exch_data["quotes"]["USD"]["adjusted_volume_24h"] = formatted
    # Format Reported Volume
    if exch_data["quotes"]["USD"]["reported_volume_24h"]:
        no_formatted = exch_data["quotes"]["USD"]["reported_volume_24h"]
        formatted = num_2_str(no_formatted, 'usd-us-dollars')
        exch_data["quotes"]["USD"]["reported_volume_24h"] = formatted
    return exch_data


def get_coin_data(id,
                  coin_info_file,
                  people_info_file,
                  tag_info_file,
                  logger):
    """Gets, mixes and cleans the coin information retrieved from Coinpaprika
    for the coin with 'id'.
    """
    coin_data = None
    if id:
        try:
            coin_data = coin_info_file[id]
        except KeyError as e:
            logger.warning("routes: No coin info found for '{}'"
                           "".format(id))
    if coin_data:
        # For each team member, add its description and links
        try:
            # Check if 'team' is a list
            if not isinstance(coin_data["team"], list):
                coin_data["team"] = []
            # Loop for each person in the list
            for index, person in enumerate(coin_data["team"]):
                person_id = person["id"]
                # Fetch info from people
                person_descr = None
                person_links = {}
                try:
                    person_links = people_info_file[person_id]["links"]
                    person_descr = people_info_file[person_id]["description"]
                except KeyError as e:
                    logger.debug("routes: Could not fetch info"
                                 " for person_id='{}'".format(person_id))
                coin_data["team"][index]["description"] = person_descr
                coin_data["team"][index]["links"] = person_links
        except KeyError as e:
            logger.warning("routes: NCould not gather team for coin '{}'"
                           "".format(coin_data["symbol"]))
        # For each tag, add its description
        try:
            # Check if 'tags' is a list
            if not isinstance(coin_data["tags"], list):
                coin_data["tags"] = []
            # Loop for each tag in the list
            for index, tag in enumerate(coin_data["tags"]):
                tag_id = tag["id"]
                # Fetch info from people
                tag_descr = None
                try:
                    tag_descr = tag_info_file[tag_id]["description"]
                except KeyError as e:
                    logger.info("routes: Could not fetch info"
                                " for tag_id='{}'".format(tag_id))
                coin_data["tags"][index]["description"] = tag_descr
        except KeyError as e:
            logger.warning("routes: NCould not gather tags for coin '{}'"
                           "".format(coin_data["symbol"]))
        # Format date ('started_at')
        if 'started_at' in coin_data:
            raw_date = coin_data['started_at']
            if raw_date:
                formated_date = raw_date.replace("T00:00:00Z", "")
                coin_data['started_at'] = formated_date
            else:
                coin_data['started_at'] = 'n/a'
        else:
            coin_data['started_at'] = 'n/a'
        # Format Development status
        if 'development_status' not in coin_data:
            coin_data['development_status'] = 'n/a'
        # Format Whitepaper status
        if 'whitepaper' not in coin_data:
            coin_data['whitepaper']['link'] = 'n/a'
        # Format Org.structure status
        if 'org_structure' not in coin_data:
            coin_data['org_structure'] = 'n/a'
        # Format Open Source status
        if 'open_source' in coin_data:
            if coin_data['open_source'] is True:
                coin_data['open_source'] = 'Yes'
            else:
                coin_data['open_source'] = 'No'
        else:
            coin_data['open_source'] = 'n/a'
        # Format HD Wallet status
        if 'hardware_wallet' in coin_data:
            if coin_data['hardware_wallet'] is True:
                coin_data['hardware_wallet'] = 'Yes'
            else:
                coin_data['hardware_wallet'] = 'No'
        else:
            coin_data['hardware_wallet'] = 'n/a'
        # Format Consensus Type status
        if 'proof_type' not in coin_data:
            coin_data['proof_type'] = 'n/a'
        # Format Hash Algo status
        if 'hash_algorithm' not in coin_data:
            coin_data['hash_algorithm'] = 'n/a'
        # Format Links
        if (('links' not in coin_data) or
                (not isinstance(coin_data['links'], dict))):
            coin_data['links'] = None
        else:
            counter = 0
            links = coin_data['links']
            if 'explorer' not in links:
                coin_data['links']['explorer'] = None
                counter += 1
            if 'reddit' not in links:
                coin_data['links']['reddit'] = None
                counter += 1
            if 'source_code' not in links:
                coin_data['links']['source_code'] = None
                counter += 1
            if 'website' not in links:
                coin_data['links']['website'] = None
                counter += 1
            if 'facebook' not in links:
                coin_data['links']['facebook'] = None
                counter += 1
            if 'youtube' not in links:
                coin_data['links']['youtube'] = None
                counter += 1
            else:
                # Format youtube link to embed it
                if isinstance(coin_data['links']['youtube'], list):
                    init_link = coin_data['links']['youtube'][0]
                    # If not embed format, create it
                    if init_link.find("embed") == -1:
                        # If Youtube short format, add 'v='
                        if init_link.find(".be/") > -1:
                            init_link = init_link.replace(".be/", ".be/v=")
                        # Find video ID delimited by 'v=' and '&'
                        init_pos = init_link.find("v=")
                        if init_pos > -1:
                            video_id = init_link[init_pos+2:]
                            end_pos = video_id.find("&")
                            if end_pos > -1:
                                video_id = video_id[:end_pos]
                            new_link = "https://www.youtube.com/embed/"\
                                + video_id
                            coin_data['links']['youtube'][0] = new_link
                        else:
                            coin_data['links']['youtube'] = None
                else:
                    coin_data['links']['youtube'] = None
            # If no links, change no None object
            if counter == 6:
                coin_data['links'] = None
    return coin_data
