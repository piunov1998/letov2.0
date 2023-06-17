from uuid import uuid4

import discord
from discord import app_commands
from discord.ext import commands

from adapters.sessions import SessionAdapter
from models.letov_hub import LetovHubSession


class Hub(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = SessionAdapter()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync(guild=discord.Object(id=358780693595291652))

    @app_commands.command(
        name="get_key",
        description="Generate URL with key to access Letov Hub",
    )
    async def issue_token(self, interaction: discord.Interaction):
        """Генерация ключа для входа в панель управления"""

        session = LetovHubSession(
            sid=uuid4().hex,
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild=interaction.guild.id
        )

        self.sessions.create_session(session)

        await interaction.response.send_message(
            f"Your URL is: http://hub.letov.fvds.ru/auth?sid={session.sid}", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot), guilds=[discord.Object(id=358780693595291652)])
