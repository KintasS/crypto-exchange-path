from urllib.request import urlopen


try:
    # urlopen("http://192.168.1.137:5000/update/slfjh23hk353mh4567df")
    urlopen("https://www.cryptofeesaver.com/update/prices_slfjh23hk353mh4567df")
except Exception as e:
    print("KO - Error opening link")
