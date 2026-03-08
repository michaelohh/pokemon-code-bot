import discord
from discord.ext import tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import json
import re
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1480026254743830528

DATABASE = "codes.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

sources = [
    "https://www.serebii.net/events/"
]


def load_db():
    try:
        with open(DATABASE) as f:
            return json.load(f)
    except:
        return {}


def save_db(data):
    with open(DATABASE, "w") as f:
        json.dump(data, f, indent=4)


def detect_game(text):

    text = text.lower()

    if "scarlet" in text or "violet" in text:
        return "Scarlet & Violet"

    if "pokemon go" in text:
        return "Pokemon GO"

    if "za" in text:
        return "Legends ZA"

    if "arceus" in text:
        return "Legends Arceus"

    if "sword" in text or "shield" in text:
        return "Sword & Shield"

    if "diamond" in text:
        return "BDSP"

    return "Pokemon"


def find_codes(text):

    pattern = r"\b[A-Z0-9]{6,16}\b"
    return set(re.findall(pattern, text))


async def scrape_codes():

    results = []

    for url in sources:

        try:

            r = requests.get(url)

            soup = BeautifulSoup(r.text, "html.parser")

            text = soup.get_text()

            codes = find_codes(text)

            for code in codes:

                game = detect_game(text)

                results.append({
                    "code": code,
                    "game": game,
                    "status": "active",
                    "expires": "Unknown"
                })

        except:
            pass

    return results


@tasks.loop(minutes=20)
async def code_scanner():

    channel = client.get_channel(CHANNEL_ID)

    db = load_db()

    found = await scrape_codes()

    for item in found:

        code = item["code"]

        if code not in db:

            db[code] = item

            embed = discord.Embed(
                title="New Pokémon Mystery Gift Code",
                color=0x00ff00
            )

            embed.add_field(name="Code", value=code)
            embed.add_field(name="Game", value=item["game"])
            embed.add_field(name="Expires", value=item["expires"])

            await channel.send(embed=embed)

    save_db(db)


@tasks.loop(hours=24)
async def daily_codes():

    channel = client.get_channel(CHANNEL_ID)

    db = load_db()

    active = [c for c in db.values() if c["status"] == "active"]

    if not active:
        return

    embed = discord.Embed(
        title="Daily Active Pokémon Codes",
        color=0x3498db
    )

    for c in active[:25]:

        embed.add_field(
            name=c["code"],
            value=f"{c['game']} | Expires: {c['expires']}",
            inline=False
        )

    await channel.send(embed=embed)


@tree.command(name="codes", description="Show active Pokemon codes")
async def codes(interaction: discord.Interaction):

    db = load_db()

    active = [c for c in db.values() if c["status"] == "active"]

    if not active:
        await interaction.response.send_message("No active codes found.")
        return

    embed = discord.Embed(
        title="Active Pokémon Codes",
        color=0x2ecc71
    )

    for c in active[:25]:

        embed.add_field(
            name=c["code"],
            value=f"{c['game']} | Expires: {c['expires']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@tree.command(name="expired", description="Show expired codes")
async def expired(interaction: discord.Interaction):

    db = load_db()

    expired_codes = [c for c in db.values() if c["status"] == "expired"]

    if not expired_codes:
        await interaction.response.send_message("No expired codes stored.")
        return

    embed = discord.Embed(
        title="Expired Pokémon Codes",
        color=0xe74c3c
    )

    for c in expired_codes[:25]:

        embed.add_field(
            name=c["code"],
            value=c["game"],
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@tree.command(name="refresh", description="Force check for new codes")
async def refresh(interaction: discord.Interaction):

    await interaction.response.send_message("Checking for new codes...")

    await code_scanner()

    await interaction.followup.send("Done.")


@client.event
async def on_ready():

    await tree.sync()

    print("Bot online")

    code_scanner.start()
    daily_codes.start()


client.run(TOKEN)