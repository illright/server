"""Library browsing support for hardware Squeezebox players.

Implements the server-side handlers for Squeezebox library browsing.
The commands share names with LMS CLI database commands
(https://lyrion.org/reference/cli/database/).

Each handler returns a list of "blocks" (dicts). The first block contains
metadata (rescan status and total count), and subsequent blocks are the
individual items. For example, the genres command returns:
    [{"rescan": 1, "count": 16}, {"id": 1, "genre": "Acid Jazz"}, ...]
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

from music_assistant_models.enums import MediaType, QueueOption

from .menu import build_library_menu_items
from .slimbrowse_protocol import SlimBrowseActionsFields

if TYPE_CHECKING:
    from music_assistant_models.media_items import Album, Artist, MediaItemImage, Playlist, Track

    from music_assistant import MusicAssistant

# ruff: noqa: ARG001

# Image proxy size for artwork thumbnails sent to Squeezebox hardware displays.
# Could be made configurable per-player in the future (e.g., based on screen resolution),
# but 300px is a reasonable default for Controller/Touch screens.
IMAGE_PROXY_SIZE = 300

# Default number of items returned per page when the client does not specify a limit.
DEFAULT_PAGE_SIZE = 50


class SlimBrowsePlaylistControlResponse(TypedDict):
    """Response format for the 'playlistcontrol' command over SlimBrowse.

    The command is documented at: https://lyrion.org/reference/cli/playlist/#playlistcontrol.
    """

    count: int
    # TODO: Not implemented, Music Assistant currently does not expose the status of rescanning
    rescan: NotRequired[Literal[1]]


class SlimBrowseTrackItem(TypedDict):
    """A single track entry in a browse response block.

    See: https://lyrion.org/reference/slimbrowse/
    """

    id: str
    track: str
    artist: str
    album: str
    duration: int
    trackType: str
    icon: str
    artwork_url: str
    text: str
    style: str
    nextWindow: str
    params: dict[str, Any]
    actions: SlimBrowseActionsFields


class SlimBrowseAlbumItem(TypedDict):
    """A single album entry in a browse response block.

    See: https://lyrion.org/reference/slimbrowse/
    """

    id: str
    album: str
    artist: str
    year: int
    icon: str
    artwork_url: str
    text: str
    style: str
    nextWindow: str
    params: dict[str, Any]
    actions: SlimBrowseActionsFields


class SlimBrowseArtistItem(TypedDict):
    """A single artist entry in a browse response block.

    See: https://lyrion.org/reference/slimbrowse/
    """

    id: str
    artist: str
    icon: str
    artwork_url: str
    text: str
    style: str
    params: dict[str, Any]
    actions: SlimBrowseActionsFields


class SlimBrowsePlaylistItem(TypedDict):
    """A single playlist entry in a browse response block.

    See: https://lyrion.org/reference/slimbrowse/
    """

    id: str
    playlist: str
    icon: str
    artwork_url: str
    text: str
    style: str
    nextWindow: str
    params: dict[str, Any]
    actions: SlimBrowseActionsFields


class SlimBrowseGenreItem(TypedDict):
    """A single genre entry in a browse response block."""

    id: str
    genre: str
    text: str
    style: str
    params: dict[str, Any]
    actions: SlimBrowseActionsFields


BrowseItem = (
    SlimBrowseTrackItem
    | SlimBrowseAlbumItem
    | SlimBrowseArtistItem
    | SlimBrowsePlaylistItem
    | SlimBrowseGenreItem
)


def _get_image_url(mass: MusicAssistant, image: MediaItemImage | None) -> str | None:
    """Return a proxied image URL for the given image, or empty string."""
    if not image:
        return None
    return mass.metadata.get_image_url(image, size=IMAGE_PROXY_SIZE)


def _track_to_item(mass: MusicAssistant, track: Track) -> SlimBrowseTrackItem:
    """Convert a Track to a browse response block."""
    artist_name = ", ".join(a.name for a in track.artists) if track.artists else ""
    album_name = track.album.name if track.album else ""
    image_url = _get_image_url(mass, track.image) or ""
    return {
        "id": track.item_id,
        "track": track.name,
        "artist": artist_name,
        "album": album_name,
        "duration": track.duration or 0,
        # trackType is set to "local" as a placeholder. LMS uses this field to indicate
        # the source type (local, remote, etc.), but Music Assistant abstracts away the
        # underlying provider. The Controller UI uses this mainly for display purposes.
        "trackType": "local",
        "icon": image_url,
        "artwork_url": image_url,
        "text": track.name,
        "style": "itemplay",
        "nextWindow": "nowPlaying",
        "params": {
            "track_id": track.item_id,
            "item_id": track.item_id,
            "uri": track.uri or "",
        },
        "actions": _playable_actions(track.uri or ""),
    }


def _album_to_item(mass: MusicAssistant, album: Album) -> SlimBrowseAlbumItem:
    """Convert an Album to a browse response block."""
    artist_name = ", ".join(a.name for a in album.artists) if album.artists else ""
    image_url = _get_image_url(mass, album.image) or ""
    return {
        "id": album.item_id,
        "album": album.name,
        "artist": artist_name,
        "year": album.year or 0,
        "icon": image_url,
        "artwork_url": image_url,
        "text": album.name,
        "style": "itemplay",
        "nextWindow": "nowPlaying",
        "params": {
            "item_id": album.item_id,
            "uri": album.uri or "",
        },
        "actions": {
            "go": {
                "cmd": ["tracks"],
                "itemsParams": "commonParams",
                "params": {"album_id": album.item_id},
                "player": 0,
            },
            **_playable_actions(album.uri or ""),
        },
    }


def _artist_to_item(mass: MusicAssistant, artist: Artist) -> SlimBrowseArtistItem:
    """Convert an Artist to a browse response block."""
    image_url = _get_image_url(mass, artist.image) or ""
    return {
        "id": artist.item_id,
        "artist": artist.name,
        "icon": image_url,
        "artwork_url": image_url,
        "text": artist.name,
        "style": "itemNoAction",
        "params": {
            "item_id": artist.item_id,
            "uri": artist.uri or "",
        },
        "actions": {
            "go": {
                "cmd": ["albums"],
                "itemsParams": "commonParams",
                "params": {"artist_id": artist.item_id},
                "player": 0,
            },
            **_playable_actions(artist.uri or ""),
        },
    }


def _playlist_to_item(mass: MusicAssistant, playlist: Playlist) -> SlimBrowsePlaylistItem:
    """Convert a Playlist to a browse response block."""
    image_url = _get_image_url(mass, playlist.image) or ""
    return {
        "id": playlist.item_id,
        "playlist": playlist.name,
        "icon": image_url,
        "artwork_url": image_url,
        "text": playlist.name,
        "style": "itemplay",
        "nextWindow": "nowPlaying",
        "params": {
            "item_id": playlist.item_id,
            "uri": playlist.uri or "",
        },
        "actions": {
            "go": {
                "cmd": ["playlists", "tracks"],
                "itemsParams": "commonParams",
                "params": {"playlist_id": playlist.item_id},
                "player": 0,
            },
            **_playable_actions(playlist.uri or ""),
        },
    }


def _playable_actions(uri: str) -> SlimBrowseActionsFields:
    """Return standard play/add/insert actions for a playable URI."""
    return {
        "play": {
            "cmd": ["playlistcontrol"],
            "itemsParams": "commonParams",
            "params": {"uri": uri, "cmd": "play"},
            "player": 0,
            "nextWindow": "nowPlaying",
        },
        "play-hold": {
            "cmd": ["playlistcontrol"],
            "itemsParams": "commonParams",
            "params": {"uri": uri, "cmd": "load"},
            "player": 0,
            "nextWindow": "nowPlaying",
        },
        "add": {
            "cmd": ["playlistcontrol"],
            "itemsParams": "commonParams",
            "params": {"uri": uri, "cmd": "add"},
            "player": 0,
            "nextWindow": "refresh",
        },
        "add-hold": {
            "cmd": ["playlistcontrol"],
            "itemsParams": "commonParams",
            "params": {"uri": uri, "cmd": "insert"},
            "player": 0,
            "nextWindow": "refresh",
        },
    }


def _convert_to_response(
    items: Sequence[BrowseItem], total_count: int | None = None
) -> list[dict[str, Any]]:
    """Return a list of blocks: metadata block followed by item blocks.

    :param items: The page of items to return.
    :param total_count: The total number of items available across all pages.
        If not provided, defaults to the length of the items list.
    """
    count = total_count if total_count is not None else len(items)
    return [{"rescan": 1, "count": count}, *items]


async def _handle_artists(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'artists' browse command.

    See: https://lyrion.org/reference/cli/database/#artists

    Supported parameters:
        - search: Filter artists by name substring, case insensitive.
        - artist_id: Return info for a specific artist.

    The rest of the parameters are currently unsupported.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE
    search = kwargs.get("search")
    artist_id = kwargs.get("artist_id")

    response_first_block = {
        "rescan": 0,
        "count": 0,
    }

    if artist_id:
        # Return info for the specific artist
        artist = await mass.music.artists.get_library_item(int(artist_id))
        response_first_block["count"] = 1
        return [response_first_block, {"id": artist_id, "artist": artist.name}]

    # TODO: Add filtering by album_id and genre_id

    artists = await mass.music.artists.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    response_first_block["count"] = len(artists)
    return [response_first_block] + [
        {"id": artist.item_id, "artist": artist.name} for artist in artists
    ]


async def _handle_albums(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'albums' browse command.

    See: https://lyrion.org/reference/cli/database/#albums

    Supported parameters:
        - search: Filter albums by name substring.
        - artist_id: Return albums by a specific artist.
        - genre_id: Return albums in a given genre.
        - album_id: Return info for a specific album.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE
    search = kwargs.get("search")
    artist_id = kwargs.get("artist_id")

    if artist_id:
        artist = await mass.music.artists.get_library_item(int(artist_id))
        albums = await mass.music.artists.albums(
            item_id=artist.item_id,
            provider_instance_id_or_domain=artist.provider,
        )
        all_items = [_album_to_item(mass, album) for album in albums]
        page = all_items[offset : offset + limit]
        return _convert_to_response(page, total_count=len(all_items))

    albums = await mass.music.albums.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_album_to_item(mass, album) for album in albums]
    return _convert_to_response(items)


async def _handle_tracks(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'tracks' browse command.

    See: https://lyrion.org/reference/cli/database/#titles

    Supported parameters:
        - search: Filter tracks by name substring.
        - album_id: Return tracks on a specific album.
        - artist_id: Return tracks by a specific artist.
        - genre_id: Return tracks in a given genre.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE
    search = kwargs.get("search")
    album_id = kwargs.get("album_id")

    if album_id:
        album = await mass.music.albums.get_library_item(int(album_id))
        tracks = await mass.music.albums.tracks(
            item_id=album.item_id,
            provider_instance_id_or_domain=album.provider,
        )
        all_items = [_track_to_item(mass, track) for track in tracks]
        page = all_items[offset : offset + limit]
        return _convert_to_response(page, total_count=len(all_items))

    tracks = await mass.music.tracks.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_track_to_item(mass, track) for track in tracks]
    return _convert_to_response(items)


async def _handle_playlists(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'playlists' browse command.

    See: https://lyrion.org/reference/cli/database/#playlists

    Supported parameters:
        - search: Filter playlists by name substring.
        - playlist_id: Return tracks within a specific playlist.

    The Controller sends 'playlists tracks <start> <count> playlist_id:<id>' to
    browse into a playlist. The CLI dispatcher extracts command="playlists" and
    passes ["tracks", <start>, <count>] as positional args, so we detect and skip
    the "tracks" subcommand token before interpreting pagination args.
    """
    # If called as "playlists tracks ...", shift args past the subcommand token.
    if args and args[0] == "tracks":
        args = args[1:]
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE
    search = kwargs.get("search")

    playlist_id = kwargs.get("playlist_id")
    if playlist_id:
        playlist = await mass.music.playlists.get_library_item(int(playlist_id))
        tracks = await mass.music.playlists.tracks(
            item_id=playlist.item_id,
            provider_instance_id_or_domain=playlist.provider,
        )
        all_items = [_track_to_item(mass, track) for track in tracks]
        page = all_items[offset : offset + limit]
        return _convert_to_response(page, total_count=len(all_items))

    playlists = await mass.music.playlists.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_playlist_to_item(mass, playlist) for playlist in playlists]
    return _convert_to_response(items)


async def _handle_genres(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'genres' browse command.

    See: https://lyrion.org/reference/cli/database/#genres
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE

    genres = await mass.music.genres.library_items(
        limit=limit,
        offset=offset,
    )
    items: list[SlimBrowseGenreItem] = [
        {
            "id": genre.item_id,
            "genre": genre.name,
            "text": genre.name,
            "style": "itemNoAction",
            "params": {"item_id": genre.item_id},
            "actions": {
                "go": {
                    "cmd": ["albums"],
                    "itemsParams": "commonParams",
                    "params": {"genre_id": genre.item_id},
                    "player": 0,
                },
            },
        }
        for genre in genres
    ]
    return _convert_to_response(items)


async def _handle_search(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'search' browse command.

    Accepts both `term` (LMS CLI standard) and `search` (legacy/alias) parameters.

    Note: The LMS CLI spec returns separate contributors_loop, albums_loop, and
    tracks_loop in the response. This implementation returns a single flat list
    mixing all result types as blocks.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else 10
    term = kwargs.get("term", kwargs.get("search", ""))

    if not term:
        return _convert_to_response([])

    results = await mass.music.search(
        search_query=str(term),
        media_types=[MediaType.ARTIST, MediaType.ALBUM, MediaType.TRACK, MediaType.PLAYLIST],
        limit=limit,
        library_only=True,
    )

    all_items: list[BrowseItem] = []
    for artist in results.artists:
        all_items.append(_artist_to_item(mass, artist))
    for album in results.albums:
        all_items.append(_album_to_item(mass, album))
    for track in results.tracks:
        all_items.append(_track_to_item(mass, track))
    for playlist in results.playlists:
        all_items.append(_playlist_to_item(mass, playlist))

    page = all_items[offset : offset + limit]
    return _convert_to_response(page, total_count=len(all_items))


async def _handle_playlistcontrol(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowsePlaylistControlResponse:
    """Handle the 'playlistcontrol' command.

    Supports play/load/add/insert/delete actions on media URIs.

    See: https://lyrion.org/reference/cli/playlists/#playlistcontrol

    Note: The LMS CLI spec also supports selectors like genre_id, artist_id,
    album_id, track_id (comma-separated), year, folder_id, playlist_name,
    play_index, and sort. This implementation only uses the `uri` parameter
    (a Music Assistant extension) to identify media. The `delete` command
    removes items from the current queue by URI.
    """
    cmd = kwargs.get("cmd", "play")
    uri = kwargs.get("uri", "")

    if not uri:
        return {"count": 0}

    queue = mass.player_queues.get_active_queue(player_id)
    if not queue:
        return {"count": 0}

    if cmd == "delete":
        # Remove matching items from the current queue by URI.
        queue_items = mass.player_queues.items(queue.queue_id)
        removed = 0
        for item in queue_items:
            if getattr(item, "uri", None) == uri:
                mass.player_queues.delete_item(queue.queue_id, item.queue_item_id)
                removed += 1
        return {"count": removed}

    cmd_to_option = {
        "play": QueueOption.PLAY,
        "load": QueueOption.REPLACE,
        "add": QueueOption.ADD,
        "insert": QueueOption.NEXT,
    }
    option = cmd_to_option.get(cmd, QueueOption.PLAY)
    await mass.player_queues.play_media(queue.queue_id, uri, option=option)
    return {"count": 1}


async def _handle_favorites(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Handle the 'favorites' browse command.

    Note: The LMS CLI spec uses 'favorites items <start> <count>' with params like
    item_id, search, want_url, feedMode. This implementation is a Music Assistant
    adaptation that returns all favorited media (tracks, albums, artists, playlists)
    from the MA library as a flat list of blocks. It does not implement the
    LMS favorites hierarchy or the documented CLI parameters.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE

    tracks_coro = mass.music.tracks.library_items(favorite=True, limit=500, offset=0)
    albums_coro = mass.music.albums.library_items(favorite=True, limit=500, offset=0)
    artists_coro = mass.music.artists.library_items(favorite=True, limit=500, offset=0)
    playlists_coro = mass.music.playlists.library_items(favorite=True, limit=500, offset=0)

    tracks, albums, artists, playlists = await asyncio.gather(
        tracks_coro, albums_coro, artists_coro, playlists_coro
    )

    items: list[BrowseItem] = []
    for track in tracks:
        items.append(_track_to_item(mass, track))
    for album in albums:
        items.append(_album_to_item(mass, album))
    for artist in artists:
        items.append(_artist_to_item(mass, artist))
    for playlist in playlists:
        items.append(_playlist_to_item(mass, playlist))

    page = items[offset : offset + limit]
    return _convert_to_response(page, total_count=len(items))


def register_browse_handlers(mass: MusicAssistant, slimproto: Any) -> None:
    """
    Register library browsing command handlers on the SlimServer.

    Handlers are dynamically set as methods on the SlimProtoCLI instance so that
    the CLI's command dispatch (which uses getattr) can find and invoke them.

    :param mass: The MusicAssistant instance for library access.
    :param slimproto: The SlimServer instance to register handlers on.
    """

    async def handle_artists(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_artists(mass, player_id, *args, **kwargs)

    async def handle_albums(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_albums(mass, player_id, *args, **kwargs)

    async def handle_tracks(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_tracks(mass, player_id, *args, **kwargs)

    async def handle_playlists(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_playlists(mass, player_id, *args, **kwargs)

    async def handle_genres(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_genres(mass, player_id, *args, **kwargs)

    async def handle_search(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_search(mass, player_id, *args, **kwargs)

    async def handle_playlistcontrol(
        player_id: str, *args: Any, **kwargs: Any
    ) -> SlimBrowsePlaylistControlResponse:
        return await _handle_playlistcontrol(mass, player_id, *args, **kwargs)

    async def handle_favorites(player_id: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await _handle_favorites(mass, player_id, *args, **kwargs)

    # Build the library menu items for the Squeezebox Controller's home menu
    library_menu_items = build_library_menu_items()

    # Wrap the existing menu handler to include library entries
    cli = slimproto.cli
    original_handle_menu = cli._handle_menu

    async def handle_menu(player_id: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Return library menu items merged with the original menu items."""
        original = await original_handle_menu(player_id, *args, **kwargs)
        original_items = original.get("item_loop", [])
        all_items = library_menu_items + original_items
        offset = int(args[0]) if args else int(kwargs.get("_index", 0))
        limit = int(args[1]) if len(args) > 1 else int(kwargs.get("_quantity", 200))
        page = all_items[offset : offset + limit]
        return {
            "item_loop": page,
            "count": len(all_items),
        }

    # Register handlers on the CLI object by setting _handle_<command> methods.
    # The CLI dispatches commands via getattr(self, f"_handle_{command}").
    cli._handle_menu = handle_menu
    cli._handle_artists = handle_artists
    cli._handle_albums = handle_albums
    cli._handle_tracks = handle_tracks
    cli._handle_playlists = handle_playlists
    cli._handle_genres = handle_genres
    cli._handle_search = handle_search
    cli._handle_playlistcontrol = handle_playlistcontrol
    cli._handle_favorites = handle_favorites
