import textwrap

from chat import Chat
from utils import Utils, Db


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

    @staticmethod
    def dispatcher(ws, getter: bool, command: dict):
        dispatch = {
            "echo": {
                "permission": 2,
                "command": Interactor.echo
            },
            "chatecho": {
                "permission": 2,
                "command": Interactor.chatecho
            },
            "relay": {
                "permission": 2,
                "command": Interactor.relay
            },
            "triggers": {
                "permission": 2,
                "command": Interactor.triggers
            },
            "speak": {
                "permission": 2,
                "command": Interactor.speak
            },
            "pets": {
                "permission": 2,
                "command": Interactor.pets
            },
            "help": {
                "permission": 2,
                "command": Interactor.help
            },
            "permissions": {
                "permission": 3,
                "command": Interactor.permissions
            },
            "mute": {
                "permission": 3,
                "command": Interactor.mute
            },
            "whois": {
                "permission": 3,
                "command": Interactor.whois
            },
            "generic": {
                "permission": 3,
                "command": Interactor.generic
            },
        }

        if getter:
            return dispatch

        if command["command"] in dispatch:
            if Utils.permission_level(command["player"]) < dispatch[command["command"]]["permission"]:
                return "Permission level too low."
        else:
            return "Invalid command."

        dispatch[command["command"]]["command"](ws, command)
        return f"Command '{command['command']}' issued successfully."

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
        recipient = content.split(":")[0]
        message = content.split(":")[1]
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
            Utils.send_custom_message(ws, player, f"{payload} has been added to automod triggers.")
        elif subcommand == "remove":
            trigger_list.remove(payload.strip())
            trigger_dict = {"word_list": ",".join(trigger_list)}
            Db.set_config_row("automod_flag_words", trigger_dict)
            Utils.send_custom_message(ws, player, f"{payload} has been removed from the automod triggers.")

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
            Utils.send_custom_message(ws, player, f"Invalid syntax. (pets:add;pet;title;link)")
        else:
            subcommand = split_sub_command[0]
            pet = split_sub_command[1]
            title = split_sub_command[2]
            link = split_sub_command[3]

            pet_data = (title, pet, link)

            if subcommand == "add":
                Db.add_pet(ws, pet_data, player)
                Utils.send_custom_message(ws, player, f"{pet} link added with title: {title}")
            elif subcommand == "remove":
                Utils.send_custom_message(ws, player, f"Remove feature not added.")

    @staticmethod
    def permissions(ws, command: dict):
        player = command["player"]
        content = command["content"]
        split_command = content.split(";")
        if len(split_command) == 2:
            updated_player = split_command[0]
            level = split_command[1]
            Db.update_permission(ws, player, updated_player, level)
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
            help_string = "Command List"
            for com in interactor_commands:
                help_string += f" | {com}"
            Utils.send_custom_message(ws, player, help_string)
            Utils.send_custom_message(ws, player, "help:command will give a brief description of the command.")
        else:
            help_string = Interactor.get_help_string(content)
            Utils.send_custom_message(ws, player, help_string)

        if content == "triggers":
            trigger_list = Db.read_config_row("automod_flag_words")
            Utils.send_custom_message(ws, player, f"Current triggers: {trigger_list}")
        elif content == "permissions":
            query = f"SELECT * FROM permissions"
            params = tuple()
            perms_list = Db.fetch_db(query, params, True)
            perms_string = f"Current permissions: {perms_list}"
            wrapped_message = textwrap.wrap(perms_string, 240)
            for message in wrapped_message:
                Utils.send_custom_message(ws, player, message)
