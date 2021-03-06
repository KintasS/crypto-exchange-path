""" ***********************************************************************
***************************************************************************
PRICE MANAGING FUNCTIONS
***************************************************************************
*********************************************************************** """

"""Dictionary where FX prices will be stored.
"""
fx_dictionary = {}


def reset_fx():
    """Resets the dictionary of FX. To be called whenever the 'update_prices'
    function is called.
    """
    global fx_dictionary
    fx_dictionary = {}


def set_fx(coin, base_coin, fx):
    """Adds a new FX to the FX dictionary.
    """
    global fx_dictionary
    if coin not in fx_dictionary.keys():
        fx_dictionary[coin] = {}
    fx_dictionary[coin][base_coin] = fx


def get_fx(coin, base_coin):
    """Gets a FX from the FX dictionary.
    """
    try:
        return fx_dictionary[coin][base_coin]
    except KeyError as e:
        return None
