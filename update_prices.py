from urllib.request import urlopen
# from crypto_exchange_path.utils import set_logger
# from crypto_exchange_path.info_fetcher import update_prices


try:
    # urlopen("http://192.168.1.137:5000/update/slfjh23hk353mh4567df")
    urlopen("https://www.cryptofeesaver.com/update/prices_slfjh23hk353mh4567df")
    print("ok")
except Exception as e:
    print("KO - Error opening link")
