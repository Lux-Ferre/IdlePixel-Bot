import random
import re
from datetime import datetime, timedelta

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
        split_message = raw_message.split(" ", 1)
        full_command = split_message[0]
        split_command = full_command.split(":", 1)
        primary_command = split_command[0].lower()
        if len(split_command) > 1:
            sub_command = split_command[1].lower()
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
        replace_dict = {
            "richie19942": "Bawbag",
            "Richie19942": "Bawbag",
            "ma25": "Cupcake",
            "Ma25": "Cupcake",
            "amyjane1991": "Noobbun",
            "Amyjane1991": "Noobbun",
            "Axe": "Lux",
            "Luxferre": "Lux",
            "luxferre": "Lux",
            "Godofnades": "Nades",
            "godofnades": "Nades",
            "zlef": "Zlefy",
            "Zlef": "Zlefy",
            "cammyrock": "Clammy Rock",
            "Cammyrock": "Clammy Rock",
        }

        for key, value in replace_dict.items():
            chat_string = chat_string.replace(key, value)

        chat_string = f"CHAT={chat_string}"

        message_clear = True

        flag_words_dict = Db.read_config_row("automod_flag_words")
        automod_flag_words = flag_words_dict["word_list"].split(",")
        automod_flag_words += [" fag", "fag "]
        message = chat_string.lower()
        for trigger in automod_flag_words:
            if trigger in message:
                message_clear = False
                break
        if message_clear:
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
            "youarenoob",
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

        if message[:5] == "?wiki":      # 30/10/23 14:00
            current_stats["wikibot"] += 1

        if message[0] == "!":
            if message[:7] == "!hevent":
                current_stats["hevent"] += 1
            elif message[:6] == "!zombo":
                current_stats["zombo"] += 1
                if current_stats["zombo"] % 100 == 0:
                    Chat.send_chat_message(ws, f"{player['username'].capitalize()} just made request number {current_stats['zombo']} to the !zombo command! (Since I started tracking)")

            if message[:7] == "!luxbot":
                current_stats["luxbot_requests"] += 1
            else:
                current_stats["botofnades_requests"] += 1

        Db.set_config_row("chat_stats", current_stats)

    @staticmethod
    def track_yells(ws, yell_dict: dict):
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
            case "gold_armour":
                current_stats["gold_armour"] += 1
            case "one_life_death":
                current_stats["oneLifeDeaths"] += 1
                Chat.track_one_life_deaths(ws, yell_dict)
            case _:
                pass

        Db.set_config_row("chat_stats", current_stats)

    @staticmethod
    def track_one_life_deaths(ws, yell_dict: dict):
        message = yell_dict["message"]

        mob_name = message.split("died to a ")[1].split(" and lost")[0]

        current_stats = Db.read_config_row("one_life_killers")

        if mob_name not in current_stats:
            current_stats[mob_name] = 1
        else:
            current_stats[mob_name] += 1

        Db.set_config_row("one_life_killers", current_stats)

        if mob_name == "spider":
            spider_kills = current_stats["spider"]
            custom_string = f"spiderTaunt:spiderKill:{spider_kills}"
            Utils.send_custom_message(ws, "a spider", custom_string)

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
        elif "blood diamond" in message:
            required_value = "blood_diamonds_found"
        elif "diamond" in message:
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
        elif "playtime" in message:
            required_value = "playtime"
        elif "hevent" in message:
            required_value = "hevent"
        elif "zombo" in message:
            required_value = "zombo"

        if "day" in message:
            time_frame = 1
        elif "hour" in message:
            time_frame = 2
        else:
            time_frame = 0

        if required_value is not None:
            chat_stats = Db.read_config_row("chat_stats")

            if required_value == "playtime":
                diamonds = chat_stats["diamonds_found"]
                blood_diamonds = chat_stats["blood_diamonds_found"]

                est_by_diamonds = (diamonds * 1000000) / 60 / 60
                est_by_blood_diamonds = blood_diamonds * 25000000 / 60 / 60
                requested_value = round((est_by_blood_diamonds + est_by_diamonds) / 2)
            else:
                requested_value = chat_stats[required_value]

            if required_value == "hevent":
                start_date = "23/10/23 17:00"
            elif required_value == "zombo":
                start_date = "25/10/23 11:00"
            else:
                start_date = chat_stats["start_date"]

            start_datetime = datetime.strptime(start_date, "%d/%m/%y %H:%M")
            delta = datetime.now() - start_datetime
            total_time = round(delta.total_seconds())

            request_per_time = Chat.per_time(total_time, requested_value)

            match time_frame:
                case 1:
                    response_timeframe = "every day"
                case 2:
                    response_timeframe = "every hour"
                case _:
                    if required_value == "hevent":
                        response_timeframe = "since 17:00 23/10/2023 BST"
                    elif required_value == "zombo":
                        response_timeframe = "since 11:00 25/10/2023 BST"
                    else:
                        response_timeframe = "since 09/08/2023"

            response_value = f"{request_per_time[time_frame]} {response_timeframe}"

            response_patterns = [
                f"Here's the number you wanted {player['username'].capitalize()}: {response_value}. Get it yourself next time.",
                f"Ugh. Fine. Here: {response_value}.",
                f"You're so lazy! Here: {response_value}.",
                f"-.- {response_value}",
                f"*sigh* {response_value}",
                f"Damn slave driver... {response_value}...",
            ]

            response = random.choice(response_patterns)
            Chat.send_chat_message(ws, response)

    @staticmethod
    def dispatcher(ws, player: dict, command: dict, getter: bool = False):
        dispatch_map = {
            "echo": {
                "command": Chat.echo,
                "permission": 2,
                "help_string": "Repeats your message back into chat. [!luxbot:echo<message>]"
            },
            "dho_maps": {
                "command": Chat.dho_maps,
                "permission": 0,
                "help_string": "Replies with the solutions to the Offline treasure maps."
            },
            "vega": {
                "command": Chat.vega,
                "permission": 0,
                "help_string": "Replies with a <random> photo of Vega. [!luxbot:vega <opt:title>]",
            },
            "wiki": {
                "command": Chat.wiki,
                "permission": 0,
                "help_string": "Replies with a link to the wiki (links are case sensitive.) [!luxbot:wiki <opt:page_title>]",
            },
            "bear": {
                "command": Chat.bear,
                "permission": 0,
                "help_string": "Replies with a <random> photo of Bear. [!luxbot:bear <opt:title>]",
            },
            "pet": {
                "command": Chat.pet,
                "permission": 0,
                "help_string": "Replies with a random photo from the pets database. [!luxbot:pet <opt:pet_name>]",
            },
            "pet_stats": {
                "command": Chat.pet_stats,
                "permission": 0,
                "help_string": "Replies with a pastebin link containing info about the pets database.",
            },
            "amy_noobs": {
                "command": Chat.amy_noobs,
                "permission": 1,
                "help_string": "Tells you the frequency with which Amy says the word 'noob'.",
            },
            "quote": {
                "command": Chat.quote,
                "permission": 1,
                "help_string": "Replies with a random stored quote. (Only one placeholder quote atm.)",
            },
            "import": {
                "command": Chat.import_command,
                "permission": 1,
                "help_string": "Easteregg. [!luxbot:import <REDACTED>]",
            },
            "chat_stats": {
                "command": Chat.chat_stats,
                "permission": 0,
                "help_string": "Replies with a pastebin link containing various chat statistics.",
            },
            "pirate_loot": {
                "command": Chat.pirate_loot,
                "permission": 0,
                "help_string": "A screenshot of the pirate cost and odds table.",
            },
            "sigil_list": {
                "command": Chat.sigil_list,
                "permission": 1,
                "help_string": "A screenshot of Lux's sigil collection.",
            },
            "gem_guide": {
                "command": Chat.gem_guide,
                "permission": 0,
                "help_string": "A link with a guide for how to prioritize tool socketing upgrades.",
            },
            "cammy": {
                "command": Chat.cammyrock,
                "permission": 1,
                "help_string": "Replies with an image of Cammy.",
            },
            "better_calc": {
                "command": Chat.better_calc,
                "permission": 1,
                "help_string": "Does basic arithmetical operations.",
            },
            "one_life": {
                "command": Chat.one_life,
                "permission": 1,
                "help_string": "Replies with a pastebin link with current 1L death stats.",
            },
            "help": {
                "command": Chat.help,
                "permission": 0,
                "help_string": "Replies with a list of chat commands or info on a specific command. [!luxbot:help <opt:command>]",
            },
        }

        if getter:
            return dispatch_map

        request = command["sub_command"]
        requested_command_data = dispatch_map.get(request, None)

        if requested_command_data is None:
            return True, "Invalid LuxBot command issued.", ""

        if player["perm"] >= requested_command_data["permission"]:
            last_command = command["last_time"]
            current_time = datetime.now()
            cooldown_length = timedelta(minutes=1)
            elapsed_time = current_time - last_command

            if elapsed_time > cooldown_length or player["perm"] > 0:
                dispatched_command = requested_command_data["command"]
            else:
                print(f"{elapsed_time} < {cooldown_length}")
                return False, "Cooldown", last_command

        else:
            return True, f"{player['username']} permission level too low to use {command['sub_command']}.", ""

        errored, msg = dispatched_command(ws, player, command)

        return errored, msg, current_time

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
                reply_string = f"{player['username'].capitalize()}, here's the {command['payload']} Vega you requested: {vega_links[command['payload'].lower()]}"
            except KeyError:
                reply_string = f"Sorry {player['username'].capitalize()}, that is an invalid Vega."
        else:
            random_vega = random.choice(list(vega_links))
            reply_string = f"{player['username'].capitalize()}, your random Vega is: {random_vega}: {vega_links[random_vega]}"

        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def wiki(ws, player: dict, command: dict):
        if command['payload'] is not None:
            reply_string = f"Wiki page for {command['payload']}: https://idle-pixel.wiki/index.php/{command['payload']}"
        else:
            reply_string = f"Wiki home page: https://idle-pixel.wiki/index.php/Main_Page"

        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def bear(ws, player: dict, command: dict):
        bear_links = Db.get_pet_links("bear")
        if command['payload'] is not None:
            try:
                reply_string = f"{player['username'].capitalize()}, here's the {command['payload']} Bear you requested: {bear_links[command['payload'].lower()]}"
            except KeyError:
                reply_string = f"Sorry {player['username'].capitalize()}, that is an invalid Bear."
        else:
            random_bear = random.choice(list(bear_links))
            reply_string = f"{player['username'].capitalize()}, your random Bear is: {random_bear}: {bear_links[random_bear]}"

        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def pet(ws, player: dict, command: dict):
        if command['payload'] is not None:
            query = "SELECT title, pet, link FROM pet_links WHERE pet=? ORDER BY RANDOM() LIMIT 1;"
            params = (command['payload'].lower(),)
        else:
            query = "SELECT title, pet, link FROM pet_links ORDER BY RANDOM() LIMIT 1;"
            params = tuple()

        pet_link = Db.fetch_db(query, params, False)

        if pet_link is None:
            reply_string = f"Sorry {player['username'].capitalize()}, that is an invalid pet name."
        else:
            reply_string = f"{player['username'].capitalize()}, your random pet is {pet_link[1].capitalize()}! {pet_link[0].capitalize()}: {pet_link[2]}"

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
        golds = Chat.per_time(total_time, chat_stats["gold_armour"])
        wikibot = Chat.per_time(total_time, chat_stats["wikibot"])

        output_string = f'''
        Since {start_date} there have been:
        {chats[0]} chat messages sent!
        {nades[0]} BotofNades commands sent!
        {luxbot[0]} LuxBot commands sent!
        {wikibot[0]} WikiSearch bot requests made!
        {yells[0]} server messages sent!
        Those include:
        	- {golds[0]} gold armour pieces found!
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
    def gem_guide(ws, player: dict, command: dict):
        reply_string = f"https://www.reddit.com/r/idlepixel/comments/xzo62l/dboys_gemming_priorities_guide/"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def cammyrock(ws, player: dict, command: dict):
        reply_string = f"{player['username'].capitalize()}, here is a photo of Clammy Rock at a party: https://prnt.sc/CibZHdTWns3G"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def better_calc(ws, player: dict, command: dict):
        def parse_input(raw_input: str) -> list:
            pattern = re.compile(r"([+/*-])")
            input_with_spaces = re.sub(pattern, r" \1 ", raw_input)

            input_list = input_with_spaces.split()

            def is_floatable(n):
                n = n.replace(".", "", 1)
                return n.isnumeric()

            converted_list = [float(value) if is_floatable(value) else value for value in input_list]

            for value in converted_list:
                if not (isinstance(value, float) or re.search(pattern, value)):
                    raise ValueError

            return converted_list

        if command['payload'] is not None:
            input_string = command["payload"]
        else:
            return True, "Invalid input"

        calculation_map = {
            "*": (lambda a, b: a * b),
            "/": (lambda a, b: a / b),
            "+": (lambda a, b: a + b),
            "-": (lambda a, b: a - b),
        }

        parsed_list = parse_input(input_string)

        if len(parsed_list) % 2 == 0:
            return True, "Invalid input"

        for operator, func in calculation_map.items():
            while operator in parsed_list:
                op_index = parsed_list.index(operator)
                new_value = func(parsed_list[op_index - 1], parsed_list[op_index + 1])

                parsed_list[op_index - 1] = new_value
                del parsed_list[op_index:op_index + 2]

        reply_string = f"{player['username'].capitalize()}, here is the result: {parsed_list[0]}"
        Chat.send_chat_message(ws, reply_string)
        return False, "Success"

    @staticmethod
    def one_life(ws, player: dict, command: dict):
        enemy_info = {
            "ent": {
                "display": "Boss Ent",
                "location": "Quest",
                "kills": 0
            },
            "rat": {
                "display": "Rat",
                "location": "fields",
                "kills": 0
            },
            "spider": {
                "display": "Spider",
                "location": "fields",
                "kills": 0
            },
            "chicken": {
                "display": "Chicken",
                "location": "fields",
                "kills": 0
            },
            "bee": {
                "display": "Bee",
                "location": "fields",
                "kills": 0
            },
            "lizard": {
                "display": "Lizard",
                "location": "fields",
                "kills": 0
            },
            "snake": {
                "display": "Snake",
                "location": "Forest",
                "kills": 0
            },
            "ants": {
                "display": "Ants",
                "location": "Forest",
                "kills": 0
            },
            "wolf": {
                "display": "Wolf",
                "location": "Forest",
                "kills": 0
            },
            "thief": {
                "display": "Thief",
                "location": "Forest",
                "kills": 0
            },
            "forest_ent": {
                "display": "Ent",
                "location": "Forest",
                "kills": 0
            },
            "bear": {
                "display": "Bear",
                "location": "Caves",
                "kills": 0
            },
            "goblin": {
                "display": "Goblin",
                "location": "Caves",
                "kills": 0
            },
            "bat": {
                "display": "Bat",
                "location": "Caves",
                "kills": 0
            },
            "skeleton": {
                "display": "Skeleton",
                "location": "Caves",
                "kills": 0
            },
            "fire_snake": {
                "display": "Fire Snake",
                "location": "Volcano",
                "kills": 0
            },
            "fire_hawk": {
                "display": "Fire Hawk",
                "location": "Volcano",
                "kills": 0
            },
            "fire_golem": {
                "display": "Fire Golem",
                "location": "Volcano",
                "kills": 0
            },
            "fire_witch": {
                "display": "Fire Witch",
                "location": "Volcano",
                "kills": 0
            },
        }
        one_life_total = Db.read_config_row("chat_stats")["oneLifeDeaths"]

        one_life_killers = Db.read_config_row("one_life_killers")

        for mob, kill_count in one_life_killers.items():
            if mob in enemy_info:
                enemy_info[mob]["kills"] = kill_count
            else:
                enemy_info[mob] = {
                    "display": mob,
                    "location": "Unknown",
                    "kills": kill_count,
                }

        display_string = f"""Total One-life deaths: {one_life_total}\n\n\n"""

        for mob, data in enemy_info.items():
            new_line = f"{data['location']} - {data['display']}: {data['kills']}\n"
            display_string += new_line

        pastebin_url = Utils.dump_to_pastebin(display_string, "10M")

        Chat.send_chat_message(ws, f"{player['username'].capitalize()}, here are the stats: {pastebin_url}")

        return False, ""

    @staticmethod
    def help(ws, player: dict, command: dict):
        payload = command["payload"]
        username = player["username"]

        chat_commands = Chat.dispatcher(ws, player, command, getter=True)

        if payload is None:
            help_string = "Command List"
            for com in chat_commands:
                help_string += f" | {com}"

            Chat.send_chat_message(ws, help_string)
            return False, "Success"
        else:
            error_reply = {
                "help_string": f"Sorry {username}, {payload} is not a valid LuxBot command."
            }

            requested_command = chat_commands.get(payload, error_reply)

            help_string = requested_command["help_string"]

        Chat.send_chat_message(ws, help_string)
        return False, "Success"
