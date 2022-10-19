import datetime

from dotenv import load_dotenv
from os import environ

import discord
from discord import app_commands

from database import DatabaseHandler
import minecraft

load_dotenv()

DISCORD_TOKEN = environ["DISCORD_TOKEN"]
HYPIXEL_KEY = environ["HYPIXEL_KEY"]
GUILD = discord.Object(id=965681239174549554)
START = 1663859112

database_handler = DatabaseHandler()
hypixel_handler = minecraft.HyixelHandler(HYPIXEL_KEY)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.tree.remove_command("verify")

    async def setup_hook(self):
        await self.tree.sync(guild=GUILD)

    async def on_ready(self):
        print(f'Logged in as {client.user} (ID: {client.user.id})')
        print('------')

    async def on_guild_available(self, guild: discord.Guild):
        if guild.id == GUILD.id:
            for member in guild.members:
                database_handler.check_user_inactivity(member.id)

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            return
        if message.guild.id == GUILD.id:
            if message.channel.id == 1029351337789509662:
                await message.delete()
                return

            current_time = datetime.datetime.now().timestamp()
            database_handler.update_user_inactivity(message.author.id, last_message=current_time)

    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member.guild.id == GUILD.id:
            current_time = datetime.datetime.now().timestamp()
            database_handler.update_user_inactivity(member.id, last_voice=current_time)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
client = MyClient(intents=intents)


@client.tree.command(name="check", description="Checks an user's inactivity.", guild=GUILD)
@app_commands.describe(user="user")
@app_commands.default_permissions()
async def check(interaction: discord.Interaction, user: discord.User):
    user_id = user.id

    data = database_handler.get_user_inactivity(user_id)

    last_message = data[1]
    last_voice = data[2]

    member = interaction.guild.get_member(user_id)
    username = member.name
    nick = member.nick

    if last_message:
        lm_text = f"Last sent message: <t:{int(last_message)}:R>"
    else:
        lm_text = f"Last sent Message: `No Information`"

    if last_voice:
        vc_text = f"Voice channel joined last time: <t:{int(last_voice)}:R>"
    else:
        vc_text = f"Voice channel joined last time: `No Information`"

    if nick:
        title = f"{nick}'s ({username}) information:"
    else:
        title = f"{username}'s information:"

    description = lm_text + "\n" + vc_text + f"\nJoined: <t:{int(member.joined_at.timestamp())}:R>" + f"\nBegin of logs: <t:{START}:R>"

    await interaction.response.send_message(embed=discord.Embed(title=title, description=description))


@client.tree.command(name="verify", description="Link your discord with your minecraft account.", guild=GUILD)
@app_commands.describe(ign="Your minecraft IGN")
async def verify(interaction: discord.Interaction, ign: str):
    info = database_handler.check_user(interaction.user.id)
    user = interaction.user

    if info is not None:
        response = "You're already verified!"

    else:
        uuid = minecraft.username_to_uuid(ign)
        if uuid is None:
            response = "This IGN does not exist!"

        else:
            hypixel_info = hypixel_handler.get_player(uuid)
            if hypixel_info is None:
                response = "You never played on hypixel!"

            else:
                if "socialMedia" not in hypixel_info:
                    response = "Your discord account is not linked to hypixel!"

                else:
                    social = hypixel_info["socialMedia"]["links"]
                    if "DISCORD" not in social:
                        response = "Your discord account is not linked to hypixel!"

                    else:
                        discord_tag = social["DISCORD"]
                        discord_name = discord_tag.split("#")[0]
                        discord_discriminator = discord_tag.split("#")[1]

                        if discord_name == user.name and discord_discriminator == user.discriminator:
                            response = "Successfully verified!"
                            database_handler.add_user(user.id, uuid)
                            await user.add_roles(discord.Object(id=1029053058770010203))

                        else:
                            response = "The given IGN is not linked to your discord account!"

    await interaction.response.send_message(embed=discord.Embed(title=response), ephemeral=True)


client.run(DISCORD_TOKEN)
