import sqlite3
import json
import base64


def add_config_to_database(key: str, value: str | list):
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


def read_table(table: str):
    query = f"SELECT * FROM {table}"
    res = cur.execute(query)
    return res.fetchall()


def permission_level(player: str):
    query = "SELECT level FROM permissions WHERE user=?"
    params = (player, )

    res = cur.execute(query, params)
    level = res.fetchone()
    if level is None:
        return None
    else:
        return level[0]


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
    con = sqlite3.connect("configs.db")
    cur = con.cursor()

    # cur.execute("CREATE TABLE pet_links(title, pet, link)")
    # cur.execute("ALTER TABLE pet_links RENAME TO old_pet_links")
    # cur.execute("CREATE TABLE permissions(user UNIQUE, level)")
    # con.commit()

    print(read_table("permissions"))


