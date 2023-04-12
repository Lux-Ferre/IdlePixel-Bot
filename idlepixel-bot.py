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
development_mode = True

global page

lbt_webhook = SyncWebhook.from_url(env_consts["LBT_DISCORD_HOOK_URL"])
dh_webhook = SyncWebhook.from_url(env_consts["DH_DISCORD_HOOK_URL"])
testing_webhook = SyncWebhook.from_url(env_consts["TESTING_HOOK_URL"])


def on_web_socket(ws):
    print(f"WebSocket opened: {ws.url}")
    ws.on("framesent", lambda payload: print(payload))
    ws.on("framereceived", receive_message)
    ws.on("close", handle_disconnect)


def receive_message(raw_message: str):
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
            loop = asyncio.get_event_loop()
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

        # await page.locator('[id=chat-area-input]').fill("Playwright test.")
        # await page.evaluate("Chat.send()")


asyncio.run(main())
