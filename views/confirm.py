import discord


class Confirm(discord.ui.View):
    def __init__(self, user: discord.User, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.user = user
        self.value = None
        self.response = None

    @discord.ui.button(label='Onayla', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id is not self.user.id:
            return

        self.value = True
        self.clear_items()
        await self.response.edit(view=self)
        self.stop()

    @discord.ui.button(label='İptal', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id is not self.user.id:
            return

        self.value = False
        self.clear_items()
        await self.response.edit(view=self)
        self.stop()

    async def on_timeout(self):
        self.clear_items()
        await self.response.edit(view=self)
        self.stop()


