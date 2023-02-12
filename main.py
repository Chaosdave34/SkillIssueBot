import asyncio
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
GUILD = discord.Object(id=environ["GUILD_ID"])
START = 1663859112

database_handler = DatabaseHandler()
hypixel_handler = minecraft.HyixelHandler(HYPIXEL_KEY)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync(guild=GUILD)

    async def on_ready(self):
        print("Started!")
        print(f'Logged in as {client.user} (ID: {client.user.id})')
        print('----------')

        client.loop.create_task(check_dungeon_death())

    async def on_guild_available(self, guild: discord.Guild):
        if guild.id == GUILD.id:
            for member in guild.members:
                database_handler.check_user_inactivity(member.id)

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            return
        if message.guild.id == GUILD.id:
            if message.channel.id == 1029351337789509662:
                if message.author.guild_permissions.administrator is not True:
                    await message.delete()
                    return

            current_time = datetime.datetime.now().timestamp()
            database_handler.update_user_inactivity(message.author.id, last_message=current_time)

    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member.guild.id == GUILD.id:
            current_time = datetime.datetime.now().timestamp()
            database_handler.update_user_inactivity(member.id, last_voice=current_time)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.get_role(1029053058770010203) is not None and after.get_role(1029053058770010203) is None:
            info = database_handler.check_user(after.id)

            if info is not None:
                database_handler.remove_user(after.id)

    async def on_member_remove(self, member: discord.Member):
        info = database_handler.check_user(member.id)

        if info is not None:
            database_handler.remove_user(member.id)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
client = MyClient(intents=intents)


@client.tree.command(description="Link your discord with your minecraft account.", guild=GUILD)
@app_commands.describe(ign="Your minecraft IGN")
async def verify(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()

    info = database_handler.check_user(interaction.user.id)
    user = interaction.user

    if info is not None:
        response = "You're already verified!"

    else:
        uuid = minecraft.username_to_uuid(ign)
        if uuid is None:
            response = "This IGN does not exist!"

        else:
            try:
                hypixel_info = hypixel_handler.get_player(uuid)
            except minecraft.ApiException as e:
                await interaction.followup.send(embed=discord.Embed(title=e.message, color=discord.Colour.red()), ephemeral=True)
                return

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

                            embed = filter_profile_informartion(member=user)
                            await interaction.guild.get_channel(1022135331094528070).send(embed=embed, content="Someone verified:")

                        else:
                            response = "The given IGN is not linked to your discord account!"

    await interaction.followup.send(embed=discord.Embed(title=response), ephemeral=True)


@app_commands.guilds(GUILD.id)
@app_commands.default_permissions()
class Manage(app_commands.Group):
    @app_commands.command(description="Verify an user!")
    async def verify(self, interaction: discord.Interaction, user: discord.User, ign: str):
        await interaction.response.defer()

        info = database_handler.check_user(user.id)
        user = interaction.guild.get_member(user.id)

        if info is not None:
            response = "The user is already verified!"

        else:
            uuid = minecraft.username_to_uuid(ign)
            if uuid is None:
                response = "This IGN does not exist!"

            else:
                try:
                    hypixel_info = hypixel_handler.get_player(uuid)
                except minecraft.ApiException as e:
                    await interaction.followup.send(embed=discord.Embed(title=e.message, color=discord.Colour.red()), ephemeral=True)
                    return

                if hypixel_info is None:
                    response = "The user never played on hypixel!"

                else:
                    if "socialMedia" not in hypixel_info:
                        response = "The user's discord account is not linked to hypixel!"

                    else:
                        social = hypixel_info["socialMedia"]["links"]
                        if "DISCORD" not in social:
                            response = "The user's  discord account is not linked to hypixel!"

                        else:
                            discord_tag = social["DISCORD"]
                            discord_name = discord_tag.split("#")[0]
                            discord_discriminator = discord_tag.split("#")[1]

                            if discord_name == user.name and discord_discriminator == user.discriminator:
                                response = "Successfully verified!"
                                database_handler.add_user(user.id, uuid)
                                await user.add_roles(discord.Object(id=1029053058770010203))
                                embed = filter_profile_informartion(member=user)
                                await interaction.guild.get_channel(1022135331094528070).send(embed=embed, content="Someone verified:")
                            else:
                                response = "The given IGN is not linked to the user's discord account!"

        await interaction.followup.send(embed=discord.Embed(title=response))

    @app_commands.command(description="Unverify an user!")
    async def unverify(self, interaction: discord.Interaction, user: discord.User):
        info = database_handler.check_user(user.id)

        user = interaction.guild.get_member(user.id)

        if info is None:
            response = "The user is not verified!"
        else:
            await user.remove_roles(discord.Object(id=1029053058770010203))
            database_handler.remove_user(user.id)
            response = "Successfully unverified!"

        await interaction.response.send_message(embed=discord.Embed(title=response))


@app_commands.guilds(GUILD.id)
@app_commands.default_permissions()
class Check(app_commands.Group):
    @app_commands.command(description="Check an user's inactivity.")
    async def inactivity(self, interaction: discord.Interaction, user: discord.User):
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

    @app_commands.command(description="Get an user's IGN")
    async def ign(self, interaction: discord.Interaction, user: discord.User):
        info = database_handler.check_user(user.id)

        if info is None:
            response = "This user is not verified yet!"

        else:
            uuid = info[1]
            profile = minecraft.uuid_to_profile(uuid)

            if profile is None:
                response = "The linked UUID is invalid!"

            else:
                name = profile['name']
                response = f"This user's IGN is: {name}"

        await interaction.response.send_message(embed=discord.Embed(title=response))

    @app_commands.command(description="Check if an user passes the requirements.")
    async def reqs(self, interaction: discord.Interaction, user: discord.User):
        user = interaction.guild.get_member(user.id)

        await interaction.response.defer()
        embed = filter_profile_informartion(user)

        await interaction.followup.send(embed=embed)


def filter_profile_informartion(member: discord.Member):
    info = database_handler.check_user(member.id)

    if info is None:
        embed = discord.Embed(title="This user is not verified yet!")

    else:
        uuid = info[1]
        profiles = minecraft.get_skyblock_profile(uuid)
        profiles = profiles["profiles"]
        average_levels = {}
        for profile in profiles:
            average_levels[profiles[profile]["data"]["average_level"]] = profiles[profile]["profile_id"]

        profile = profiles[average_levels[max(average_levels)]]

        secrets = profile["data"]["dungeons"]["secrets_found"]
        cata = profile["data"]["dungeons"]["catacombs"]["level"]["level"]
        if "7" in profile["data"]["dungeons"]["catacombs"]["floors"]:
            comps = profile["data"]["dungeons"]["catacombs"]["floors"]["7"]["stats"]["tier_completions"]
        else:
            comps = 0

        weapons = profile["items"]["weapons"]
        weapon_list = []
        for weapon in weapons:
            weapon_info = weapon["tag"]["ExtraAttributes"]
            weapon_id = weapon_info["id"]

            if weapon_id == "TERMINATOR":
                weapon_list.append("Terminator")

            if weapon_id == "JUJU_SHORTBOW":
                overload = weapon_info["enchantments"]["overload"] if "overload" in weapon_info["enchantments"] else 0
                soul_eater = weapon_info["enchantments"]["ultimate_soul_eater"] if "ultimate_soul_eater" in weapon_info["enchantments"] else 0
                weapon_list.append(f"Juju Shortbow - SE {soul_eater} and OV {overload}")

            if weapon_id == "AXE_OF_THE_SHREDDED ":
                weapon_list.append("Axe of the Shredded")

            if weapon_id == "GIANTS_SWORD":
                weapon_list.append("Giant's Sword")

            if weapon_id in ["HYPERION", "VALKYRIE", "ASTRAEA", "SCYLLA"]:
                weapon_list.append("Wither Blade")

        response = f"Secrets: {secrets}/5000\nCatacombs Level: {cata}/30\nF7 Completions: {comps}/40"

        if member.nick:
            title = f"{member.nick}'s ({member.name}) requirements:"
        else:
            title = f"{member.name}'s requirements:"

        colour = discord.Colour.red()

        test = any(items in ["Wither Blade", "Terminator"] for items in weapon_list) or all(
            items in ["Axe of the Shredded", "Giant's Sword"] for items in weapon_list) or "Juju Shortbow - SE 5 and OV 5" in weapon_list

        if secrets >= 5000 and cata >= 30 and comps >= 40 and test:
            colour = discord.Colour.green()

        embed = discord.Embed(title=title, colour=colour)
        embed.add_field(name="General:", value=response)
        value = "\n".join(weapon_list)

        embed.add_field(name="Weapons:", value=value if value != "" else "---")

    return embed


is_in_dungeon = []
prev_deaths_list = {}
prev_dungeon_runs = {}


async def check_dungeon_death():
    while client.loop.is_running():
        check_list = ["Chaosdave34", "_Tren1ty", "MagicHappened"]

        for user in check_list:
            try:
                session = hypixel_handler.get_status(minecraft.username_to_uuid(user))
            except minecraft.ApiException as e:
                print(e.message)
                break

            if session is not None:
                if session["online"]:
                    if session["mode"] == "dungeon":
                        if user not in is_in_dungeon:
                            is_in_dungeon.append(user)
                            await save_stats(user)

                    else:
                        if user in is_in_dungeon:
                            is_in_dungeon.remove(user)
                            await compare_stats(user)

        await asyncio.sleep(15)


async def save_stats(user):
    try:
        profiles = hypixel_handler.get_profiles(minecraft.username_to_uuid(user))
    except minecraft.ApiException as e:
        print(e.message)
        return

    if profiles is not None:
        for profile in profiles:
            if profile["selected"]:
                user_profile_info = profile["members"][minecraft.username_to_uuid(user)]

                deaths = {key: value for key, value in user_profile_info["stats"].items() if "death" in key}
                prev_deaths_list[user] = deaths

                dungeons = user_profile_info["dungeons"]["dungeon_types"]
                prev_dungeon_runs[user] = dungeons


async def compare_stats(user):
    uuid = minecraft.username_to_uuid(user)
    try:
        profiles = hypixel_handler.get_profiles(uuid)
    except minecraft.ApiException as e:
        print(e.message)
        return

    if profiles is not None:
        for profile in profiles:
            if profile["selected"]:
                user_profile_info = profile["members"][uuid]

                deaths = {key: value for key, value in user_profile_info["stats"].items() if "death" in key}
                dungeons = user_profile_info["dungeons"]["dungeon_types"]

                prev_deaths = prev_deaths_list[user]
                prev_dungeons = prev_dungeon_runs[user]

                # Check for deaths
                if prev_deaths["deaths"] == deaths["deaths"]:
                    return

                death_count = deaths["deaths"] - prev_deaths["deaths"]

                death_list = {}
                new_death_type_key = prev_deaths.keys() ^ deaths.keys()
                for key in new_death_type_key:
                    death_list[key] = deaths[key]

                for key in prev_deaths.keys():
                    if key != "deaths":
                        if deaths[key] > prev_deaths[key]:
                            death_list[key] = deaths[key] - prev_deaths[key]

                # Get Dungsons floor
                prev_catacombs = prev_dungeons["catacombs"]["times_played"]
                catacombs = dungeons["catacombs"]["times_played"]

                floor = "0"
                new_times_played_key = prev_catacombs.keys() ^ catacombs.keys()
                for key in new_times_played_key:
                    floor = key

                for key in prev_catacombs.keys():
                    if catacombs[key] > prev_catacombs[key]:
                        floor = key

                # Check if catacombs or master catacombs
                mode = "`unknown`"
                if floor == "0":
                    mode = "Catacombs"

                prev_catacombs_killed = prev_dungeons["catacombs"]["mobs_killed"][floor]
                catacombs_killed = dungeons["catacombs"]["mobs_killed"][floor]

                prev_master_catacombs_killed = prev_dungeons["master_catacombs"]["mobs_killed"][floor]
                master_catacombs_killed = dungeons["master_catacombs"]["mobs_killed"][floor]

                if catacombs_killed > prev_catacombs_killed:
                    mode = "Catacombs"
                elif master_catacombs_killed > prev_master_catacombs_killed:
                    mode = "Master Catacombs"

                if floor == "0":
                    floor = "Entrance"

                if death_count == 1:
                    embed = discord.Embed(title=f"{user} died 1 time in {mode} Floor {floor}.")
                else:
                    embed = discord.Embed(title=f"{user} died {death_count} times in {mode} Floor {floor}.", timestamp=datetime.datetime.now())

                embed.set_footer(text="This feature is currently in alpha state!")

                if mode == "`unknown`":
                    embed.description = "You somehow managed to not kill a single mob!"

                for death_reason in death_list.keys():
                    name = death_reason.split("_")
                    name.pop(0)
                    name = [x.capitalize() for x in name]
                    name = " ".join(name)
                    embed.add_field(name=f"{int(death_list[death_reason])}x {name}", value=" ", inline=True)

                await client.get_channel(995442764693114880).send(embed=embed)


client.tree.add_command(Check())
client.tree.add_command(Manage())

client.run(DISCORD_TOKEN)
