import discord
from discord_components import Button, ButtonStyle
from discord.ext import commands
import asyncio
from copy import deepcopy
from typing import List, Union
from collections import namedtuple
from .abc import Dialog


ControlEmojis = namedtuple(
    "ControlEmojis",
    ("first", "previous", "next", "last", "close"),
    defaults=("⏮", "⬅️", "➡️", "⏭", "⏹"),
)


class EmbedPaginator(Dialog):
    """
    Represents an interactive menu containing multiple embeds.

    :param client: The :class:`discord.Client` to use.
    :param pages: A list of :class:`discord.Embed` to paginate through.
    :param message: An optional :class:`discord.Message` to edit.
        Otherwise a new message will be sent.
    :param control_emojis: :class:`ControlEmojis`, `tuple` or `list`
        containing control emojis to use, otherwise the default will be used.
        A value of `None` causes a reaction to be left out.
    """

    def __init__(
        self,
        client: discord.Client,
        pages: [discord.Embed],
        message: discord.Message = None,
        *,
        control_emojis: Union[ControlEmojis, tuple, list] = ControlEmojis(),
    ):
        super().__init__()

        self._client = client
        self.pages = pages
        self.message = message

        if isinstance(control_emojis, ControlEmojis):
            self.control_emojis = control_emojis
        else:
            control_emojis = tuple(control_emojis)
            if len(control_emojis) == 1:
                self.control_emojis = ControlEmojis(
                    None, None, None, None, control_emojis[0]
                )
            elif len(control_emojis) == 2:
                self.control_emojis = ControlEmojis(
                    None, control_emojis[0], control_emojis[1], None, None
                )
            elif len(control_emojis) == 3:
                self.control_emojis = ControlEmojis(
                    None,
                    control_emojis[0],
                    control_emojis[1],
                    None,
                    control_emojis[2],
                )
            else:
                control_emojis += (None,) * (5 - len(control_emojis))
                self.control_emojis = ControlEmojis(*control_emojis)

    @property
    def formatted_pages(self) -> List[discord.Embed]:
        """ The embeds with formatted footers to act as pages. """

        pages = deepcopy(self.pages)  # copy by value not reference
        for page in pages:
            if page.footer.text == discord.Embed.Empty:
                page.set_footer(text=f"({pages.index(page)+1}/{len(pages)})")
            else:
                page_index = pages.index(page)
                if page.footer.icon_url == discord.Embed.Empty:
                    page.set_footer(
                        text=f"{page.footer.text} - ({page_index+1}/{len(pages)})"
                    )
                else:
                    page.set_footer(
                        icon_url=page.footer.icon_url,
                        text=f"{page.footer.text} - ({page_index+1}/{len(pages)})",
                    )
        return pages

    def generate_buttons(self):
        b = [Button(emoji=control_emoji, style=ButtonStyle.blue) for control_emoji in self.control_emojis]
        b[0].disabled, b[1].disabled = True, True
        return [b]


    async def run(
        self,
        users: List[discord.User],
        channel: discord.TextChannel = None,
        timeout: int = 100,
        **kwargs,
    ):
        """
        Runs the paginator.

        :type users: List[discord.User]
        :param users:
            A list of :class:`discord.User` that can control the pagination.
            Passing an empty list will grant access to all users. (Not recommended.)

        :type channel: Optional[discord.TextChannel]
        :param channel:
            The text channel to send the embed to.
            Must only be specified if `self.message` is `None`.

        :type timeout: int
        :param timeout:
            Seconds to wait until stopping to listen for user interaction.

        :param kwargs:
            - text :class:`str`: Text to appear in the pagination message.
            - timeout_msg :class:`str`: Text to appear when pagination times out.
            - quit_msg :class:`str`: Text to appear when user quits the dialog.

        :return: None
        """

        self._embed = self.pages[0]
        text = kwargs.get("text")

        if len(self.pages) == 1:  # no pagination needed in this case
            await self._publish(channel, content=text, embed=self._embed)

            return

        buttons = self.generate_buttons()
        channel = await self._publish(
            channel, content=text, embed=self.formatted_pages[0], components=buttons
        )
        current_page_index = 0

        def check(r):
            if r.message.id == self.message.id:
                if r.user.id in [u1.id for u1 in users]:
                    return True
                else:
                    self._client.loop.create_task(r.respond(type=6))
                    return False
            else:
                return False

        while True:
            try:
                interaction = await self._client.wait_for(
                    "button_click", check=check, timeout=timeout
                )
            except asyncio.TimeoutError:
                if not isinstance(
                    channel, discord.channel.DMChannel
                ) and not isinstance(channel, discord.channel.GroupChannel):
                    try:
                        await self.message.edit(components=[])
                    except discord.Forbidden:
                        pass
                if "timeout_msg" in kwargs:
                    await self.display(kwargs["timeout_msg"], components=[])
                else:
                    await self.message.edit(components=[])
                return

            emoji = str(interaction.component.emoji)
            max_index = len(self.pages) - 1  # index for the last page

            if emoji == self.control_emojis[0]:
                load_page_index = 0
                buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = True, True, False, False

            elif emoji == self.control_emojis[1]:
                load_page_index = (
                    current_page_index - 1
                    if current_page_index > 0
                    else current_page_index
                )
                if load_page_index == 0:
                    buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = True, True, False, False
                else:
                    buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = False, False, False, False



            elif emoji == self.control_emojis[2]:
                load_page_index = (
                    current_page_index + 1
                    if current_page_index < max_index
                    else current_page_index
                )
                if load_page_index == max_index:
                    buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = False, False, True, True
                else:
                    buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = False, False, False, False


            elif emoji == self.control_emojis[3]:
                load_page_index = max_index
                buttons[0][0].disabled, buttons[0][1].disabled, buttons[0][2].disabled, buttons[0][3].disabled = False, False, True, True


            else:
                await self.quit(kwargs.get("quit_msg"))
                return

            await interaction.respond(embed=self.formatted_pages[load_page_index], components=buttons, type=7)

            current_page_index = load_page_index

    @staticmethod
    def generate_sub_lists(origin_list: list, max_len: int = 25) -> List[list]:
        """
        Takes a list of elements and transforms it into a list of sub-lists of those
        elements with each sublist containing max. ``max_len`` elements.

        This can be used to easily split content for embed-fields across multiple pages.

        .. note::

            Discord allows max. 25 fields per Embed (see `Embed Limits`_).
            Therefore, ``max_len`` must be set to a value of 25 or less.

        .. _Embed Limits: https://discord.com/developers/docs/resources/channel#embed-limits

        :param origin_list: total list of elements
        :type origin_list: :class:`list`

        :param max_len: maximal length of a sublist
        :type max_len: :class:`int`, optional

        :return: list of sub-lists of elements
        :rtype: ``List[list]``
        """

        if len(origin_list) > max_len:
            sub_lists = []

            while len(origin_list) > max_len:
                sub_lists.append(origin_list[:max_len])
                del origin_list[:max_len]

            sub_lists.append(origin_list)

        else:
            sub_lists = [origin_list]

        return sub_lists


class BotEmbedPaginator(EmbedPaginator):
    """
    Same as :class:`EmbedPaginator`, except for the discord.py commands extension.

    :param ctx: The :class:`discord.ext.commands.Context` to use.
    :param pages: A list of :class:`discord.Embed` to paginate through.
    :param message: An optional :class:`discord.Message` to edit.
        Otherwise a new message will be sent.
    :param control_emojis: :class:`ControlEmojis`, `tuple` or `list`
        containing control emojis to use, otherwise the default will be used.
        A value of `None` causes a reaction to be left out.
    """

    def __init__(
        self,
        ctx: commands.Context,
        pages: [discord.Embed],
        message: discord.Message = None,
        *,
        control_emojis: Union[ControlEmojis, tuple, list] = ControlEmojis(),
    ):
        self._ctx = ctx

        super(BotEmbedPaginator, self).__init__(
            ctx.bot, pages, message, control_emojis=control_emojis
        )

    async def run(
        self,
        channel: discord.TextChannel = None,
        users: List[discord.User] = None,
        timeout: int = 100,
        **kwargs,
    ):
        """
        Runs the paginator.

        :type channel: Optional[discord.TextChannel]
        :param channel:
            The text channel to send the embed to.
            Default is the context channel.

        :type users: Optional[List[discord.User]]
        :param users:
            A list of :class:`discord.User` that can control the pagination.
            Default is the context author.
            Passing an empty list will grant access to all users. (Not recommended.)

        :type timeout: int
        :param timeout:
            Seconds to wait until stopping to listen for user interaction.

        :param kwargs:
            - text :class:`str`: Text to appear in the pagination message.
            - timeout_msg :class:`str`: Text to appear when pagination times out.
            - quit_msg :class:`str`: Text to appear when user quits the dialog.

        :return: None
        """

        if users is None:
            users = [self._ctx.author]

        if self.message is None and channel is None:
            channel = self._ctx.channel

        await super().run(users, channel, timeout, **kwargs)
