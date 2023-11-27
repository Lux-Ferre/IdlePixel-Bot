import textwrap
import requests
import json

from chat import Chat
from utils import Utils, Db


class Interactor:
    @staticmethod
    def get_help_string(command: str) -> str:
        dispatch_map = Interactor.dispatcher("", True, {})
        error_reply = {
            "help_string": "Invalid help command. Should be of format (help:command)"
        }

        requested_command = dispatch_map.get(command, error_reply)

        help_string = requested_command["help_string"]

        return help_string

    @staticmethod
    def dispatcher(ws, getter: bool, command: dict):
        dispatch_map = {
            "echo": {
                "permission": 2,
                "command": Interactor.echo,
                "help_string": "Echos message as custom. (echo:message)"
            },
            "chatecho": {
                "permission": 2,
                "command": Interactor.chatecho,
                "help_string": "Echos message into chat. (chatecho:message)"
            },
            "relay": {
                "permission": 2,
                "command": Interactor.relay,
                "help_string": "Passes on message to another account. (relay:recipient;message)"
            },
            "triggers": {
                "permission": 2,
                "command": Interactor.triggers,
                "help_string": "Add/remove automod triggers. (triggers:add/remove;trigger)"
            },
            "speak": {
                "permission": 2,
                "command": Interactor.speak,
                "help_string": "Relays text to chat as the bot. (speak:content)"
            },
            "pets": {
                "permission": 2,
                "command": Interactor.pets,
                "help_string": "Interacts with the pets database. (pets:add/remove;pet;title;link)"
            },
            "update_cheaters": {
                "permission": 2,
                "command": Interactor.update_cheaters,
                "help_string": "Updates cheater permission levels from Nades's list."
            },
            "help": {
                "permission": 2,
                "command": Interactor.help,
                "help_string": "Lists commands or gives a description of a command. (help:command)"
            },
            "permissions": {
                "permission": 3,
                "command": Interactor.permissions,
                "help_string": "Modifies player permissions. (permissions:player:level)"
            },
            "mute": {
                "permission": 3,
                "command": Interactor.mute,
                "help_string": "Mutes target player. (mute:player;reason;length;is_ip)"
            },
            "whois": {
                "permission": 3,
                "command": Interactor.whois,
                "help_string": "Runs a whois check on <player>, sending the result to all level 3 accounts. (whois:<player>)"
            },
            "newstat": {
                "permission": 3,
                "command": Interactor.new_stat,
                "help_string": "Adds a new datapoint to the chat_stats stored in the database. (newstat:<datapoint_name>)"
            },
            "generic": {
                "permission": 3,
                "command": Interactor.generic,
                "help_string": "Relays content as a websocket frame."
            },
        }

        if getter:
            return dispatch_map

        if command["command"] in dispatch_map:
            if Utils.permission_level(command["player"]) < dispatch_map[command["command"]]["permission"]:
                return "Interactor:Response:Permission level too low."
        else:
            return "Interactor:Response:Invalid command."

        dispatch_map[command["command"]]["command"](ws, command)
        return f"Interactor:Response:Command '{command['command']}' issued successfully."

    @staticmethod
    def echo(ws, command: dict):
        player = command["player"]
        content = command["content"]
        Utils.send_custom_message(ws, player, content)

    @staticmethod
    def chatecho(ws, command: dict):
        player = command["player"]
        content = command["content"]
        chat_string = f"{player} echo: {content}"
        Chat.send_chat_message(ws, chat_string)

    @staticmethod
    def relay(ws, command: dict):
        content = command["content"]
        split_content = content.split(";", 1)
        recipient = split_content[0]
        message = split_content[1]
        Utils.send_custom_message(ws, recipient, message)

    @staticmethod
    def triggers(ws, command: dict):
        player = command["player"]
        content = command["content"]
        flag_words_dict = Db.read_config_row("automod_flag_words")
        trigger_list = flag_words_dict["word_list"].split(",")
        split_sub_command = content.split(";")
        subcommand = split_sub_command[0]
        payload = split_sub_command[1]
        if subcommand == "add":
            trigger_list.append(payload.strip())
            trigger_dict = {"word_list": ",".join(trigger_list)}
            Db.set_config_row("automod_flag_words", trigger_dict)
            Utils.send_custom_message(ws, player, f"Interactor:Response:{payload} has been added to automod triggers.")
        elif subcommand == "remove":
            trigger_list.remove(payload.strip())
            trigger_dict = {"word_list": ",".join(trigger_list)}
            Db.set_config_row("automod_flag_words", trigger_dict)
            Utils.send_custom_message(ws, player, f"Interactor:Response:{payload} has been removed from the automod triggers.")

    @staticmethod
    def speak(ws, command: dict):
        content = command["content"]
        Chat.send_chat_message(ws, content)

    @staticmethod
    def pets(ws, command: dict):
        player = command["player"]
        content = command["content"]
        split_sub_command = content.split(";")
        if len(split_sub_command) != 4:
            Utils.send_custom_message(ws, player, f"Interactor:Response:Invalid syntax. (pets:add;pet;title;link)")
        else:
            subcommand = split_sub_command[0]
            pet = split_sub_command[1]
            title = split_sub_command[2]
            link = split_sub_command[3]

            pet_data = (title, pet, link)

            if subcommand == "add":
                Db.add_pet(ws, pet_data, player)
                Utils.send_custom_message(ws, player, f"Interactor:Response:{pet} link added with title: {title}")
            elif subcommand == "remove":
                Utils.send_custom_message(ws, player, f"Interactor:Response:Remove feature not added.")

    @staticmethod
    def update_cheaters(ws, command: dict):
        player = command["player"]

        url = 'https://raw.githubusercontent.com/GodofNades/idle-pixel/main/AltTraders.json'
        resp = requests.get(url)
        data = json.loads(resp.text)

        cheater_list = []
        for data_point in data:
            cheater_list.append(data_point["name"])

        for cheater in cheater_list:
            Db.update_permission(ws, player, cheater, "-2")

        Utils.send_custom_message(ws, player, f"LuxBot:update_cheaters:All cheaters now given level -2 permissions.")

    @staticmethod
    def permissions(ws, command: dict):
        player = command["player"]
        content = command["content"]
        split_command = content.split(";")
        if len(split_command) == 2:
            updated_player = split_command[0]
            level = split_command[1]
            Db.update_permission(ws, player, updated_player, level)
            Utils.send_custom_message(ws, player, f"LuxBot:update_permission:{updated_player} permission level set to {level}.")
        else:
            Utils.send_custom_message(ws, player, "Invalid syntax. Must be of form 'permissions:player;level'")

    @staticmethod
    def mute(ws, command: dict):
        player = command["player"]
        content = command["content"]
        if content is None:
            split_data = None
            Utils.send_custom_message(ws, player, "Invalid mute format. Must be mute:player;reason;length;is_ip")
        else:
            split_data = content.split(";")

        if len(split_data) == 4 and split_data is not None:
            target = split_data[0]
            reason = split_data[1]
            length = split_data[2]
            is_ip = split_data[3]

            Utils.mute_player(ws, target, length, reason, is_ip)
            Utils.send_custom_message(ws, player, f"{target} has been successfully muted for {length} hours.")
        else:
            Utils.send_custom_message(ws, player, "Invalid mute format. Must be mute:player;reason;length;is_ip")

    @staticmethod
    def whois(ws, command: dict):
        player = command["player"]
        content = command["content"]
        if content is None:
            Utils.send_custom_message(ws, player, "Invalid syntax. Specify a target.")
        else:
            Chat.send_chat_message(ws, f"/whois {content}")

    @staticmethod
    def new_stat(ws, command: dict):
        player = command["player"]
        content = command["content"]

        current_stats = Db.read_config_row("chat_stats")
        if content in current_stats:
            response_string = f"The value {content} already exists!"
        else:
            current_stats[content] = 0
            Db.set_config_row("chat_stats", current_stats)
            response_string = f"{content} is now added to the tracking database."

        Utils.send_custom_message(ws, player, response_string)

    @staticmethod
    def generic(ws, command: dict):
        player = command["player"]
        content = command["content"]
        Utils.send_generic(ws, content)
        Utils.send_custom_message(ws, player, f"Generic websocket command sent: {content}")

    @staticmethod
    def help(ws, command: dict):
        player = command["player"]
        content = command["content"]
        interactor_commands = Interactor.dispatcher(ws, True, {})
        if content is None:
            help_string = "Interactor:help_list:"
            for com in interactor_commands:
                help_string += f" | {com}"
            Utils.send_custom_message(ws, player, help_string)
            Utils.send_custom_message(ws, player, "Interactor:Help:help:<command> will give a brief description of the command.")
        else:
            help_string = Interactor.get_help_string(content)
            Utils.send_custom_message(ws, player, help_string)

        if content == "triggers":
            trigger_list = Db.read_config_row("automod_flag_words")
            Utils.send_custom_message(ws, player, f"Interactor:trigger_list:{trigger_list}")
        elif content == "permissions":
            query = f"SELECT * FROM permissions"
            params = tuple()
            perms_list = Db.fetch_db(query, params, True)
            perms_string = f"{perms_list}"
            wrapped_message = textwrap.wrap(perms_string, 230)
            for message in wrapped_message:
                Utils.send_custom_message(ws, player, f"Interactor:perm_list:{message}")
