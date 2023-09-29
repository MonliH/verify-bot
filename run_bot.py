import os
from random import randint
import re

from dotenv import load_dotenv

load_dotenv()

import db
from discord.ext import commands
import discord

intents = discord.Intents(dm_messages=True, guilds=True, members=True)

from send_email import send_verify


TOKEN = os.getenv("TOKEN")
bot = commands.Bot(command_prefix="$", intents=intents)

DOMAIN = os.getenv('DOMAIN')
email_domain_re = re.escape(DOMAIN)
email_re = re.compile(rf"^\S+@{email_domain_re}$")

_SERVER_IDS = list(map(int,os.getenv("SERVER_ID").split(",")))
_ROLE_IDS = list(map(int,os.getenv("ROLE_ID").split(",")))

SERVERS = set(_SERVER_IDS)
SERVER_ROLES = list(zip(_SERVER_IDS, _ROLE_IDS))


async def verify_role(user: discord.User):
    # add member to all servers in SERVER_ROLES
    for server_id, role_id in SERVER_ROLES:
        guild = bot.get_guild(server_id)
        member = guild.get_member(user.id)

        # make sure the user is in the server
        if member:
            role = guild.get_role(role_id)
            await member.add_roles(role)


@bot.event
async def on_member_join(member: discord.Message):
    if member.guild.id not in SERVERS:
        return

    user_id = member.id
    verification_info = await db.get_state(user_id)

    match verification_info:
        case db.SentVerification(_, _) | None:
            guild = bot.get_guild(member.guild.id)
            await member.send(
                f'Hey! to get access to the rest of the "{guild.name}" server, enter your **school email (ending with `@limestone.on.ca`)**'
            )
        case db.Verified():
            await verify_role(member)


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    
    if not message.guild:
        try:
            random_code = randint(0, 99999)
            random_code = f"{random_code:05}"
            content = message.content.lower()
            snowflake = message.author.id
            status = await db.get_state(snowflake)
            match status:
                case db.SentVerification(email, code):
                    if content == code:
                        await db.set_state(snowflake, db.Verified())
                        await message.channel.send(
                            f":tada: You have been verified using the email **{email}**. Enjoy!"
                        )
                        await db.add_email(email, str(snowflake))
                        await verify_role(message.author)
                    else:
                        await message.channel.send(
                            f":x: You provided the wrong code. Please try verifying again (send me your email again)."
                        )
                        await db.reset_state(snowflake)
                case db.Verified():
                    await message.channel.send(
                        f"You have already been verified. What are you doing here? :clown:"
                    )
                case _:
                    if email_re.findall(content):
                        if not await db.used_email(content):
                            msg = await message.channel.send(
                                f"Sending verification email..."
                            )
                            send_verify(
                                content,
                                str(message.author.display_name),
                                "KSS Discord Servers",
                                random_code,
                            )
                            await db.set_state(
                                snowflake, db.SentVerification(content, random_code)
                            )
                            await msg.edit(
                                content=f"Email sent to {content}. Please enter your verification code. If you do not receive an email, please check your spam folder."
                            )
                        else:
                            await message.channel.send(
                                ":x: Email has already been used."
                            )
                    else:
                        await message.channel.send(
                            f":x: Invalid email specified. Please enter your **school email (ending with @{DOMAIN})**."
                        )
        except discord.errors.Forbidden:
            pass

bot.run(TOKEN)
