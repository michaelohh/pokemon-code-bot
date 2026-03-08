import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import re
import datetime
import feedparser

TOKEN = "MTQ4MDAyNTA3NjY2NDUwMDMyNw.G9PGg1.6GKUELdVLN8Z2DWppvAtlsm3TojvcUP3UDAzm8"
CHANNEL_ID = 1480026254743830528

DATABASE = "codes.json"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

sources = [
    "https://www.serebii.net/events/"
]

rss_sources = [
    "https://www.serebii.net/index2.xml"
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

    if "legends z" in text or "za" in text:
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

    channel = bot.get_channel(CHANNEL_ID)

    db = load_db()

    found = await scrape_codes()

    for item in found:

        code = item["code"]

        if code not in db:

            db[code] = item

            embed = discord.Embed(
                title="New Pokémon Code Found",
                color=0x00ff00
            )

            embed.add_field(name="Code", value=code)
            embed.add_field(name="Game", value=item["game"])
            embed.add_field(name="Expires", value=item["expires"])

            await channel.send(embed=embed)

    save_db(db)


@tasks.loop(hours=24)
async def daily_codes():

    channel = bot.get_channel(CHANNEL_ID)

    db = load_db()

    active = [c for c in db.values() if c["status"] == "active"]

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


@bot.command()
async def codes(ctx, game=None):

    db = load_db()

    active = [c for c in db.values() if c["status"] == "active"]

    if game:
        active = [c for c in active if game.lower() in c["game"].lower()]

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

    await ctx.send(embed=embed)


@bot.command()
async def expired(ctx):

    db = load_db()

    expired = [c for c in db.values() if c["status"] == "expired"]

    embed = discord.Embed(
        title="Expired Pokémon Codes",
        color=0xe74c3c
    )

    for c in expired[:25]:

        embed.add_field(
            name=c["code"],
            value=c["game"],
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command()
async def refresh(ctx):

    await ctx.send("Checking for new codes...")

    await code_scanner()

    await ctx.send("Done.")


@bot.event
async def on_ready():

    print("Bot Online")

    code_scanner.start()
    daily_codes.start()


bot.run(TOKEN)