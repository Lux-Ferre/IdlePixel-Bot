import asyncio
import os
import random
import discord
import requests
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import websocket
import sys
from datetime import datetime, timedelta, timezone
from discord import SyncWebhook
import rel
import ssl
import traceback
from dataclasses import dataclass

from utils import RepeatTimer, Db, Utils
from chat import Chat
from interactor import Interactor


def get_env_var(env_var: str) -> str:
    """Return environment variable of key ``env_var``. Will stop application if not found."""
    try:
        return os.environ[env_var]
    except KeyError:
        print(f"Missing environment variable: {env_var}")
        raise


def get_env_consts() -> dict:
    """Return dict containing all required environment variables at application launch."""
    env_const_dict = {
        "IP_USERNAME": "",
        "IP_PASSWORD": "",
        "TESTING_HOOK_URL": "",
        "LBT_DISCORD_HOOK_URL": "",
        "DH_DISCORD_HOOK_URL": "",
        "EVENT_HOOK_URL": "",
        "PASTEBIN_API_KEY": "",
    }

    for key in env_const_dict:
        env_const_dict[key] = get_env_var(key)

    return env_const_dict


def is_development_mode():
    """Return True if development mode command line argument present."""
    cl_args = sys.argv
    dev_mode = False

    for arg in cl_args:
        if arg == "-d":
            print("Development mode enabled.")
            dev_mode = True

    return dev_mode


async def get_signature() -> str:
    """
    Uses a Playwright headless browser to authenticate login.

    User authentication is done via HTTP, the server sends an authentication signature to the client which is then
    sent as the first frame over the websocket.

    A browser is used to comply with CORS security measures.

    :return: Authentication signature
    :rtype: str
    """
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


def on_ws_message(ws, raw_message: str):
    """
    Primary handler for received websocket frames.

    Parses DHP websocket format by splitting the data into the frame type and payload.
    Passes payload on to appropriate secondary handlers, defaults to printing unknown frame types.

    :param ws: websocket
    :param raw_message: String containing websocket data
    :type raw_message: str
    """
    ignore_messages = ["SET_COUNTRY"]
    split_message = raw_message.split("=", 1)
    if len(split_message) > 1:
        [message_type, message_data] = split_message
    else:
        message_type = raw_message
        message_data = ""

    if message_type == "SET_ITEMS":
        new_data = Utils.parse_item_data(message_data)
        global_vars_instance.item_data.update(new_data)

        if "event_upcomming_timer" in global_vars_instance.item_data:
            event_timer = int(global_vars_instance.item_data["event_upcomming_timer"])
            event_type = global_vars_instance.item_data["event_name"]
            running_timer = 1
            if "event_active_timer" in global_vars_instance.item_data:
                running_timer = int(global_vars_instance.item_data["event_active_timer"])
            if event_timer > 0 and not global_vars_instance.event_countdown_started:
                start_event_countdown(event_timer=event_timer, event_type=event_type)
            if running_timer < 0 and global_vars_instance.event_countdown_started:
                end_event(event_type=event_type)
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
    elif message_type == "EVENT_GLOBAL_PROGRESS":
        global_vars_instance.raw_event_scores = message_data
    elif message_type in ignore_messages:
        pass
    else:
        print(f"{message_type}: {message_data}")


def on_ws_error(ws, error):
    """
    Top level error handler.

    If websocket connection drops, will print a retrying message to notify before ``rel`` retries.
    Otherwise, prints timestamp, error, and traceback.

    :param ws: websocket
    :param error: Exception object
    """

    if isinstance(error, websocket.WebSocketConnectionClosedException):
        print("Connection closed. Retrying...")
    else:
        print(datetime.now().strftime("%d/%m/%Y , %H:%M:%S"))
        print(error)
        traceback.print_tb(error.__traceback__)


def on_ws_close(ws, close_status_code, close_msg):
    """Called when websocket is closed by server."""
    print("### closed ###")


def on_ws_open(ws):
    """
    Called when websocket opens.

    Acquires authentication signature then sends it as first frame over websocket.

    :param ws: websocket
    """
    print("Opened connection.")
    print("Acquiring signature...")
    signature = asyncio.run(get_signature())
    print("Signature acquired.")
    print("Logging in...")
    ws.send(f"LOGIN={signature}")


def on_chat(data: str):
    """
    Handler for ``CHAT`` websocket frames.

    Passes player information and chat message into each further function that requires it. In order these are:
        - Automoderation
        - Statistic tracking
        - Dynamic statistic command
        - Discord mirror
        - Formatted chat commands
        - Mod caller
    :param data:
    :type data: str
    """

    player, message = Chat.splitter(data)

    handle_automod(player, message)

    Chat.track_chats(ws, player, message)

    perm = Utils.permission_level(player["username"])

    dynamic_command_tiggers = ["chat stat", "gimme", "fetch", "look up", "statistic"]

    trigger_found = False

    if perm >= 0:
        if message[0] != "!" and "luxbot" in message.lower():
            for trigger in dynamic_command_tiggers:
                if trigger in message.lower():
                    trigger_found = True

    if trigger_found:
        Chat.get_chat_stat(ws, player, message.lower())

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **{player["username"]}:** {message} '

    log_message(formatted_chat)

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
    """
    Scans chat messages for restricted words and issues a mute instruction if one is present.

    Restricted words are stored in the configs db table.

    :param player: Parsed player information [username, sigil, tag, level]
    :type player: dict
    :param message: Chat message content
    :type message: str
    """
    flag_words_dict = Db.read_config_row("automod_flag_words")

    automod_replies = [
        f"{player['username']} has been axed from chat.",
        f"{player['username']} has been defenestrated.",
        f"Buh-bye {player['username']}!",
        "𝔹 𝕆 ℕ 𝕂 !",
        f"{player['username']} is taking an enforced break from chat.",
    ]

    automod_flag_words = flag_words_dict["word_list"].split(",")
    automod_flag_words += [" fag", "fag "]
    message = message.lower()
    for trigger in automod_flag_words:
        if trigger in message:
            message_string = f"**{player['username']} has been muted for using the word: {trigger}**"
            send_modmod_message(payload=message_string, command="MSG", player="ALL")
            length = "24"
            reason = f"Using the word: {trigger}"
            is_ip = "false"
            Utils.mute_player(ws, player['username'], length, reason, is_ip)
            Chat.send_chat_message(ws, random.choice(automod_replies))
            return


def on_yell(message: str):
    """
    Handler for ``YELL`` websocket frames (called server messages in chat.)

    Mirrors messages to discord.
    Parses and passes message to chat stat tracker.

    :param message: Yell data payload
    :type message: str
    :return:
    """

    now = datetime.now()
    current_time = now.strftime("%H:%M")
    formatted_chat = f'*[{current_time}]* **SERVER MESSAGE:** {message} '

    log_message(formatted_chat)

    yell_dict = {"type": "", "player": message.split(" ")[0]}

    if "agrodon" in message.lower():
        Chat.send_chat_message(ws, "Wizard hax!")
    elif "i am smitty" in message.lower():
        Chat.send_chat_message(ws, "Dev hax!")
    elif "ma25" in message.lower():
        Chat.send_chat_message(ws, "Congradulations sweetie! Mwah⁓")

    if "found a diamond" in message:
        yell_dict["type"] = "diamond"
    elif "found a legendary blood diamond" in message:
        yell_dict["type"] = "blood_diamond"
    elif "encountered a gem goblin" in message:
        yell_dict["type"] = "gem_goblin"
    elif "encountered a blood gem goblin" in message:
        yell_dict["type"] = "blood_goblin"
    elif "looted a monster sigil" in message:
        yell_dict["type"] = "sigil"
    elif "has just reached level 100" in message:
        yell_dict["type"] = "max_level"
    elif "has completed the elite" in message:
        yell_dict["type"] = "elite_achievement"
    elif "gold armour" in message:
        yell_dict["type"] = "gold_armour"
    else:
        yell_dict["type"] = "unknown"

    Chat.track_yells(yell_dict)


def on_dialogue(data: str):
    """
    Handler for ``DIALOGUE`` websocket frames.

    Parses ``WHOIS`` dialogues, sending the player list over ``CUSTOM`` to accounts with level 3 permissions.
    Prints data otherwise.

    :param data:
    :type data: str
    """
    if data[:5] == "WHOIS":
        cropped_data = data[15:]
        whois_list = cropped_data.split("<br />")[:-1]

        query = "SELECT user FROM permissions WHERE level=3"
        params = tuple()

        account_list = Db.fetch_db(query, params, True)

        level_three_accounts = [x[0] for x in account_list]

        for account in level_three_accounts:
            Utils.send_custom_message(ws, account, "LuxBot:WHOIS:" + str(whois_list))
    else:
        print(data)


def on_custom(data: str):
    """
    Handler for ``CUSTOM`` websocket frames.

    Customs are designed for sending data between players sent via the server.
    Server will respond with a ``PLAYER_OFFLINE`` custom if one is sent to an offline player.

    Customs are parsed according to Anwin's formatting for the IP+ client mod library:
        - CUSTOM=player_username~callback_id:plugin_name:command:payload

    Data is then passed to further handlers according to which plugin has sent the custom message.

    :param data:
    :type data: str
    """
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
    """
    Parses formatted chat commands.
    Currently only handles LuxBot commands.
    Checks if player has valid permissions then passes data into Chat.dispatcher.

    :param player: Parsed player information [username, sigil, tag, level]
    :type player: dict
    :param message: Raw chat message containing formatted command
    :type message: str
    """
    reply_string = ""
    reply_needed = False
    command = Chat.generate_command(message)

    if command["command"] == "!luxbot":
        perm_level = Utils.permission_level(player['username'])
        if perm_level >= 1:
            if command["sub_command"] is None:
                reply_string = f"Sorry {player['username']}, that is an invalid LuxBot command format."
                reply_needed = True
            else:
                errored, msg = Chat.dispatcher(ws, player, command)
                if errored:
                    print(msg)
                    reply_string = f"Sorry {player['username']}, that is an invalid LuxBot command."
                    reply_needed = True
        elif perm_level < 1:
            pass
        else:
            reply_string = f"Sorry {player['username']}, you are not authorized to issue LuxBot commands."
            reply_needed = True

    if reply_needed:
        Chat.send_chat_message(ws, reply_string)


def handle_player_offline(player: str):
    """Removes player from online_mods set"""
    if player in online_mods:
        try:
            online_mods.remove(player)
        except ValueError:
            pass
        send_modmod_message(payload=f"{player} has logged out!", command="MSG", player="ALL")
        send_modmod_message(payload=f"remove:{player}", command="LIST", player="ALL")


def poll_online_mods():
    """Sends ``CUSTOM`` messages formatted for the ModMod plugin to check if mods are still online."""
    try:
        send_modmod_message(command="HELLO", player="ALL", payload="0:0")
    except:     # Specifying exception type caused further problems. GH issue #25
        print("Online mod poll attempted while connection closed.")


def handle_interactor(player: str, command: str, content: str, callback_id: str):
    """
    Simple parser that passes Interactor plugin data onto Interactor.dispatcher.
    :param player: Player username
    :type player: str
    :param command: Interactor command
    :type command: str
    :param content: Sub commands and payload for interactor command
    :type content: str
    :param callback_id: IP+ framework callback ID
    :type callback_id: str
    """
    command_data = {
        "player": player,
        "command": command,
        "content": content,
        "callback_id": callback_id
    }

    response = Interactor.dispatcher(ws, False, command_data)

    Utils.send_custom_message(ws, player, response)


def handle_modmod(player: str, command: str, content: str, callback_id: str):
    """
    Handles custom messages sent by the ModMod client script.

    Adds account that sent the message to the online mods set.

    Informs currently online mods when a mod logs in or out.

    Relays messages for the in-game mod chat room.

    :param player: Username of account that sent the command
    :type player: str
    :param command: Command type
    :type command: str
    :param content: Sub commands and payload
    :type content: str
    :param callback_id: IP+ framework callback ID
    :type callback_id: str
    """
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
    """Sends ``CUSTOM`` message formatted for ModMod client script."""
    payload = kwargs.get("payload", None)
    command = kwargs.get("command", None)
    player = kwargs.get("player", None)
    message = f"MODMOD:{command}:{payload}"
    if player == "ALL":
        for account in online_mods.copy():
            Utils.send_custom_message(ws, account, message)
    else:
        Utils.send_custom_message(ws, player, message)


def log_message(message: str):
    """Posts formatted chat messages to the DH discord server. Also to a testing server and file if in dev mode."""
    if development_mode:
        testing_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())

        with open('chat.log', 'a', encoding="utf-8") as the_file:
            the_file.write(message + '\n')
    else:
        dh_webhook.send(content=message, allowed_mentions=discord.AllowedMentions.none())


def start_event_countdown(event_timer: int, event_type: str):

    global_vars_instance.event_countdown_started = True

    current_time = datetime.now(timezone.utc)
    time_delta = timedelta(seconds=event_timer)

    event_start_object = current_time + time_delta
    timestamp = int(event_start_object.timestamp())
    event_start_string = f"<t:{timestamp}:f>"

    global_vars_instance.last_event_start_time = event_start_object

    declaration = f"<@&1142985685184282705>, A {event_type} event will start in {event_timer} seconds! ({event_start_string})"

    allowed = discord.AllowedMentions(everyone=False, users=False,
                                      roles=[discord.Object(id="1142985685184282705", type=discord.Role)])

    with requests.Session() as session:
        event_webhook = SyncWebhook.from_url(env_consts["EVENT_HOOK_URL"], session=session)
        event_webhook.send(content=declaration, allowed_mentions=allowed)


def end_event(event_type: str):
    global_vars_instance.event_countdown_started = False
    raw_data = global_vars_instance.raw_event_scores

    parsed_scores = {}
    split_data = raw_data.split("~")
    for i in range(0, len(split_data), 2):
        parsed_scores[split_data[i]] = int(split_data[i + 1])

    sorted_scores = dict(sorted(parsed_scores.items(), key=lambda item: item[1], reverse=True))

    global_vars_instance.parsed_event_score = sorted_scores
    global_vars_instance.last_event_type = event_type

    # end_time = global_vars_instance.last_event_end_time.strftime("%H:%M:%S")

    formatted_scores = f"The last event was a {event_type} event. The final scores were: \n"

    for rank, username in enumerate(sorted_scores):
        new_line = f"{rank + 1}: {username} - {sorted_scores[username]}\n"
        if len(formatted_scores) + len(new_line) < 2000:
            formatted_scores += f"{rank + 1}: {username} - {sorted_scores[username]}\n"
        else:
            break

    allowed = discord.AllowedMentions(everyone=False, users=False,
                                      roles=[discord.Object(id="1142985685184282705", type=discord.Role)])

    with requests.Session() as session:
        event_webhook = SyncWebhook.from_url(env_consts["EVENT_HOOK_URL"], session=session)
        event_webhook.send(content=formatted_scores, allowed_mentions=allowed)


if __name__ == "__main__":
    env_consts = get_env_consts()
    development_mode = is_development_mode()
    online_mods = set()

    @dataclass
    class GlobalizedVars:
        """Class to store pseudo-global variables"""
        item_data: dict
        last_event_type: str = ""
        last_event_ending_declaration: str = ""
        parsed_event_score = dict = {}
        last_event_start_time: datetime = None
        last_event_end_time: datetime = None
        event_countdown_started: bool = False
        raw_event_scores: str = ""

    global_vars_instance = GlobalizedVars(item_data={})

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
                   reconnect=120,
                   sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly, no SSL cert
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
    timer.cancel()
