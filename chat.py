import random
from datetime import datetime

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

        if "noob" in message:
            current_stats["total_noobs"] += 1

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
    def get_chat_stat(ws, player: dict, message: str):
        required_value = None

        if "amy" in message:
            if "suck" in message:
                required_value = "amy_sucks"
            elif "noob" in message:
                required_value = "amy_noobs"
            elif "spoken" in message or "messages" in message:
                required_value = "amy_total"
        elif "noob" in message:
            required_value = "total_noobs"
        elif "other bot" in message:
            required_value = "botofnades_requests"
        elif "blood diamonds" in message:
            required_value = "blood_diamonds_found"
        elif "diamonds" in message:
            required_value = "diamonds_found"
        elif "blood gem goblin" in message:
            required_value = "blood_goblin_encounters"
        elif "gem goblin" in message:
            required_value = "gem_goblin_encounters"
        elif "server message" in message:
            required_value = "total_yells"
        elif "elite" in message:
            required_value = "elite_achievements"
        elif "sigils" in message:
            required_value = "sigils_found"
        elif "asked you" in message:
            required_value = "luxbot_requests"
        elif "max" in message:
            required_value = "max_levels"
        elif "messages" in message:
            required_value = "total_messages"

        if "day" in message:
            time_frame = 1
        elif "hour" in message:
            time_frame = 2
        else:
            time_frame = 0

        if required_value is not None:
            chat_stats = Db.read_config_row("chat_stats")
            requested_value = chat_stats[required_value]

            start_date = chat_stats["start_date"]
            start_datetime = datetime.strptime(start_date, "%d/%m/%y %H:%M")
            delta = datetime.now() - start_datetime
            total_time = round(delta.total_seconds())

            request_per_time = Chat.per_time(total_time, requested_value)

            response = f"Here's the number you wanted Lux: {request_per_time[time_frame]}. Get it yourself next time"
            Chat.send_chat_message(ws, response)

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
            "chat_stats": Chat.chat_stats,
            "fixed_fix": Chat.fixed_fix,
            "pirate_loot": Chat.pirate_loot,
            "sigil_list": Chat.sigil_list,
            "help": Chat.help,
        }

        dispatched_command = dispatch.get(command["sub_command"], None)

        if dispatched_command is None:
            return True, "Invalid LuxBot command issued."

        errored, msg = dispatched_command(ws, player, command)

        return errored, msg

    @staticmethod
    def echo(ws, player: dict, command: dict):
        reply_string = f"Echo: {player['username']}: {command['payload']}"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"
        
    @staticmethod
    def combat(ws, player: dict, command: dict):
        reply_string = f"https://idle-pixel.wiki/index.php/Combat_Guide"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def dho_maps(ws, player: dict, command: dict):
        reply_string = f"Offline map solutions: https://prnt.sc/Mdd-AKMIHfLz"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def scripts(ws, player: dict, command: dict):
        reply_string = f"https://idle-pixel.wiki/index.php/Scripts"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

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
        return False, "Success"

    @staticmethod
    def wiki(ws, player: dict, command: dict):
        if command['payload'] is not None:
            reply_string = f"Wiki page for {command['payload']}: https://idle-pixel.wiki/index.php/{command['payload'].capitalize()}"
        else:
            reply_string = f"Wiki home page: https://idle-pixel.wiki/index.php/Main_Page"

        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

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
        return False, "Success"

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
        return False, "Success"

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
        return False, "Success"

    @staticmethod
    def amy_noobs(ws, player: dict, command: dict):
        chat_stats = Db.read_config_row("chat_stats")

        start_date = chat_stats["start_date"]
        start_datetime = datetime.strptime(start_date, "%d/%m/%y %H:%M")
        delta = datetime.now() - start_datetime
        total_time = round(delta.total_seconds())

        amy_noobs = Chat.per_time(total_time, chat_stats["amy_noobs"])
        amy_total = chat_stats["amy_total"]
        total_noobs = chat_stats["total_noobs"]

        noobs_per_amy = round((amy_noobs[0] / amy_total) * 100)
        noobs_per_total = round((amy_noobs[0] / total_noobs) * 100)
        reply_string = f"Since {start_date}, Amy has said noob {amy_noobs[0]} times. That's {round(amy_noobs[1])} times per day; making up {noobs_per_amy}% of her messages, and {noobs_per_total}% of the times noob is said in chat."
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def quote(ws, player: dict, command: dict):
        reply_string = "Your 'random' quote is: https://prnt.sc/E4RHZ-3zj3JB"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def import_command(ws, player: dict, command: dict):
        if command['payload'] == "antigravity":
            reply_string = "https://xkcd.com/353"
            Chat.send_chat_message(ws, reply_string)

        return False, "Success"

    @staticmethod
    def bird_loot(ws, player: dict, command: dict):
        reply_string = f"Here's the birdhouse loot table, {player['username'].capitalize()}: https://i.imgur.com/3Tka1n8.png"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def chat_stats(ws, player: dict, command: dict):
        chat_stats = Db.read_config_row("chat_stats")
        start_date = chat_stats["start_date"]

        start_datetime = datetime.strptime(start_date, "%d/%m/%y %H:%M")

        delta = datetime.now() - start_datetime
        total_time = round(delta.total_seconds())

        # Storing this in a dictionary would make this section dryer but would make the output string a lot less readable
        chats = Chat.per_time(total_time, chat_stats["total_messages"])
        nades = Chat.per_time(total_time, chat_stats["botofnades_requests"])
        luxbot = Chat.per_time(total_time, chat_stats["luxbot_requests"])
        yells = Chat.per_time(total_time, chat_stats["total_yells"])
        diamonds = Chat.per_time(total_time, chat_stats["diamonds_found"])
        blood_diamonds = Chat.per_time(total_time, chat_stats["blood_diamonds_found"])
        sigils = Chat.per_time(total_time, chat_stats["sigils_found"])
        goblins = Chat.per_time(total_time, chat_stats["gem_goblin_encounters"])
        blood_goblins = Chat.per_time(total_time, chat_stats["blood_goblin_encounters"])
        elites = Chat.per_time(total_time, chat_stats["elite_achievements"])
        skills = Chat.per_time(total_time, chat_stats["max_levels"])

        output_string = f'''
        Since {start_date} there have been:
        {chats[0]} chat messages sent!
        {nades[0]} BotofNades commands sent!
        {luxbot[0]} LuxBot commands sent!
        {yells[0]} server messages sent!
        Those include:
        	- {diamonds[0]} diamonds found!
        	- {blood_diamonds[0]} blood diamonds found!
        	- {sigils[0]} monster sigils found!

        	- {goblins[0]} gem goblin encounters!
        	- {blood_goblins[0]} blood gem goblin encounters!

        	- {elites[0]} elite achievement sets completed!
        	- {skills[0]} skills reached the max level of 100!
        ======================================================================================
        Every day that means:
        	- {chats[1]} chat messages and {yells[1]} server messages sent!
        	- {diamonds[1]} diamonds, {blood_diamonds[1]} blood diamonds, and {sigils[1]} monster sigils have been found!
        	- {goblins[1]} gem goblins, and {blood_goblins[1]} blood gem goblins have been fought!
        	- {elites[1]} elites and {skills[1]} skills have been completed!
        ======================================================================================
        That works out to be:
        	- {chats[2]} chat messages and {yells[2]} server messages sent!
        	- {diamonds[2]} diamonds, {blood_diamonds[2]} blood diamonds, and {sigils[2]} monster sigils found!
        	- {goblins[2]} gem goblins, and {blood_goblins[2]} blood gem goblins fought!
        	- {elites[2]} elites and {skills[2]} skills completed!
        every hour!
        '''

        pastebin_url = Utils.dump_to_pastebin(output_string, "10M")

        Chat.send_chat_message(ws, f"{player['username'].capitalize()}, here are the currently tracked stats: {pastebin_url}")
        return False, "Success"

    @staticmethod
    def fixed_fix(ws, player: dict, command: dict):
        reply_string = f"Here's the fix for Fixed, {player['username'].capitalize()}: https://prnt.sc/tYv2ZlTgXPPx"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def pirate_loot(ws, player: dict, command: dict):
        reply_string = f"{player['username'].capitalize()} here's the pirate loot and cost table: https://prnt.sc/tLjabu1LGtsX"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def sigil_list(ws, player: dict, command: dict):
        reply_string = f"{player['username'].capitalize()} here's (an out-dated) image of Lux's sigils: https://prnt.sc/zs7CX4WjB8q8"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def per_time(total_time: int, stat_count: int) -> tuple[int, float, float]:
        """
        Takes a time in seconds(int) and a stat_count(int),
        returns tuple of stat_count(int), count_per_day(float), count_per_hour(float)
        """
        number_of_hours = round(total_time / 3600)
        number_of_days = round(number_of_hours / 24)

        if number_of_hours == 0:
            count_per_hour = 0
        else:
            count_per_hour = round(stat_count / number_of_hours, 3)

        if number_of_days == 0:
            count_per_day = 0
        else:
            count_per_day = round(stat_count / number_of_days, 3)

        return stat_count, count_per_day, count_per_hour

    @staticmethod
    def help(ws, player: dict, command: dict):
        help_strings = {
            "echo": "Repeats your message back into chat. [!luxbot:echo<message>]",
            "combat": "Replies with a link to the combat guide on the wiki.",
            "dho_maps": "Replies with the solutions to the Offline treasure maps.",
            "scripts": "Replies with a link to the QoL scripts wiki page.",
            "vega": "Replies with a <random> photo of Vega. [!luxbot:vega <opt:title>]",
            "wiki": "Replies with a link to the wiki. [!luxbot:wiki <opt:page_title>]",
            "bear": "Replies with a <random> photo of Bear. [!luxbot:bear <opt:title>]",
            "pet": "Replies with a random photo from the pets database. [!luxbot:pet <opt:pet_name>]",
            "pet_stats": "Replies with a pastebin link containing info about the pets database.",
            "amy_noobs": "Tells you the frequency with which Amy says the word 'noob'.",
            "quote": "Replies with a random stored quote. (Only one placeholder quote atm.)",
            "import": "Easteregg. [!luxbot:import <REDACTED>]",
            "bird_loot": "Replies with a screenshot of the birdhouse loot list.",
            "chat_stats": "Replies with a pastebin link containing various chat statistics.",
            "fixed_fix": "A screenshot of the fix to Kape's DHP Fixed script, generously provided by strawberry.",
            "pirate_loot": "A screenshot of the pirate cost and odds table.",
            "sigil_list": "A screenshot of Lux's sigil collection.",
            "help": "Replies with a list of chat commands or info on a specific command. [!luxbot:help <opt:command>]",
        }

        payload = command["payload"]
        username = player["username"]

        if payload is None:
            help_string = "Command List"
            for com in help_strings:
                help_string += f" | {com}"

            Chat.send_chat_message(ws, help_string)
            return False, "Success"

        if payload not in help_strings:
            help_string = f"Sorry {username}, {payload} is not a valid LuxBot command."
            Chat.send_chat_message(ws, help_string)
            return False, "Success"

        help_string = help_strings[payload]
        Chat.send_chat_message(ws, help_string)
        return False, "Success"
