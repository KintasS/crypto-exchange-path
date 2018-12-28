from urllib.request import urlopen


try:
    # urlopen("http://192.168.1.137:5000/update/slfjh23hk353mh4567df")
    urlopen("https://www.cryptofeesaver.com/get/"
            "tag_info_uoruyrweqryqzmcxvnds", timeout=3600)
except Exception as e:
    print("KO - Error opening link")
