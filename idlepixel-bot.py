import asyncio
import random
import sys
import os
from playwright.async_api import async_playwright
from datetime import datetime
from discord import SyncWebhook
from jokeapi import Jokes


def get_env_var(env_var: str):
    try:
        return os.environ[env_var]
    except KeyError:
        print("Missing environment variable")
        raise


env_consts = {
    "IP_USERNAME": "",
    "IP_PASSWORD": "",
    "TESTING_HOOK_URL": "",
    "LBT_DISCORD_HOOK_URL": "",
    "DH_DISCORD_HOOK_URL": ""
}

for key in env_consts:
    env_consts[key] = get_env_var(key)

idle_pixel_connected = False
online_mods = set()
whitelisted_accounts = ["lux", "axe", "luxferre", "luxchatter", "godofnades", "amyjane1991"]
cl_args = sys.argv
development_mode = False
global replace_nadebot
replace_nadebot = False
nadebot_commands = ["!bigbone",  "!combat", "!dhm", "!dho", "!event", "!rocket", "!wiki", "!xp"]
global nadebot_reply
nadebot_reply = "Nadess  bot is offline atm."
automod_flag_words = ["nigger", "nigga", "fag", "chink", "beaner", ]

for arg in cl_args:
    if arg == "-d":
        print("Development mode enabled.")
        development_mode = True

global page

lbt_webhook = SyncWebhook.from_url(env_consts["LBT_DISCORD_HOOK_URL"])
dh_webhook = SyncWebhook.from_url(env_consts["DH_DISCORD_HOOK_URL"])
testing_webhook = SyncWebhook.from_url(env_consts["TESTING_HOOK_URL"])


def on_web_socket(ws):
    print(f"WebSocket opened: {ws.url}")
    ws.on("framesent", on_message_send)
    ws.on("framereceived", receive_message)
    ws.on("close", handle_disconnect)


def on_message_send(sent_message: str):
    if development_mode:
        print("Sent: " + sent_message)


async def receive_message(raw_message: str):
    split_message = raw_message.split("=", 1)
    if len(split_message) > 1:
        [message_type, message_data] = split_message
    else:
        message_type = raw_message
        message_data = ""

    if message_type == "SET_ITEMS":
        pass
        # print(f"{message_type}: {message_data}")
    elif message_type == "CHAT":
        await on_chat(message_data)
    elif message_type == "YELL":
        on_yell(message_data)
    elif message_type == "CUSTOM":
        await on_custom(message_data)
    else:
        print(f"{message_type}: {message_data}")


async def on_chat(data: str):
    data_split = data.split("~")
    message_data = {
        "username": data_split[0],
        "sigil": data_split[1],
        "tag": data_split[2],
        "level": data_split[3],
        "message": data_split[4].replace("@", "")
    }

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **{message_data["username"]}:** {message_data["message"]} '

    log_message(formatted_chat)

    await handle_automod(message_data)

    if message_data["message"][0] == "!":
        await handle_chat_command(player=message_data["username"], message=message_data["message"])
        if development_mode:
            print(f'Chat command received: {message_data["message"]}')


async def handle_automod(data):
    player = data["username"]
    message = data["message"].lower()
    for trigger in automod_flag_words:
        if trigger in message:
            message_string = f"{data['username']} sent a message with the blacklisted word: {trigger}."
            await send_modmod_message(payload=message_string, command="MSG", player="ALL")
            length = "24"
            reason = f"Using the word: {trigger}"
            is_ip = "false"
            await mute_player(player, length, reason, is_ip)
            await send_chat_message(f"{player} has been muted by me.")
            break


def on_yell(data: str):
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    formatted_chat = f'*[{current_time}]* **SERVER MESSAGE:** {data} '

    log_message(formatted_chat)


async def on_custom(data: str):
    [player, data_packet] = data.split("~")

    if data_packet == "PLAYER_OFFLINE":
        await handle_player_offline(player)

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
        await handle_interactor(player, command, content, callback_id)
    elif plugin == "MODMOD":
        await handle_modmod(player, command, content, callback_id)


async def handle_chat_command(player: str, message: str):
    reply_string = ""
    reply_needed = False
    split_message = message.split(" ", 1)
    command = split_message[0]
    if len(split_message) > 1:
        payload = split_message[1]
    else:
        payload = None

    if replace_nadebot:
        if command in nadebot_commands:
            reply_string = f"Sorry {player}, " + nadebot_reply
            reply_needed = True

    if command[:7] == "!luxbot":
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
            elif sub_command == "scripts":
                reply_string = f"https://idle-pixel.wiki/index.php/Scripts"
                reply_needed = True
            elif sub_command == "vega":
                vega_links = {
                    "santa": "https://prnt.sc/iLEELtvirILy",
                    "paper": "https://prnt.sc/5Ga3Tsl0oay6",
                    "face": "https://prnt.sc/WbVMwBw63d9g",
                    "attack": "https://prnt.sc/dASKN1prvBJ9",
                    "kitten": "https://prnt.sc/rp_t4eiSGM1h",
                    "hide": "https://prnt.sc/aPvMRNNkbbEE",
                    "beans": "https://prnt.sc/_XCgGFh3jIbv",
                    "borgor": "https://prnt.sc/HwewSCtGlJvM",
                    "banana": "https://prnt.sc/pSs3rVcPlfHE",
                    "gamer": "https://prnt.sc/yEQaV346hY7c",
                    "peer": "https://prnt.sc/LgPFXqfyk3Gi",
                    "axolotl": "https://prnt.sc/ev3f_BkI6CsN",
                    "noodle": "https://prnt.sc/TTYHSPbazWbJ",
                    "reader": "https://prnt.sc/N3oVzhnb3N80",
                }
                if payload is not None:
                    try:
                        reply_string = vega_links[payload]
                    except KeyError:
                        reply_string = "Invalid Vega."
                else:
                    random_vega = random.choice(list(vega_links))
                    reply_string = f"Your random Vega is: {random_vega}: {vega_links[random_vega]}"

                reply_needed = True
            elif sub_command == "joke":
                j = await Jokes()
                joke = await j.get_joke(
                    category=["pun"],
                    blacklist=["nsfw", "religious", "political", "racist", "sexist", "explicit"],
                    joke_type="single"
                )
                reply_string = joke["joke"]
                reply_needed = True
            elif sub_command == "import":
                if payload == "antigravity":
                    reply_string = "https://xkcd.com/353"
                    reply_needed = True
            else:
                if sub_command is not None:
                    reply_string = f"Sorry {player}, that is an invalid LuxBot command."
                    reply_needed = True
        elif player == "flymanry":
            reply_string = f"Never whitelisting you Fly."
            reply_needed = True
        else:
            reply_string = f"Sorry {player}, you are not authorized to issue LuxBot commands."
            reply_needed = True

    if reply_needed:
        await send_chat_message(reply_string)


async def handle_player_offline(player: str):
    if player in online_mods:
        try:
            online_mods.remove(player)
        except ValueError:
            pass
        await send_modmod_message(payload=f"{player} has logged out!", command="MSG", player="ALL")


async def poll_online_mods():
    await send_modmod_message(command="HELLO", player="ALL", payload="0:0")


async def mute_player(player, length, reason, is_ip):
    # websocket.send("MUTE=" + username_target + "~" + hours + "~" + reason + "~" + is_ip);
    mute_string = f"MUTE={player}~{length}~{reason}~{is_ip}"
    await page.evaluate(f"window.websocket.send('{mute_string}')")


async def handle_interactor(player: str, command: str, content: str, callback_id: str):
    interactor_commands = ["echo", "chatecho", "relay", "whitelist", "blacklist", "togglenadebotreply", "nadesreply", "help"]
    if player in whitelisted_accounts:
        if command == "echo":
            await send_custom_message(player, content)
        elif command == "chatecho":
            chat_string = f"{player} echo: {content}"
            await send_chat_message(chat_string)
        elif command == "relay":
            recipient = content.split(":")[0]
            message = content.split(":")[1]
            await send_custom_message(recipient, message)
        elif command == "whitelist":
            whitelisted_accounts.append(content.strip())
            await send_custom_message(player, f"{content} has been temporarily whitelisted to issue interactor commands.")
        elif command == "blacklist":
            whitelisted_accounts.remove(content.strip())
            await send_custom_message(player, f"{content} has been removed from the interactor whitelist.")
        elif command == "togglenadebotreply":
            global replace_nadebot
            replace_nadebot = not replace_nadebot
            if replace_nadebot:
                status = "on"
            else:
                status = "off"
            await send_custom_message(player, f"Nadebot replies are now {status}.")
        elif command == "nadesreply":
            content = content.replace("'", "")
            global nadebot_reply
            nadebot_reply = content
            await send_custom_message(player, f"New NadeBot reply set. New reply is:")
            await send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
        elif command == "joke":
            j = await Jokes()  # Initialise the class
            joke = await j.get_joke(
                category=["pun"],
                blacklist=["nsfw", "religious", "political", "racist", "sexist", "explicit"],
                joke_type="single"
            )
            await send_custom_message(player, joke["joke"])
        elif command == "help":
            if content is None:
                help_string = "Command List"
                for com in interactor_commands:
                    help_string += f" | {com}"
                await send_custom_message(player, help_string)
                await send_custom_message(player, "help:command will give a brief description of the command.")
            elif content == "echo":
                help_string = "Echos message as custom. (echo:message)"
                await send_custom_message(player, help_string)
            elif content == "chatecho":
                help_string = "Echos message into chat. (chatecho:message)"
                await send_custom_message(player, help_string)
            elif content == "relay":
                help_string = "Passes on message to another account. (relay:account:message)"
                await send_custom_message(player, help_string)
            elif content == "whitelist":
                help_string = "Temporarily adds account to whitelist. (whitelist:account)"
                await send_custom_message(player, help_string)
                whitelist_string = "Whitelisted accounts"
                for account in whitelisted_accounts:
                    whitelist_string += f" | {account}"
                await send_custom_message(player, whitelist_string)
            elif content == "blacklist":
                help_string = "Temporarily removes account from whitelist. (blacklist:account)"
                await send_custom_message(player, help_string)
            elif content == "togglenadebotreply":
                help_string = "Toggles bot responses to Nadess bot commands."
                await send_custom_message(player, help_string)
            elif content == "nadesreply":
                help_string = "Sets a new reply string for Nadess bot commands. (nadesreply:reply_string) Current string is:"
                await send_custom_message(player, help_string)
                await send_custom_message(player, f"Sorry <player>, {nadebot_reply}.")
            elif content == "help":
                help_string = "Lists commands or gives a description of a command. (help:command)"
                await send_custom_message(player, help_string)
            else:
                help_string = "Invalid help command. Should be of format (help:command)"
                await send_custom_message(player, help_string)
        else:
            await send_custom_message(player, f"{command} is not a valid interactor command.")
    else:
        await send_custom_message(player, "403: Interactor request denied. Account not approved.")


async def handle_modmod(player: str, command: str, content: str, callback_id: str):
    online_mods.add(player)
    if command == "HELLO":
        if content == "1:0":
            await send_modmod_message(payload=f"{player} has logged in!", command="MSG", player="ALL")
        elif content == "0:0":
            if player == "luxferre":
                await poll_online_mods()
    elif command == "MODCHAT":
        await send_modmod_message(payload=f"{player}: {content}", command="MSG", player="ALL")
    elif command == "MODLIST":
        mod_string = "Mod accounts online at last poll"
        for mod in online_mods:
            capital_mod = ""
            for word in mod.split(" "):
                capital_mod += f"{word.capitalize()} "
            mod_string += f" | {capital_mod}"
        await send_modmod_message(payload=mod_string, command="MSG", player=player)


async def send_modmod_message(**kwargs):
    payload = kwargs.get("payload", None)
    command = kwargs.get("command", None)
    player = kwargs.get("player", None)
    message = f"MODMOD:{command}:{payload}"
    if player == "ALL":
        for account in online_mods.copy():
            await send_custom_message(account, message)
    else:
        await send_custom_message(player, message)


async def send_custom_message(player: str, content: str):
    custom_string = f"CUSTOM={player}~{content}"
    await page.evaluate(f"window.websocket.send('{custom_string}')")


async def send_chat_message(chat_string: str):
    chat_string = chat_string.replace("`", "")
    chat_string = chat_string.replace("'", "")
    chat_string = f"window.websocket.send(`CHAT={chat_string}`)"
    await page.evaluate(chat_string)


def log_message(message: str):
    if development_mode:
        testing_webhook.send(message)

        with open('chat.log', 'a', encoding="utf-8") as the_file:
            the_file.write(message + '\n')
    else:
        dh_webhook.send(message)
        lbt_webhook.send(message)


async def handle_disconnect():
    print("Disconnect registered.")
    global idle_pixel_connected
    idle_pixel_connected = False
    await asyncio.sleep(60)
    await connect_to_idlepixel()


async def connect_to_idlepixel():
    print("Attempting connection...")
    await page.goto("https://idle-pixel.com/login/")
    await page.locator('[id=id_username]').fill(env_consts["IP_USERNAME"])
    await page.locator('[id=id_password]').fill(env_consts["IP_PASSWORD"])
    await page.locator("[id=login-submit-button]").click()
    global idle_pixel_connected
    idle_pixel_connected = True
    print("Connection established.")


async def main():
    run_forever = True
    global page
    timed_out = False

    async with async_playwright() as p:
        browser_type = p.chromium
        browser = await browser_type.launch_persistent_context("persistent_context")
        page = await browser.new_page()

        if run_forever:
            print('Press CTRL-D to stop')
            reader = asyncio.StreamReader()
            pipe = sys.stdin
            loop = asyncio.get_running_loop()
            if not idle_pixel_connected:
                await connect_to_idlepixel()
            page.on("websocket", on_web_socket)
            if timed_out:
                await handle_disconnect()
            await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), pipe)
            async for line in reader:
                print(f'Got: {line.decode()!r}')
        else:
            await browser.close()


asyncio.run(main())
