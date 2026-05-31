"""Types describing the data expected by the SlimBrowse protocol.

The SlimBrowse protocol is the Squeezeplay Interface used for browsing music.
Reference: https://lyrion.org/reference/slimbrowse/
"""

from collections.abc import Sequence
from typing import Any, Literal, NotRequired, TypedDict


class SlimBrowseHelpFields(TypedDict):
    """Help text field for items and windows."""

    text: NotRequired[str]
    token: NotRequired[str]


class SlimBrowseWindowFields(TypedDict):
    """Window styling and display fields for windows opened from menu items.

    These fields are used when opening a new window, either defined at
    the base level or at the item level for the "next" window.
    """

    text: NotRequired[str]
    textarea: NotRequired[str]
    textareaToken: NotRequired[str]
    icon_id: NotRequired[int]
    icon: NotRequired[str]
    titleStyle: NotRequired[Literal["album"]]
    menuStyle: NotRequired[Literal["album"]]
    windowStyle: NotRequired[Literal["home_menu", "icon_list", "text_list"]]
    help: NotRequired[SlimBrowseHelpFields]
    windowId: NotRequired[str]


class SlimBrowseInputFields(TypedDict):
    """Input validation and UI configuration for text input items."""

    len: int
    allowedChars: NotRequired[str]
    inputStyle: NotRequired[Literal["text", "time", "ip"]]
    initialText: NotRequired[str]
    help: NotRequired[SlimBrowseHelpFields]
    softbutton1: NotRequired[str]
    softbutton2: NotRequired[str]


class SlimBrowseActionCommand(TypedDict):
    """JSON RPC command definition for SlimBrowse actions."""

    player: NotRequired[int]
    cmd: list[str]
    params: NotRequired[dict[str, Any]]
    itemsParams: NotRequired[str]
    nextWindow: NotRequired[str]
    setSelectedIndex: NotRequired[int]


Action = str | SlimBrowseActionCommand | None
SlimBrowseActionsFields = TypedDict(
    "SlimBrowseActionsFields",
    {
        "go": NotRequired[Action],
        "do": NotRequired[Action],
        "more": NotRequired[Action],
        "back": NotRequired[Action],
        "play": NotRequired[Action],
        "play-hold": NotRequired[Action],
        "add": NotRequired[Action],
        "add-hold": NotRequired[Action],
        "rew": NotRequired[Action],
        "rew-hold": NotRequired[Action],
        "fwd": NotRequired[Action],
        "fwd-hold": NotRequired[Action],
        "pause": NotRequired[Action],
        "pause-hold": NotRequired[Action],
        "on": NotRequired[Action],
        "off": NotRequired[Action],
    },
)


class SlimBrowseBaseFields(TypedDict):
    """Base fields define values applicable to the entire menu or window."""

    icon: NotRequired[str]
    window: NotRequired[SlimBrowseWindowFields]
    actions: NotRequired[SlimBrowseActionsFields]
    jsonrpc: NotRequired[str]
    nextWindow: NotRequired[str]
    setSelectedIndex: NotRequired[int]
    onClick: NotRequired[Literal["refreshMe", "refreshOrigin", "refreshGrandparent"]]


class SlimBrowseSliderItem(TypedDict):
    """Slider item configuration for volume/value selection."""

    slider: Literal[1]
    min: int
    max: int
    adjust: NotRequired[int]
    initial: NotRequired[int]
    sliderIcons: NotRequired[Literal["volume", "none"]]
    text: NotRequired[str]
    help: NotRequired[SlimBrowseHelpFields]
    actions: SlimBrowseActionsFields


class SlimBrowseItemFields(TypedDict):
    """Item fields for individual menu items."""

    text: NotRequired[str]
    textkey: NotRequired[str]
    icon_id: NotRequired[int]
    icon: NotRequired[str]
    extid: NotRequired[str]
    radio: NotRequired[int]
    checkbox: NotRequired[int]
    slider: NotRequired[Literal[1]]
    selectedIndex: NotRequired[int]
    choiceStrings: NotRequired[list[str]]
    nextWindow: NotRequired[str]
    setSelectedIndex: NotRequired[int]
    onClick: NotRequired[Literal["refreshMe", "refreshOrigin", "refreshGrandparent"]]
    showBigArtwork: NotRequired[int]
    input: NotRequired[SlimBrowseInputFields]
    window: NotRequired[SlimBrowseWindowFields]
    actions: NotRequired[SlimBrowseActionsFields]
    playAction: NotRequired[str | SlimBrowseActionCommand]
    playHoldAction: NotRequired[str | SlimBrowseActionCommand]
    addAction: NotRequired[str | SlimBrowseActionCommand]
    goAction: NotRequired[str | SlimBrowseActionCommand]


class SlimBrowseImageFields(TypedDict):
    """Image fields for slideshow items."""

    image: str
    caption: NotRequired[str]


class SlimBrowseSlideshow(TypedDict):
    """Slideshow response format."""

    base: NotRequired[SlimBrowseBaseFields]
    offset: NotRequired[int]
    title: NotRequired[str]
    data: list[SlimBrowseImageFields]


class SlimBrowseItemResponse(TypedDict):
    """Response format for SlimBrowse commands that return lists of items.

    The format is defined by the SlimBrowse protocol:
    https://lyrion.org/reference/slimbrowse/#introduction
    """

    count: int
    item_loop: Sequence[Any]

    base: NotRequired[SlimBrowseBaseFields]
    rescan: NotRequired[Literal[1]]
    goNow: NotRequired[Literal["home", "nowPlaying", "playlist"]]
    window: NotRequired[SlimBrowseWindowFields]


class SlimBrowseAlertWindow(TypedDict):
    """Alert window configuration for non-transient popup windows."""

    title: str
    text: list[str]


class SlimBrowseJiveBlock(TypedDict):
    """Jive block for showBriefly communications (popup notifications)."""

    text: NotRequired[list[str]]
    type: NotRequired[Literal["popupplay", "icon", "song", "mixed", "popupalbum", "alertWindow"]]
    duration: NotRequired[int]
    style: NotRequired[str]
    alertWindow: NotRequired[SlimBrowseAlertWindow]


class SlimBrowseShowBriefly(TypedDict):
    """ShowBriefly message for transient popup notifications."""

    jive: SlimBrowseJiveBlock
