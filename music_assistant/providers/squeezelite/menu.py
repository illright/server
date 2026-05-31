"""SqueezePlay Menu System for hardware Squeezebox Controllers.

This module builds the home menu structure that hardware Squeezebox Controllers
(Controller, Boom, Transporter) display on their screens. The menu items follow
the SqueezePlay/SlimBrowse menu format as described in:
https://lyrion.org/reference/home-vs-slimbrowse/

Each menu item defines an ID, display text, icon, weight (for ordering), and
actions that map to LMS CLI commands handled by the browse module.
"""

from __future__ import annotations

from typing import Any


def build_library_menu_items() -> list[dict[str, Any]]:
    """Build the static library menu items shown on the Squeezebox Controller home screen.

    These items appear in the Controller's "My Music" node and provide navigation
    into the Music Assistant library. Each item's "go" action triggers a corresponding
    LMS CLI command (e.g., "artists", "albums") which is handled by the browse module.

    The item IDs (e.g., "myMusicArtists") follow the LMS convention for built-in
    menu entries. See: https://lyrion.org/reference/home-vs-slimbrowse/

    Returns:
        A list of menu item dicts in SqueezePlay/SlimBrowse format.
    """
    return [
        {
            "id": "myMusicArtists",
            "node": "myMusic",
            "text": "Artists",
            "homeMenuText": "Artists",
            "icon": "html/images/artists.png",
            "weight": 20,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["artists"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicAlbums",
            "node": "myMusic",
            "text": "Albums",
            "homeMenuText": "Albums",
            "icon": "html/images/albums.png",
            "weight": 21,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["albums"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicTracks",
            "node": "myMusic",
            "text": "Songs",
            "homeMenuText": "Songs",
            "icon": "html/images/playall.png",
            "weight": 22,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["tracks"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicGenres",
            "node": "myMusic",
            "text": "Genres",
            "homeMenuText": "Genres",
            "icon": "html/images/genres.png",
            "weight": 23,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["genres"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicPlaylists",
            "node": "myMusic",
            "text": "Playlists",
            "homeMenuText": "Playlists",
            "icon": "html/images/playlists.png",
            "weight": 24,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["playlists"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicFavorites",
            "node": "myMusic",
            "text": "Favorites",
            "homeMenuText": "Favorites",
            "icon": "html/images/favorites.png",
            "weight": 25,
            "style": "itemNoAction",
            "actions": {
                "go": {
                    "cmd": ["favorites"],
                    "itemsParams": "commonParams",
                    "params": {},
                    "player": 0,
                },
            },
        },
        {
            "id": "myMusicSearch",
            "node": "myMusic",
            "text": "Search",
            "homeMenuText": "Search",
            "icon": "html/images/search.png",
            "weight": 30,
            "style": "itemNoAction",
            "input": {
                "len": 1,
                "processingPopup": {"text": "SEARCHING"},
                "help": {"text": "JIVE_SEARCHFOR_HELP"},
            },
            "actions": {
                "go": {
                    "cmd": ["search"],
                    "itemsParams": "commonParams",
                    "params": {"term": "__TAGGEDINPUT__"},
                    "player": 0,
                },
            },
        },
    ]
