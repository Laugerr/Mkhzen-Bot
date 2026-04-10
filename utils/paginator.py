import discord


class EmbedPaginator(discord.ui.View):
    """Button-driven paginator for navigating a list of embeds."""

    def __init__(self, pages: list[discord.Embed], timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= len(self.pages) - 1

    @discord.ui.button(label="◀  Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="Next  ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


def paginate_fields(
    entries: list[dict],
    build_field: callable,
    title: str,
    description: str,
    color: discord.Color,
    footer_base: str,
    thumbnail_url: str | None = None,
    per_page: int = 5,
) -> list[discord.Embed]:
    """Slice a list of entries into paged embeds, one field per entry."""
    pages: list[discord.Embed] = []
    total = len(entries)
    chunks = [entries[i:i + per_page] for i in range(0, total, per_page)]

    for page_num, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(title=title, description=description, color=color)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        for entry in chunk:
            name, value = build_field(entry)
            embed.add_field(name=name, value=value, inline=False)
        page_label = f"Page {page_num} of {len(chunks)}  ·  {total} total record{'s' if total != 1 else ''}"
        embed.set_footer(text=f"{footer_base}  ·  {page_label}")
        pages.append(embed)

    return pages
