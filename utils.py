import sqlite3
import json
import requests
import os
from threading import Timer


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


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
    def read_config_row(key: str) -> dict:
        query = "SELECT data FROM configs WHERE config=?"
        params = (key,)

        config_json = Db.fetch_db(query, params, False)[0]
        config_dict = json.loads(config_json)

        return config_dict

    @staticmethod
    def set_config_row(key: str, value: dict):
        query = "UPDATE configs SET data=? WHERE config=?"

        stringified_value = json.dumps(value)

        params = (stringified_value, key)

        Db.set_db(query, params)

    @staticmethod
    def add_pet(ws, pet_data: tuple, player: str):
        query = "INSERT INTO pet_links VALUES (?, ?, ?)"

        try:
            Db.set_db(query, pet_data)
        except sqlite3.IntegrityError as e:
            print(e)
            Utils.send_custom_message(ws, player, f"LuxBot:add_pet:Link not added, '{pet_data[0]}' already exists.")

    @staticmethod
    def update_permission(ws, player: str, updated_player: str, level: str):
        level = int(level)

        if not -2 <= level <= 3:
            Utils.send_custom_message(ws, player, "LuxBot:update_permission:Invalid permission level. Must be between -2 and 3.")
            return

        query = """
                    INSERT INTO permissions(user, level) VALUES(?1, ?2)
                    ON CONFLICT(user) DO UPDATE SET level=?2
                """
        params = (updated_player, level)
        Db.set_db(query, params)

        #   Utils.send_custom_message(ws, player, f"LuxBot:update_permission:{updated_player} permission level set to {level}.")


class Utils:
    @staticmethod
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

    @staticmethod
    def send_custom_message(ws, player: str, content: str, callback_id: str = "IPP0"):
        custom_string = f"CUSTOM={player}~{callback_id}:{content}"
        ws.send(f"{custom_string}")

    @staticmethod
    def mute_player(ws, player: str, length: str, reason: str, is_ip: str):
        # websocket.send("MUTE=" + username_target + "~" + hours + "~" + reason + "~" + is_ip);
        mute_string = f"MUTE={player}~{length}~{reason}~{is_ip}"
        ws.send(f"{mute_string}")

    @staticmethod
    def send_generic(ws, command: str):
        ws.send(command)

    @staticmethod
    def permission_level(player: str):
        query = "SELECT level FROM permissions WHERE user=?"
        params = (player,)

        level = Db.fetch_db(query, params, False)
        if level is None:
            return 0
        else:
            return level[0]

    @staticmethod
    def parse_item_data(raw_data: str):
        item_data = {}
        split_data = raw_data.split("~")

        for i in range(0, len(split_data), 2):
            item_data[split_data[i]] = split_data[i + 1]

        return item_data
