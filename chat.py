import random

from utils import Db, Utils


class Chat:
    @staticmethod
    def splitter(raw_message: str) -> tuple[dict, str]:
        raw_split = raw_message.split("~")
        player = {
            "username": raw_split[0],
            "sigil": raw_split[1],
            "tag": raw_split[2],
            "level": raw_split[3],
        }
        message = raw_split[4]

        return player, message

    @staticmethod
    def generate_command(raw_message: str) -> dict:
        split_message = raw_message.lower().split(" ", 1)
        full_command = split_message[0]
        split_command = full_command.split(":", 1)
        primary_command = split_command[0]
        if len(split_command) > 1:
            sub_command = split_command[1]
        else:
            sub_command = None
        if len(split_message) > 1:
            payload = split_message[1]
        else:
            payload = None

        command = {
            "command": primary_command,
            "sub_command": sub_command,
            "payload": payload,
        }

        return command

    @staticmethod
    def send_chat_message(ws, chat_string: str):
        chat_string = chat_string.replace("richie19942", "Bawbag")
        chat_string = f"CHAT={chat_string}"
        ws.send(chat_string)

    @staticmethod
    def dispatcher(ws, player: dict, command: dict):
        dispatch = {
            "echo": Chat.echo,
            "combat": Chat.combat,
            "dho_maps": Chat.dho_maps,
            "scripts": Chat.scripts,
            "vega": Chat.vega,
            "wiki": Chat.wiki,
            "bear": Chat.bear,
            "pet": Chat.pet,
            "pet_stats": Chat.pet_stats,
            "amy_noobs": Chat.amy_noobs,
            "quote": Chat.quote,
            "import": Chat.import_command,
        }

        dispatch[command["sub_command"]](ws, player, command)

    @staticmethod
    def echo(ws, player: dict, command: dict):
        reply_string = f"Echo: {player['username']}: {command['payload']}"
        Chat.send_chat_message(ws, reply_string)
        
    @staticmethod
    def combat(ws, player: dict, command: dict):
        reply_string = f"https://idle-pixel.wiki/index.php/Combat_Guide"
        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def dho_maps(ws, player: dict, command: dict):
        reply_string = f"Offline map solutions: https://prnt.sc/Mdd-AKMIHfLz"
        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def scripts(ws, player: dict, command: dict):
        reply_string = f"https://idle-pixel.wiki/index.php/Scripts"
        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def vega(ws, player: dict, command: dict):
        vega_links = Db.get_pet_links("vega")
        if command["payload"] is not None:
            try:
                reply_string = vega_links[command["payload"]]
            except KeyError:
                reply_string = "Invalid Vega."
        else:
            random_vega = random.choice(list(vega_links))
            reply_string = f"Your random Vega is: {random_vega}: {vega_links[random_vega]}"

        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def wiki(ws, player: dict, command: dict):
        if command['payload'] is not None:
            reply_string = f"Wiki page for {command['payload']}: https://idle-pixel.wiki/index.php/{command['payload'].capitalize()}"
        else:
            reply_string = f"Wiki home page: https://idle-pixel.wiki/index.php/Main_Page"

        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def bear(ws, player: dict, command: dict):
        bear_links = Db.get_pet_links("bear")
        if command['payload'] is not None:
            try:
                reply_string = bear_links[command['payload']]
            except KeyError:
                reply_string = "Invalid Bear."
        else:
            random_bear = random.choice(list(bear_links))
            reply_string = f"Your random Bear is: {random_bear}: {bear_links[random_bear]}"

        if player['username'] == "richie19942":
            reply_string = "Bawbag, " + reply_string

        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def pet(ws, player: dict, command: dict):
        if command['payload'] is not None:
            query = "SELECT title, pet, link FROM pet_links WHERE pet=? ORDER BY RANDOM() LIMIT 1;"
            params = (command['payload'],)
        else:
            query = "SELECT title, pet, link FROM pet_links ORDER BY RANDOM() LIMIT 1;"
            params = tuple()

        pet_link = Db.fetch_db(query, params, False)

        if pet_link is None:
            reply_string = f"Sorry {player['username'].capitalize()}, that is an invalid pet name."
        else:
            reply_string = f"Your random pet is {pet_link[1].capitalize()}! {pet_link[0].capitalize()}: {pet_link[2]}"

        if player['username'] == "richie19942":
            reply_string = "Bawbag, " + reply_string

        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def pet_stats(ws, player: dict, command: dict):
        query = "SELECT pet, GROUP_CONCAT(title) FROM pet_links GROUP BY pet"
        params = tuple()
        all_stats = Db.fetch_db(query, params, True)

        output_string = ""

        for stat in all_stats:
            pet, title_string = stat
            titles = title_string.split(",")
            title_count = len(titles)
            output_string += f"{pet.capitalize()}({title_count}):\n"
            for title in titles:
                output_string += f"\t{title.capitalize()}\n"

        pastebin_url = Utils.dump_to_pastebin(output_string, "10M")

        Chat.send_chat_message(ws, pastebin_url)

    @staticmethod
    def amy_noobs(ws, player: dict, command: dict):
        counter = Db.read_config_row("amy_noobs")
        reply_string = f"Amy has said the word 'noob' {counter} times since 20/07/23."
        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def quote(ws, player: dict, command: dict):
        reply_string = "Your 'random' quote is: https://prnt.sc/E4RHZ-3zj3JB"
        Chat.send_chat_message(ws, reply_string)

    @staticmethod
    def import_command(ws, player: dict, command: dict):
        if command['payload'] == "antigravity":
            reply_string = "https://xkcd.com/353"
            Chat.send_chat_message(ws, reply_string)
