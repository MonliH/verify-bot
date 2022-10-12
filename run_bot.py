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

SERVER_ID = int(os.getenv("SERVER_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))

SERVER_NAME = os.getenv("SERVER_NAME")


async def verify_role(user: discord.User):
    guild = bot.get_guild(SERVER_ID)
    member = guild.get_member(user.id)
    role = guild.get_role(ROLE_ID)
    await member.add_roles(role)


@bot.event
async def on_member_join(member: discord.Message):
    if member.guild.id != SERVER_ID:
        return
    guild = bot.get_guild(SERVER_ID)
    await member.send(
        f'Hey! to get access to the rest of the "{guild.name}" server, enter your **school email (ending with `@limestone.on.ca`)**'
    )


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
                        await verify_role(message.author)
                        await db.add_email(email)
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
                                SERVER_NAME,
                                random_code,
                            )
                            await db.set_state(
                                snowflake, db.SentVerification(content, random_code)
                            )
                            await msg.edit(
                                content=f"Email sent to {content}. Please enter your verification code."
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
