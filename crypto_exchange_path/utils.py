import os
import logging
import datetime
from secrets import token_hex
from PIL import Image
from crypto_exchange_path import app
from crypto_exchange_path.config import Params


def set_logger(logger_name, level="INFO"):
    """Sets logging configuration.
    """
    # Set-up logger in both file
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
    dt_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler("logs/{}_{}.log".format(logger_name,
                                                               dt_str))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Set-up looger in console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # Return logger to allow it to be called from outside
    return logger


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


def num_2_str(number, currency, decs=None):
    """Formats 'number' so that it has 'decs' number of decimal places,
    and the symbol corresponding to 'currency'
    """
    try:
        symbol = Params.CURRENCY_SYMBOLS[currency]
    except Exception as e:
        symbol = '?'
    if decs is None:
        try:
            decs = Params.TOTAL_DECIMAL_POS[currency]
        except Exception as e:
            decs = 2
    try:
        if currency == 'USD':
            return "{}{:20,.{}f}".format(symbol, number, decs)
        else:
            return "{:20,.{}f} {}".format(number, decs, symbol)
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
