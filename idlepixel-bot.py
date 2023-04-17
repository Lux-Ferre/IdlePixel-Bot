import asyncio
import sys
import os
from playwright.async_api import async_playwright
from datetime import datetime
from discord import SyncWebhook


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
whitelisted_accounts = ["lux", "axe", "luxferre"]
cl_args = sys.argv
development_mode = False

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
    pass


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
        on_chat(message_data)
    elif message_type == "YELL":
        on_yell(message_data)
    elif message_type == "CUSTOM":
        await on_custom(message_data)
    else:
        print(f"{message_type}: {message_data}")


def on_chat(data: str):
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


async def handle_player_offline(player: str):
    if player in online_mods:
        online_mods.remove(player)
        await send_modmod_message(payload=f"{player} has logged out!", command="MSG", player="ALL")


async def poll_online_mods():
    await send_modmod_message(command="HELLO", player="ALL", payload="0:0")


async def handle_interactor(player: str, command: str, content: str, callback_id: str):
    if player in whitelisted_accounts:
        if command == "echo":
            await send_custom_message(player, content)
        elif command == "chatecho":
            await send_chat_message(player, content)
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
            await send_custom_message(player, "0:0")
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
        for account in online_mods:
            await send_custom_message(account, message)
    else:
        await send_custom_message(player, message)


async def send_custom_message(player: str, content: str):
    custom_string = f"CUSTOM={player}~{content}"
    await page.evaluate(f"window.websocket.send('{custom_string}')")


async def send_chat_message(player: str, content: str):
    chat_string = f"CHAT={player} echo: {content}"
    await page.evaluate(f"window.websocket.send('{chat_string}')")


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
            browser.close()


asyncio.run(main())
