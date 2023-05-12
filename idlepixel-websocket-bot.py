import asyncio
import os
import discord
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import websocket
import random
import sys
from datetime import datetime
from discord import SyncWebhook
import rel
import ssl
import sqlite3
import json
import base64
from threading import Timer


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


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
        "DH_DISCORD_HOOK_URL": ""
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
    else:
        print(f"{message_type}: {message_data}")


def on_ws_error(ws, error):
    print(error)


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
    data_split = data.split("~")
    message_data = {
        "username": data_split[0],
        "sigil": data_split[1],
        "tag": data_split[2],
        "level": data_split[3],
        "message": data_split[4]
    }

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **{message_data["username"]}:** {message_data["message"]} '

    log_message(formatted_chat)

    handle_automod(message_data)

    if len(message_data["message"]) == 0:
        pass
    elif message_data["message"][0] == "!":
        handle_chat_command(player=message_data["username"], message=message_data["message"])
        if development_mode:
            print(f'Chat command received: {message_data["message"]}')
    elif len(message_data["message"]) > 4 and message_data["message"][:5] == "@mods":
        note = message_data["message"][5:]
        mod_call = f"{message_data['username']} is calling for a mod with note: {note}"
        send_modmod_message(payload=mod_call, player="ALL", command="MSG")


def handle_automod(data: dict):
    automod_flag_words = read_config_row("automod_flag_words")
    player = data["username"]
    message = data["message"].lower()
    for trigger in automod_flag_words:
        if trigger in message:
            message_string = f"**{data['username']} has been muted for using the word: {trigger}**"
            send_modmod_message(payload=message_string, command="MSG", player="ALL")
            length = "24"
            reason = f"Using the word: {trigger}"
            is_ip = "false"
            mute_player(player, length, reason, is_ip)
            send_chat_message(f"{player} has been axed from chat.")
            break


def on_yell(data: str):
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **SERVER MESSAGE:** {data} '

    log_message(formatted_chat)


def on_custom(data: str):
    [player, data_packet] = data.split("~")

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


def handle_chat_command(player: str, message: str):
    reply_string = ""
    reply_needed = False
    split_message = message.split(" ", 1)
    command = split_message[0]
    if len(split_message) > 1:
        payload = split_message[1]
    else:
        payload = None

    if replace_nadebot:
        nadebot_commands = read_config_row("nadebot_commands")
        nadebot_reply = read_config_row("nadebot_reply")
        if command in nadebot_commands:
            reply_string = f"Sorry {player}, " + nadebot_reply
            reply_needed = True

    if command[:7] == "!luxbot":
        whitelisted_accounts = read_config_row("whitelisted_accounts")
        ignore_accounts = read_config_row("ignore_accounts")
        if player in whitelisted_accounts:
            try:
                sub_command = command.split(":", 1)[1]
            except KeyError:
                sub_command = None
                reply_string = f"Sorry {player}, that is an invalid LuxBot command format."
                reply_needed = True

            if sub_command == "echo":
                reply_string = f"Echo: {player}: {payload}"
                reply_needed = True
            elif sub_command == "easter":
                reply_string = f"https://greasyfork.org/en/scripts/463496-idlepixel-easter-2023-tracker"
                reply_needed = True
            elif sub_command == "dho_maps":
                reply_string = f"Offline map solutions: https://prnt.sc/Mdd-AKMIHfLz"
                reply_needed = True
            elif sub_command == "scripts":
                reply_string = f"https://idle-pixel.wiki/index.php/Scripts"
                reply_needed = True
            elif sub_command == "vega":
                vega_links = get_pet_links("vega")
                if payload is not None:
                    try:
                        reply_string = vega_links[payload]
                    except KeyError:
                        reply_string = "Invalid Vega."
                else:
                    random_vega = random.choice(list(vega_links))
                    reply_string = f"Your random Vega is: {random_vega}: {vega_links[random_vega]}"

                reply_needed = True
            elif sub_command == "bear":
                bear_links = get_pet_links("bear")
                if payload is not None:
                    try:
                        reply_string = bear_links[payload]
                    except KeyError:
                        reply_string = "Invalid Bear."
                else:
                    random_bear = random.choice(list(bear_links))
                    reply_string = f"Your random Bear is: {random_bear}: {bear_links[random_bear]}"

                if player == "richie19942":
                    reply_string = "Bawbag, " + reply_string

                reply_needed = True
            elif sub_command == "pet":
                if payload is not None:
                    query = "SELECT title, pet, link FROM pet_links WHERE pet=? ORDER BY RANDOM() LIMIT 1;"
                    params = (payload,)
                else:
                    query = "SELECT title, pet, link FROM pet_links ORDER BY RANDOM() LIMIT 1;"
                    params = tuple()

                res = cur.execute(query, params)

                pet_link = res.fetchone()
                reply_string = f"Your random pet is {pet_link[1].capitalize()}! {pet_link[0].capitalize()}: {pet_link[2]}"

                if player == "richie19942":
                    reply_string = "Bawbag, " + reply_string

                reply_needed = True
            elif sub_command == "import":
                if payload == "antigravity":
                    reply_string = "https://xkcd.com/353"
                    reply_needed = True
            else:
                if sub_command is not None:
                    reply_string = f"Sorry {player}, that is an invalid LuxBot command."
                    reply_needed = True
        elif player in ignore_accounts:
            pass
        else:
            reply_string = f"Sorry {player}, you are not authorized to issue LuxBot commands."
            reply_needed = True

    if reply_needed:
        send_chat_message(reply_string)


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
        print("Connection down.")


def mute_player(player: str, length: str, reason: str, is_ip: str):
    # websocket.send("MUTE=" + username_target + "~" + hours + "~" + reason + "~" + is_ip);
    mute_string = f"MUTE={player}~{length}~{reason}~{is_ip}"
    ws.send(f"{mute_string}")


def handle_interactor(player: str, command: str, content: str, callback_id: str):
    interactor_commands = ["echo", "chatecho", "relay", "togglenadebotreply",
                           "nadesreply", "speak", "mute", "whitelist", "ignores", "triggers", "help"]
    whitelisted_accounts = read_config_row("whitelisted_accounts")
    if player in whitelisted_accounts:
        if command == "echo":
            send_custom_message(player, content)
        elif command == "chatecho":
            chat_string = f"{player} echo: {content}"
            send_chat_message(chat_string)
        elif command == "relay":
            recipient = content.split(":")[0]
            message = content.split(":")[1]
            send_custom_message(recipient, message)
        elif command == "whitelist":
            whitelist = read_config_row("whitelisted_accounts")
            split_sub_command = content.split(";")
            subcommand = split_sub_command[0]
            payload = split_sub_command[1]
            if subcommand == "add":
                whitelist.append(payload.strip())
                set_config_row("whitelisted_accounts", whitelist)
                send_custom_message(player, f"{payload} has been added to the LuxBot whitelist.")
            elif subcommand == "remove":
                whitelist.remove(payload.strip())
                set_config_row("whitelisted_accounts", whitelist)
                send_custom_message(player, f"{payload} has been removed from the LuxBot whitelist.")
        elif command == "ignores":
            ignores = read_config_row("ignore_accounts")
            split_sub_command = content.split(";")
            subcommand = split_sub_command[0]
            payload = split_sub_command[1]
            if subcommand == "add":
                ignores.append(payload.strip())
                set_config_row("ignore_accounts", ignores)
                send_custom_message(player, f"{payload} has been added to the LuxBot ignore list.")
            elif subcommand == "remove":
                ignores.remove(payload.strip())
                set_config_row("ignore_accounts", ignores)
                send_custom_message(player, f"{payload} has been removed from the LuxBot ignore list.")
        elif command == "triggers":
            trigger_list = read_config_row("automod_flag_words")
            split_sub_command = content.split(";")
            subcommand = split_sub_command[0]
            payload = split_sub_command[1]
            if subcommand == "add":
                trigger_list.append(payload.strip())
                set_config_row("automod_flag_words", trigger_list)
                send_custom_message(player, f"{payload} has been added to automod triggers.")
            elif subcommand == "remove":
                trigger_list.remove(payload.strip())
                set_config_row("automod_flag_words", trigger_list)
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
            set_config_row("nadebot_reply", content)
            nadebot_reply = read_config_row("nadebot_reply")
            send_custom_message(player, f"New NadeBot reply set. New reply is:")
            send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
        elif command == "speak":
            send_chat_message(content)
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
                    add_pet(pet_data)
                    send_custom_message(player, f"{pet} link added with title: {title}")
                elif subcommand == "remove":
                    send_custom_message(player, f"Remove feature not added.")
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
        elif command == "help":
            if content is None:
                help_string = "Command List"
                for com in interactor_commands:
                    help_string += f" | {com}"
                send_custom_message(player, help_string)
                send_custom_message(player, "help:command will give a brief description of the command.")
            elif content == "echo":
                help_string = "Echos message as custom. (echo:message)"
                send_custom_message(player, help_string)
            elif content == "chatecho":
                help_string = "Echos message into chat. (chatecho:message)"
                send_custom_message(player, help_string)
            elif content == "relay":
                help_string = "Passes on message to another account. (relay:account:message)"
                send_custom_message(player, help_string)
            elif content == "whitelist":
                whitelist = read_config_row("whitelisted_accounts")
                help_string = f"Add/remove accounts from whitelist. (whitelist:add/remove;account)"
                send_custom_message(player, help_string)
                send_custom_message(player, f"Current whitelist: {whitelist}")
            elif content == "togglenadebotreply":
                help_string = "Toggles bot responses to Nadess bot commands."
                send_custom_message(player, help_string)
            elif content == "nadesreply":
                nadebot_reply = read_config_row("nadebot_reply")
                help_string = "Sets a new reply string for Nadess bot commands. (nadesreply:reply_string) Current string is:"
                send_custom_message(player, help_string)
                send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
            elif content == "triggers":
                trigger_list = read_config_row("automod_flag_words")
                help_string = f"Add/remove automod triggers. (triggers:add/remove;trigger)"
                send_custom_message(player, help_string)
                send_custom_message(player, f"Current triggers: {trigger_list}")
            elif content == "ignores":
                ignores = read_config_row("ignore_accounts")
                help_string = f"Add/remove to/from LuxBot ignore list. (ignores:add/remove;account)"
                send_custom_message(player, help_string)
                send_custom_message(player, f"Current ignore list: {ignores}")
            elif content == "speak":
                help_string = "Relays text to chat as the bot. (speak:content)"
                send_custom_message(player, help_string)
            elif content == "mute":
                help_string = "Mutes target player. (mute:player;reason;length;is_ip)"
                send_custom_message(player, help_string)
            elif content == "help":
                help_string = "Lists commands or gives a description of a command. (help:command)"
                send_custom_message(player, help_string)
            else:
                help_string = "Invalid help command. Should be of format (help:command)"
                send_custom_message(player, help_string)
        else:
            send_custom_message(player, f"{command} is not a valid interactor command.")
    else:
        send_custom_message(player, "403: Interactor request denied. Account not approved.")


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


def send_chat_message(chat_string: str):
    chat_string = f"CHAT={chat_string}"
    ws.send(chat_string)


def log_message(message: str):
    if development_mode:
        testing_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())

        with open('chat.log', 'a', encoding="utf-8") as the_file:
            the_file.write(message + '\n')
    else:
        dh_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())
        lbt_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())


def read_all_data():
    res = cur.execute("SELECT config, data from configs")
    encoded_configs = res.fetchall()
    loaded_configs = {}

    for config in encoded_configs:
        key = config[0]
        encoded_value = config[1]

        if isinstance(encoded_value, str):
            decoded_value = encoded_value
        else:
            decoded_value = json.loads(base64.b64decode(encoded_value))

        loaded_configs[key] = decoded_value

    return loaded_configs


def add_row_to_database(key: str, value: str | list):
    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    query = "INSERT INTO configs VALUES (?, ?)"
    params = (key, encoded_string)

    cur.execute(query, params)

    con.commit()


def read_config_row(key: str) -> list | str | dict:
    query = "SELECT data FROM configs WHERE config=?"
    params = (key, )
    res = cur.execute(query, params)
    encoded_config = res.fetchone()[0]
    decoded_config = json.loads(base64.b64decode(encoded_config))

    if development_mode:
        print(decoded_config)
    return decoded_config


def set_config_row(key: str, value: str | list):
    query = "UPDATE configs SET data=? WHERE config=?"

    stringified_value = json.dumps(value)
    encoded_string = base64.b64encode(stringified_value.encode('utf-8'))

    params = (encoded_string, key)
    cur.execute(query, params)

    con.commit()


def get_pet_links(pet: str):
    query = "SELECT title, link from pet_links WHERE pet=?"
    params = (pet,)
    res = cur.execute(query, params)

    all_links = res.fetchall()
    loaded_links = {}

    for pet in all_links:
        title = pet[0]
        link = pet[1]

        loaded_links[title] = link

    return loaded_links


def add_pet(pet_data: tuple):
    query = "INSERT INTO pet_links VALUES (?, ?, ?)"

    cur.execute(query, pet_data)

    con.commit()


if __name__ == "__main__":
    env_consts = set_env_consts()
    development_mode = is_development_mode()
    online_mods = set()

    con = sqlite3.connect("configs.db")
    cur = con.cursor()

    all_configs = read_all_data()

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
