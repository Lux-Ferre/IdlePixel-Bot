import sqlite3
import json


def add_config_to_database(key: str, value: dict):
    stringified_value = json.dumps(value)

    query = "INSERT INTO configs VALUES (?, ?)"
    params = (key, stringified_value)

    cur.execute(query, params)

    con.commit()


def read_all_configs():
    res = cur.execute("SELECT config, data from configs")
    config_list = res.fetchall()
    loaded_configs = {}

    for config in config_list:
        key = config[0]
        value = json.loads(config[1])

        loaded_configs[key] = value

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


def set_config_row(key: str, value: dict):
    query = "UPDATE configs SET data=? WHERE config=?"

    stringified_value = json.dumps(value)

    params = (stringified_value, key)
    cur.execute(query, params)

    con.commit()


def remove_config_row(key: str):
    query = "DELETE FROM configs WHERE config=?"

    params = (key, )
    cur.execute(query, params)

    con.commit()


if __name__ == "__main__":
    con = sqlite3.connect("configs.db")
    cur = con.cursor()

    # cur.execute("CREATE TABLE pet_links(title, pet, link)")
    # cur.execute("ALTER TABLE pet_links RENAME TO old_pet_links")
    # cur.execute("CREATE TABLE permissions(user UNIQUE, level)")
    # con.commit()

    chat_stats = {'start_date': '06/08/23',
                  'amy_noobs': 0,
                  'amy_sucks': 0,
                  'total_messages': 0,
                  'amy_total': 0,
                  'botofnades_requests': 0,
                  'luxbot_requests': 0,
                  'total_yells': 0,
                  'diamonds_found': 0,
                  'sigils_found': 0,
                  'blood_diamonds_found': 0,
                  'gem_goblin_encounters': 0,
                  'blood_goblin_encounters': 0,
                  "elite_achievements": 0,
                  "max_levels": 0
                  }

    print(read_all_configs())
