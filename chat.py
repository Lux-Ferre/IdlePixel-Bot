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
    def track_chats(ws, player: dict, message: str):
        amy_accounts = [
            "amyjane1991",
            "youallsuck",
            "freeamyhugs",
            "amybear",
            "zombiebunny",
            "idkwat2put",
            "skyedemon",
            "iloveamy",
            "demonlilly",
        ]

        current_stats = Db.read_config_row("chat_stats")

        current_stats["total_messages"] += 1

        if len(message) < 1:
            return

        if player["username"] in amy_accounts:
            current_stats["amy_total"] += 1

            if message[0] != "!":
                if "noob" in message:
                    current_stats["amy_noobs"] += 1

                if "suck" in message:
                    current_stats["amy_sucks"] += 1

        if message[0] == "!":
            if message[:7] == "!luxbot":
                current_stats["luxbot_requests"] += 1
            else:
                current_stats["botofnades_requests"] += 1

        Db.set_config_row("chat_stats", current_stats)

    @staticmethod
    def track_yells(yell_dict: dict):
        current_stats = Db.read_config_row("chat_stats")

        current_stats["total_yells"] += 1

        match yell_dict["type"]:
            case "diamond":
                current_stats["diamonds_found"] += 1
            case "blood_diamond":
                current_stats["blood_diamonds_found"] += 1
            case "gem_goblin":
                current_stats["gem_goblin_encounters"] += 1
            case "blood_goblin":
                current_stats["blood_goblin_encounters"] += 1
            case "sigil":
                current_stats["sigils_found"] += 1
            case "max_level":
                current_stats["max_levels"] += 1
            case "elite_achievement":
                current_stats["elite_achievements"] += 1
            case _:
                pass

        Db.set_config_row("chat_stats", current_stats)

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
            "bird_loot": Chat.bird_loot,
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
        reply_string = f"Amy said the word 'noob' 275 times between 20/07/23 and 06/08/23. She also said 'sucks' 46 times."
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

    @staticmethod
    def bird_loot(ws, player: dict, command: dict):
        reply_string = f"Here's the birdhouse loot table, {player['username'].capitalize()}: https://i.imgur.com/3Tka1n8.png"
        Chat.send_chat_message(ws, reply_string)
