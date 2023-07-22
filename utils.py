import sqlite3
from threading import Timer


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Chat:
    @staticmethod
    def splitter(raw_message: str):
        raw_split = raw_message.split("~")
        player = {
            "username": raw_split[0],
            "sigil": raw_split[1],
            "tag": raw_split[2],
            "level": raw_split[3],
        }
        message = raw_split[4]

        return player, message


class Interactor:
    @staticmethod
    def get_help_string(command: str):
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
