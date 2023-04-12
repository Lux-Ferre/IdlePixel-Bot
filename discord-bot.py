import os
import discord

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_GUILD = os.getenv('DISCORD_GUILD')

client = discord.Client(intents=discord.Intents.default())


async def send_message(channel: int, message: str):
    channel = client.get_channel(channel)
    await channel.send(message)


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == DISCORD_GUILD:
            break

    bot_channel = 1086793315770441770
    message_string = "[17:39:51]godofnades: too bad I already used my loot pot, have 3 g2 keys to use"

    await send_message(bot_channel, message_string)

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})\n'
    )


client.run(DISCORD_TOKEN)
