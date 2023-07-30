import asyncio
import os
import discord
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import websocket
import sys
from datetime import datetime
from discord import SyncWebhook
import rel
import ssl
import sqlite3
import json
import base64
import textwrap
import traceback

from utils import RepeatTimer, Interactor, Db
from chat import Chat


def get_env_var(env_var: str) -> str:
    try:
        return os.environ[env_var]
    except KeyError:
        print("Missing environment variable")
        raise


def set_env_consts() -> dict:
    env_const_list = {
        "IP_USERNAME": "",
        "IP_PASSWORD": "",
        "TESTING_HOOK_URL": "",
        "LBT_DISCORD_HOOK_URL": "",
        "DH_DISCORD_HOOK_URL": "",
        "PASTEBIN_API_KEY": "",
    }

    for key in env_const_list:
        env_const_list[key] = get_env_var(key)

    return env_const_list


def is_development_mode():
    cl_args = sys.argv
    dev_mode = False

    for arg in cl_args:
        if arg == "-d":
            print("Development mode enabled.")
            dev_mode = True

    return dev_mode


async def get_signature() -> str:
    async with async_playwright() as p:
        browser_type = p.chromium
        browser = await browser_type.launch_persistent_context("persistent_context")
        page = await browser.new_page()

        await page.goto("https://idle-pixel.com/login/")
        await page.locator('[id=id_username]').fill(env_consts["IP_USERNAME"])
        await page.locator('[id=id_password]').fill(env_consts["IP_PASSWORD"])
        await page.locator("[id=login-submit-button]").click()

        page_content = await page.content()
        soup = BeautifulSoup(page_content, 'html.parser')
        script_tag = soup.find("script").text

        sig_plus_wrap = script_tag.split(";", 1)[0]

        signature = sig_plus_wrap.split("'")[1]

        return signature


def on_ws_message(ws, raw_message):
    ignore_messages = ["SET_COUNTRY"]
    split_message = raw_message.split("=", 1)
    if len(split_message) > 1:
        [message_type, message_data] = split_message
    else:
        message_type = raw_message
        message_data = ""

    if message_type == "SET_ITEMS":
        if development_mode:
            print(f"{message_type}: {message_data}")
    elif message_type == "CHAT":
        on_chat(message_data)
    elif message_type == "YELL":
        on_yell(message_data)
    elif message_type == "CUSTOM":
        on_custom(message_data)
    elif message_type == "OPEN_DIALOGUE":
        on_dialogue(message_data)
    elif message_type == "VALID_LOGIN":
        print("Signature verified. Login Successful.")
    elif message_type in ignore_messages:
        pass
    else:
        print(f"{message_type}: {message_data}")


def on_ws_error(ws, error):
    if isinstance(error, websocket.WebSocketConnectionClosedException):
        print("Connection closed. Retrying...")
    else:
        traceback.print_tb(error.__traceback__)


def on_ws_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_ws_open(ws):
    print("Opened connection.")
    print("Acquiring signature...")
    signature = asyncio.run(get_signature())
    print("Signature acquired.")
    print("Logging in...")
    ws.send(f"LOGIN={signature}")


def on_chat(data: str):
    player, message = Chat.splitter(data)

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

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **{player["username"]}:** {message} '

    log_message(formatted_chat)

    handle_automod(player, message)

    if player["username"] in amy_accounts and message[:7] != "!luxbot":
        if "noob" in message:
            noob_count = message.count("noob")
            increment_amy_noobs(noob_count)
        if "suck" in message:
            suck_count = message.count("suck")
            increment_amy_sucks(suck_count)

    if len(message) == 0:
        pass
    elif message[0] == "!":
        handle_chat_command(player=player, message=message)
        if development_mode:
            print(f'Chat command received: {message}')
    elif len(message) > 4 and message[:5] == "@mods":
        note = message[5:]
        mod_call = f"{player['username']} is calling for a mod with note: {note}"
        send_modmod_message(payload=mod_call, player="ALL", command="MSG")


def handle_automod(player: dict, message: str):
    automod_flag_words = Db.read_config_row("automod_flag_words")
    message = message.lower()
    for trigger in automod_flag_words:
        if trigger in message:
            message_string = f"**{player['username']} has been muted for using the word: {trigger}**"
            send_modmod_message(payload=message_string, command="MSG", player="ALL")
            length = "24"
            reason = f"Using the word: {trigger}"
            is_ip = "false"
            mute_player(player['username'], length, reason, is_ip)
            Chat.send_chat_message(ws, f"{player['username']} has been axed from chat.")
            break


def on_yell(data: str):
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **SERVER MESSAGE:** {data} '

    log_message(formatted_chat)


def on_dialogue(data: str):
    if data[:5] == "WHOIS":
        cropped_data = data[15:]
        whois_list = cropped_data.split("<br />")[:-1]

        query = "SELECT user FROM permissions WHERE level=3"
        params = tuple()

        account_list = Db.fetch_db(query, params, True)

        level_three_accounts = [x[0] for x in account_list]

        for account in level_three_accounts:
            send_custom_message(account, "WHOIS:" + str(whois_list))
    else:
        print(data)


def on_custom(data: str):
    [player, data_packet] = data.split("~", 1)

    if data_packet == "PLAYER_OFFLINE":
        handle_player_offline(player)

        callback_id = None
        plugin = None
        command = None
        content = data_packet
    else:
        split_packet = data_packet.split(":", 3)
        callback_id = split_packet[0]
        plugin = split_packet[1]
        command = split_packet[2]

        if len(split_packet) > 3:
            content = split_packet[3]
        else:
            content = None

        if development_mode:
            print(
                f"'{plugin}' received '{command}' command with id '{callback_id}' and content '{content}' from {player}.")

    if plugin == "interactor":
        handle_interactor(player, command, content, callback_id)
    elif plugin == "MODMOD":
        handle_modmod(player, command, content, callback_id)


def handle_chat_command(player: dict, message: str):
    reply_string = ""
    reply_needed = False
    command = Chat.generate_command(message)

    if replace_nadebot:
        nadebot_commands = ['!bigbone', '!combat', '!dhm', '!dho', '!distance', '!scripts', '!wiki', '!xp', '!help']
        nadebot_reply = Db.read_config_row("nadebot_reply")
        if command["command"] in nadebot_commands:
            reply_string = f"Sorry {player['username']}, " + nadebot_reply
            reply_needed = True

    if command["command"] == "!luxbot":
        perm_level = permission_level(player['username'])
        if perm_level >= 1:
            if command["sub_command"] is None:
                reply_string = f"Sorry {player['username']}, that is an invalid LuxBot command format."
                reply_needed = True
            else:
                Chat.dispatch(ws, player, command)
        elif perm_level < 0:
            pass
        else:
            reply_string = f"Sorry {player['username']}, you are not authorized to issue LuxBot commands."
            reply_needed = True

    if reply_needed:
        Chat.send_chat_message(ws, reply_string)


def increment_amy_noobs(count: int):
    amy_noobs = int(Db.read_config_row("amy_noobs"))
    amy_noobs += count

    Db.set_config_row("amy_noobs", str(amy_noobs))


def increment_amy_sucks(count: int):
    amy_sucks = int(Db.read_config_row("amy_sucks"))
    amy_sucks += count

    Db.set_config_row("amy_sucks", str(amy_sucks))


def handle_player_offline(player: str):
    if player in online_mods:
        try:
            online_mods.remove(player)
        except ValueError:
            pass
        send_modmod_message(payload=f"{player} has logged out!", command="MSG", player="ALL")
        send_modmod_message(payload=f"remove:{player}", command="LIST", player="ALL")


def poll_online_mods():
    try:
        send_modmod_message(command="HELLO", player="ALL", payload="0:0")
    except:
        print("Online mod poll attempted while connection closed.")


def mute_player(player: str, length: str, reason: str, is_ip: str):
    # websocket.send("MUTE=" + username_target + "~" + hours + "~" + reason + "~" + is_ip);
    mute_string = f"MUTE={player}~{length}~{reason}~{is_ip}"
    ws.send(f"{mute_string}")


def update_permission(player: str, updated_player: str, level: str):
    level = int(level)

    if not -1 <= level <= 3:
        send_custom_message(player, "Invalid permission level. Must be between -1 and 3.")
        return

    query = """
                INSERT INTO permissions(user, level) VALUES(?1, ?2)
                ON CONFLICT(user) DO UPDATE SET level=?2
            """
    params = (updated_player, level)
    Db.set_db(query, params)

    send_custom_message(player, f"{updated_player} permission level set to {level}.")


def permission_level(player: str):
    query = "SELECT level FROM permissions WHERE user=?"
    params = (player, )

    level = Db.fetch_db(query, params, False)
    if level is None:
        return 0
    else:
        return level[0]


def send_generic(command: str):
    ws.send(command)


def handle_interactor(player: str, command: str, content: str, callback_id: str):
    interactor_commands = ["echo", "chatecho", "relay", "togglenadebotreply", "nadesreply", "speak", "mute",
                           "permissions", "triggers", "pets", "help", "whois", "generic", "pet_titles", ]
    perm_level = permission_level(player)
    if perm_level < 2:
        send_custom_message(player, "Permission level 2 or greater required to interact with LuxBot.")
    elif perm_level >= 2:
        if command == "echo":
            send_custom_message(player, content)
        elif command == "chatecho":
            chat_string = f"{player} echo: {content}"
            Chat.send_chat_message(ws, chat_string)
        elif command == "relay":
            recipient = content.split(":")[0]
            message = content.split(":")[1]
            send_custom_message(recipient, message)
        elif command == "triggers":
            trigger_list = Db.read_config_row("automod_flag_words")
            split_sub_command = content.split(";")
            subcommand = split_sub_command[0]
            payload = split_sub_command[1]
            if subcommand == "add":
                trigger_list.append(payload.strip())
                Db.set_config_row("automod_flag_words", trigger_list)
                send_custom_message(player, f"{payload} has been added to automod triggers.")
            elif subcommand == "remove":
                trigger_list.remove(payload.strip())
                Db.set_config_row("automod_flag_words", trigger_list)
                send_custom_message(player, f"{payload} has been removed from the automod triggers.")
        elif command == "togglenadebotreply":
            global replace_nadebot
            replace_nadebot = not replace_nadebot
            if replace_nadebot:
                status = "on"
            else:
                status = "off"
            send_custom_message(player, f"Nadebot replies are now {status}.")
        elif command == "nadesreply":
            Db.set_config_row("nadebot_reply", content)
            nadebot_reply = Db.read_config_row("nadebot_reply")
            send_custom_message(player, f"New NadeBot reply set. New reply is:")
            send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
        elif command == "speak":
            Chat.send_chat_message(ws, content)
        elif command == "pet_titles":
            query = "SELECT title FROM pet_links"
            params = tuple()
            raw_title_list = Db.fetch_db(query, params, True)
            title_list = []
            for title_tuple in raw_title_list:
                title_list.append(title_tuple[0].capitalize())
            stringified_list = ", ".join(title_list)
            title_string = f"{stringified_list}"
            wrapped_message = textwrap.wrap(title_string, 240)
            for message in wrapped_message:
                send_custom_message(player, message)
        elif command == "pets":
            split_sub_command = content.split(";")
            if len(split_sub_command) != 4:
                send_custom_message(player, f"Invalid syntax. (pets:add;pet;title;link)")
            else:
                subcommand = split_sub_command[0]
                pet = split_sub_command[1]
                title = split_sub_command[2]
                link = split_sub_command[3]

                pet_data = (title, pet, link)

                if subcommand == "add":
                    add_pet(pet_data, player)
                    send_custom_message(player, f"{pet} link added with title: {title}")
                elif subcommand == "remove":
                    send_custom_message(player, f"Remove feature not added.")
        elif command == "help":
            if content is None:
                help_string = "Command List"
                for com in interactor_commands:
                    help_string += f" | {com}"
                send_custom_message(player, help_string)
                send_custom_message(player, "help:command will give a brief description of the command.")
            else:
                help_string = Interactor.get_help_string(content)
                send_custom_message(player, help_string)

            if content == "nadesreply":
                nadebot_reply = Db.read_config_row("nadebot_reply")
                send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
            elif content == "triggers":
                trigger_list = Db.read_config_row("automod_flag_words")
                send_custom_message(player, f"Current triggers: {trigger_list}")
            elif content == "permissions":
                query = f"SELECT * FROM permissions"
                params = tuple()
                perms_list = Db.fetch_db(query, params, True)
                perms_string = f"Current permissions: {perms_list}"
                wrapped_message = textwrap.wrap(perms_string, 240)
                for message in wrapped_message:
                    send_custom_message(player, message)

        elif command in ["permissions", "mute", "whois", "generic"]:
            if perm_level < 3:
                send_custom_message(player, "Permission level 3 required.")
        else:
            send_custom_message(player, f"{command} is not a valid interactor command.")
    if perm_level >= 3:
        if command == "permissions":
            split_command = content.split(";")
            if len(split_command) == 2:
                updated_player = split_command[0]
                level = split_command[1]
                update_permission(player, updated_player, level)
            else:
                send_custom_message(player, "Invalid syntax. Must be of form 'permissions:player;level'")
        elif command == "mute":
            if content is None:
                split_data = None
                send_custom_message(player, "Invalid mute format. Must be mute:player;reason;length;is_ip")
            else:
                split_data = content.split(";")

            if len(split_data) == 4 and split_data is not None:
                target = split_data[0]
                reason = split_data[1]
                length = split_data[2]
                is_ip = split_data[3]

                mute_player(target, length, reason, is_ip)
                send_custom_message(player, f"{target} has been successfully muted for {length} hours.")
            else:
                send_custom_message(player, "Invalid mute format. Must be mute:player;reason;length;is_ip")
        elif command == "whois":
            if content is None:
                send_custom_message(player, "Invalid syntax. Specify a target.")
            else:
                Chat.send_chat_message(ws, f"/whois {content}")
        elif command == "generic":
            send_generic(content)
            send_custom_message(player, f"Generic websocket command sent: {content}")


def handle_modmod(player: str, command: str, content: str, callback_id: str):
    online_mods.add(player)
    if command == "HELLO":
        if content == "1:0":
            send_modmod_message(payload=f"{player} has logged in!", command="MSG", player="ALL")
            send_modmod_message(payload=f"add:{player}", command="LIST", player="ALL")
            mod_string = ""
            for mod in online_mods:
                mod_string += f"{mod},"
            send_modmod_message(payload=f"list:{mod_string[:-1]}", command="LIST", player=player)
        elif content == "0:0":
            pass
    elif command == "MODCHAT":
        send_modmod_message(payload=f"{player}: {content}", command="MSG", player="ALL")
    elif command == "MODLIST":
        mod_string = "Mod accounts online at last poll"
        for mod in online_mods:
            capital_mod = ""
            for word in mod.split(" "):
                capital_mod += f"{word.capitalize()} "
            mod_string += f" | {capital_mod}"
        send_modmod_message(payload=mod_string, command="MSG", player=player)


def send_modmod_message(**kwargs):
    payload = kwargs.get("payload", None)
    command = kwargs.get("command", None)
    player = kwargs.get("player", None)
    message = f"MODMOD:{command}:{payload}"
    if player == "ALL":
        for account in online_mods.copy():
            send_custom_message(account, message)
    else:
        send_custom_message(player, message)


def send_custom_message(player: str, content: str):
    custom_string = f"CUSTOM={player}~{content}"
    ws.send(f"{custom_string}")


def log_message(message: str):
    if development_mode:
        testing_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())

        with open('chat.log', 'a', encoding="utf-8") as the_file:
            the_file.write(message + '\n')
    else:
        dh_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())
        lbt_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())


def add_config_to_database(key: str, value: str | list):
    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    query = "INSERT INTO configs VALUES (?, ?)"
    params = (key, encoded_string)

    Db.set_db(query, params)


def add_pet(pet_data: tuple, player: str):
    query = "INSERT INTO pet_links VALUES (?, ?, ?)"

    try:
        Db.set_db(query, pet_data)
    except sqlite3.IntegrityError as e:
        print(e)
        send_custom_message(player, f"Link not added, '{pet_data[0]}' already exists.")


if __name__ == "__main__":
    env_consts = set_env_consts()
    development_mode = is_development_mode()
    online_mods = set()

    replace_nadebot = False

    lbt_webhook = SyncWebhook.from_url(env_consts["LBT_DISCORD_HOOK_URL"])
    dh_webhook = SyncWebhook.from_url(env_consts["DH_DISCORD_HOOK_URL"])
    if development_mode:
        testing_webhook = SyncWebhook.from_url(env_consts["TESTING_HOOK_URL"])

    timer = RepeatTimer(60, poll_online_mods)
    timer.start()

    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("wss://server1.idle-pixel.com",
                                on_open=on_ws_open,
                                on_message=on_ws_message,
                                on_error=on_ws_error,
                                on_close=on_ws_close)

    ws.run_forever(dispatcher=rel,
                   reconnect=60,
                   sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly, no SSL cert
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
    timer.cancel()
