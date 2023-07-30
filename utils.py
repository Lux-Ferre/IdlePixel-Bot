import sqlite3
import json
import base64
import requests
import os
from threading import Timer


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Interactor:
    @staticmethod
    def get_help_string(command: str) -> str:
        if command == "echo":
            help_string = "Echos message as custom. (echo:message)"
        elif command == "chatecho":
            help_string = "Echos message into chat. (chatecho:message)"
        elif command == "relay":
            help_string = "Passes on message to another account. (relay:account:message)"
        elif command == "togglenadebotreply":
            help_string = "Toggles bot responses to Nadess bot commands."
        elif command == "nadesreply":
            help_string = "Sets a new reply string for Nadess bot commands. (nadesreply:reply_string)"
        elif command == "triggers":
            help_string = f"Add/remove automod triggers. (triggers:add/remove;trigger)"
        elif command == "speak":
            help_string = "Relays text to chat as the bot. (speak:content)"
        elif command == "mute":
            help_string = "Mutes target player. (mute:player;reason;length;is_ip)"
        elif command == "pets":
            help_string = "Interacts with the pets database. (pets:add/remove;pet;title;link)"
        elif command == "permissions":
            help_string = "Modifies player permissions. (permissions:player:level)"
        elif command == "help":
            help_string = "Lists commands or gives a description of a command. (help:command)"
        elif command == "generic":
            help_string = "Relays content as a websocket frame."
        else:
            help_string = "Invalid help command. Should be of format (help:command)"

        return help_string


class Db:
    @staticmethod
    def fetch_db(query: str, params: tuple, many: bool):
        con = sqlite3.connect("configs.db")
        cur = con.cursor()

        if params:
            res = cur.execute(query, params)
        else:
            res = cur.execute(query)

        if many:
            data = res.fetchall()
        else:
            data = res.fetchone()

        return data

    @staticmethod
    def set_db(query: str, params: tuple):
        con = sqlite3.connect("configs.db")
        cur = con.cursor()

        cur.execute(query, params)

        con.commit()

    @staticmethod
    def get_pet_links(pet: str):
        query = "SELECT title, link from pet_links WHERE pet=?"
        params = (pet,)

        all_links = Db.fetch_db(query, params, True)
        loaded_links = {}

        for pet in all_links:
            title = pet[0]
            link = pet[1]

            loaded_links[title] = link

        return loaded_links

    @staticmethod
    def read_config_row(key: str) -> list | str | dict:
        query = "SELECT data FROM configs WHERE config=?"
        params = (key,)

        encoded_config = Db.fetch_db(query, params, False)[0]
        decoded_config = json.loads(base64.b64decode(encoded_config))

        return decoded_config

    @staticmethod
    def set_config_row(key: str, value: str | list):
        query = "UPDATE configs SET data=? WHERE config=?"

        stringified_value = json.dumps(value)
        encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

        params = (encoded_string, key)

        Db.set_db(query, params)


def dump_to_pastebin(paste_string: str, expiry: str) -> str:
    api_key = os.environ["PASTEBIN_API_KEY"]
    url = "https://pastebin.com/api/api_post.php"
    data = {
        "api_dev_key": api_key,
        "api_option": "paste",
        "api_paste_code": paste_string,
        "api_paste_expire_date": expiry
    }

    response = requests.post(url=url, data=data)

    return response.text
