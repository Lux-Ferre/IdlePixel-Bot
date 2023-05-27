import sqlite3
import json
import base64


def add_row_to_database(key: str, value: str | list):
    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    query = "INSERT INTO configs VALUES (?, ?)"
    params = (key, encoded_string)

    cur.execute(query, params)

    con.commit()


def read_all_configs():
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


def read_all_pets():
    res = cur.execute("SELECT title, pet, link from pet_links")
    all_links = res.fetchall()
    loaded_pets = []

    for data_point in all_links:
        title = data_point[0]
        pet = data_point[1]
        link = data_point[2]

        loaded_pets.append((title, pet, link))

    return loaded_pets


def get_pet_links(pet: str):
    query = "SELECT title, link from pet_links WHERE pet=?"
    params = (pet,)
    res = cur.execute(query, params)

    all_links = res.fetchall()
    loaded_links = {}

    for pet in all_links:
        title = pet[0]
        link = pet[1]

        loaded_links[title] = link

    return loaded_links


def set_config_row(key: str, value: str | list):
    query = "UPDATE configs SET data=? WHERE config=?"

    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    params = (encoded_string, key)
    cur.execute(query, params)

    con.commit()


if __name__ == "__main__":
    """
    config, data
    "whitelisted_accounts", ["lux", "axe", "luxferre", "luxchatter", "godofnades", "amyjane1991"]
    "ignore_accounts", ["flymanry"]
    "nadebot_commands", ["!bigbone", "!combat", "!dhm", "!dho", "!event", "!rocket", "!wiki", "!xp", "!help"]
    "automod_flag_words", ["nigger", "nigga", "niga", "fag", "chink", "beaner", ]
    "nadebot_reply", "Nades's bot is offline atm."
    """
    con = sqlite3.connect("configs.db")
    cur = con.cursor()

    data = [
        ('santa', 'vega', 'https://prnt.sc/iLEELtvirILy'),
        ('paper', 'vega', 'https://prnt.sc/5Ga3Tsl0oay6'),
        ('face', 'vega', 'https://prnt.sc/WbVMwBw63d9g'),
        ('attack', 'vega', 'https://prnt.sc/dASKN1prvBJ9'),
        ('kitten', 'vega', 'https://prnt.sc/rp_t4eiSGM1h'),
        ('hide', 'vega', 'https://prnt.sc/aPvMRNNkbbEE'),
        ('beans', 'vega', 'https://prnt.sc/_XCgGFh3jIbv'),
        ('borgor', 'vega', 'https://prnt.sc/HwewSCtGlJvM'),
        ('banana', 'vega', 'https://prnt.sc/pSs3rVcPlfHE'),
        ('gamer', 'vega', 'https://prnt.sc/yEQaV346hY7c'),
        ('peer', 'vega', 'https://prnt.sc/LgPFXqfyk3Gi'),
        ('axolotl', 'vega', 'https://prnt.sc/ev3f_BkI6CsN'),
        ('noodle', 'vega', 'https://prnt.sc/TTYHSPbazWbJ'),
        ('reader', 'vega', 'https://prnt.sc/N3oVzhnb3N80'),
        ('shutout', 'vega', 'https://prnt.sc/i06Ff5mifQNC'),
        ('pupper', 'bear', 'https://prnt.sc/Cn1tKIrvZwOM'),
        ('derp', 'bear', 'https://prnt.sc/5gbSLOCE99cn'),
        ('jenga', 'bear', 'https://prnt.sc/5zEvSclW9BIQ'),
        ('vega', 'bear', 'https://prnt.sc/6Dtm8MSFaUEg'),
        ('eepy', 'bear', 'https://prnt.sc/1u3qqxLhJXtO'),
        ('pint', 'bear', 'https://prnt.sc/I9tS6s5bICce'),
        ('water', 'bear', 'https://prnt.sc/5g1Ib9zxEv9Y'),
        ('teef', 'bear', 'https://prnt.sc/7g-tIATxEK7V'),
        ('happy', 'bear', 'https://prnt.sc/iSGQbrOSQOh7'),
        ('fennec', 'bear', 'https://prnt.sc/4yrevw1wODQc'),
        ('splish', 'bear', 'https://prnt.sc/aGvFjCjPhPkk'),
        ('uwot', 'bear', 'https://prnt.sc/ieU9eHGMqwKj'),
    ]

    # cur.executemany("INSERT INTO pet_links VALUES(?, ?, ?)", data)
    # con.commit()
    # cur.execute("CREATE TABLE pet_links(title, pet, link)")
    # cur.execute("ALTER TABLE pet_links RENAME TO old_pet_links")

    print(get_pet_links("bobo"))

    cur.execute("INSERT INTO pet_links SELECT * FROM old_pet_links")

    con.commit()

    print(get_pet_links("bobo"))
