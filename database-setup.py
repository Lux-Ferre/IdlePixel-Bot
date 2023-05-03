import sqlite3
import json
import base64


def add_row_to_database(key, value):
    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    query = "INSERT INTO configs VALUES (?, ?)"
    params = (key, encoded_string)

    cur.execute(query, params)

    con.commit()


def read_all_data():
    res = cur.execute("SELECT config, data from configs")
    encoded_configs = res.fetchall()
    loaded_configs = {}

    for config in encoded_configs:
        key = config[0]
        encoded_value = config[1]

        if isinstance(encoded_value, str):
            decoded_value = encoded_value
        else:
            decoded_value = json.loads(base64.b64decode(encoded_value))

        loaded_configs[key] = decoded_value

    return loaded_configs


if __name__ == "__main__":
    """
    config, data
    "whitelisted_accounts", ["lux", "axe", "luxferre", "luxchatter", "godofnades", "amyjane1991"]
    "ignore_accounts", ["flymanry"]
    "nadebot_commands", ["!bigbone", "!combat", "!dhm", "!dho", "!event", "!rocket", "!wiki", "!xp", "!help"]
    "automod_flag_words", ["nigger", "nigga", "niga", "fag", "chink", "beaner", ]
    "nadebot_reply", "Nades's  bot is offline atm."
    """
    con = sqlite3.connect("configs.db")
    cur = con.cursor()

    print(read_all_data())
