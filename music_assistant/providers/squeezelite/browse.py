"""SlimBrowse library browsing support for hardware Squeezebox players.

Implements the server-side handlers for Squeezebox library browsing over the
JSONRPC/CometD transport (SlimBrowse protocol). While the commands share names
with LMS CLI database commands (https://lyrion.org/reference/cli/database/),
the responses here use the SlimBrowse item_loop format described at:
https://lyrion.org/reference/slimbrowse/

LMS CLI and SlimBrowse are distinct protocols — LMS CLI returns tagged parameter
strings, while SlimBrowse returns structured JSON with item_loop arrays. These
handlers serve the SlimBrowse layer.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypedDict

from music_assistant_models.enums import MediaType, QueueOption

from .menu import build_library_menu_items

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


class SlimBrowseItemResponse(TypedDict):
    """Response format for SlimBrowse commands that return lists of items.

    This is the structured JSON response sent over JSONRPC/CometD to Squeezebox
    hardware Controllers. The format is defined by the SlimBrowse protocol:
    https://lyrion.org/reference/slimbrowse/

    Note: This is NOT the LMS CLI text-protocol format. LMS CLI database commands
    return tagged parameter strings; these handlers serve the SlimBrowse layer instead.
    """

    item_loop: list[dict[str, Any]]
    offset: int
    count: int


class SlimBrowsePlaylistControlResponse(TypedDict):
    """Response format for the 'playlistcontrol' command over SlimBrowse.

    The command is documented at: https://lyrion.org/reference/cli/playlist/#playlistcontrol
    but the response is delivered as structured JSON via JSONRPC/CometD (SlimBrowse),
    not as a CLI text string.
    """

    count: int


class SlimBrowseTrackItem(TypedDict):
    """A single track entry in a SlimBrowse item_loop response.

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
    actions: dict[str, Any]


class SlimBrowseAlbumItem(TypedDict):
    """A single album entry in a SlimBrowse item_loop response.

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
    actions: dict[str, Any]


class SlimBrowseArtistItem(TypedDict):
    """A single artist entry in a SlimBrowse item_loop response.

    See: https://lyrion.org/reference/slimbrowse/
    """

    id: str
    artist: str
    icon: str
    artwork_url: str
    text: str
    style: str
    params: dict[str, Any]
    actions: dict[str, Any]


class SlimBrowsePlaylistItem(TypedDict):
    """A single playlist entry in a SlimBrowse item_loop response.

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
    actions: dict[str, Any]


def _get_image_url(mass: MusicAssistant, image: MediaItemImage | None) -> str:
    """Return a proxied image URL for the given image, or empty string."""
    if not image:
        return ""
    return mass.metadata.get_image_url(image, size=IMAGE_PROXY_SIZE)


def _track_to_item(mass: MusicAssistant, track: Track) -> SlimBrowseTrackItem:
    """Convert a Track to a SlimBrowse item_loop entry."""
    artist_name = ", ".join(a.name for a in track.artists) if track.artists else ""
    album_name = track.album.name if track.album else ""
    image_url = _get_image_url(mass, track.image)
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
    """Convert an Album to a SlimBrowse item_loop entry."""
    artist_name = ", ".join(a.name for a in album.artists) if album.artists else ""
    image_url = _get_image_url(mass, album.image)
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
    """Convert an Artist to a SlimBrowse item_loop entry."""
    image_url = _get_image_url(mass, artist.image)
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
    """Convert a Playlist to a SlimBrowse item_loop entry."""
    image_url = _get_image_url(mass, playlist.image)
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


def _playable_actions(uri: str) -> dict[str, Any]:
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


def _paginate(items: list, offset: int, total_count: int | None = None) -> SlimBrowseItemResponse:
    """Return a paginated SlimBrowse item_loop response.

    See: https://lyrion.org/reference/slimbrowse/

    :param items: The page of items to return.
    :param offset: The starting index of this page within the full result set.
    :param total_count: The total number of items available across all pages.
        If not provided, defaults to the length of the items list.
    """
    return {
        "item_loop": items,
        "offset": offset,
        "count": total_count if total_count is not None else len(items),
    }


async def _handle_artists(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'artists' browse command (SlimBrowse response).

    See: https://lyrion.org/reference/cli/database/#artists

    Supported parameters:
        - search: Filter artists by name substring.
        - artist_id: Return info for a specific artist.
        - album_id: Return artists that appear on a given album.
        - genre_id: Return artists in a given genre.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE
    search = kwargs.get("search")
    artist_id = kwargs.get("artist_id")
    album_id = kwargs.get("album_id")

    if artist_id:
        # Return info for the specific artist
        artist = await mass.music.artists.get_library_item(int(artist_id))
        items = [_artist_to_item(mass, artist)]
        return _paginate(items, 0, total_count=1)

    # Note: album_id and genre_id filters are not yet fully implemented in the
    # Music Assistant library API. For now, we fall through to the general listing.
    # TODO: Add filtering by album_id and genre_id when the library API supports it.

    artists = await mass.music.artists.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_artist_to_item(mass, artist) for artist in artists]
    return _paginate(items, offset)


async def _handle_albums(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'albums' browse command (SlimBrowse response).

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
        return _paginate(page, offset, total_count=len(all_items))

    albums = await mass.music.albums.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_album_to_item(mass, album) for album in albums]
    return _paginate(items, offset)


async def _handle_tracks(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'tracks' browse command (SlimBrowse response).

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
        return _paginate(page, offset, total_count=len(all_items))

    tracks = await mass.music.tracks.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_track_to_item(mass, track) for track in tracks]
    return _paginate(items, offset)


async def _handle_playlists(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'playlists' browse command (SlimBrowse response).

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
        return _paginate(page, offset, total_count=len(all_items))

    playlists = await mass.music.playlists.library_items(
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [_playlist_to_item(mass, playlist) for playlist in playlists]
    return _paginate(items, offset)


async def _handle_genres(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'genres' browse command (SlimBrowse response).

    See: https://lyrion.org/reference/cli/database/#genres
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else DEFAULT_PAGE_SIZE

    genres = await mass.music.genres.library_items(
        limit=limit,
        offset=offset,
    )
    items = [
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
    return _paginate(items, offset)


async def _handle_search(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowseItemResponse:
    """Handle the 'search' browse command (SlimBrowse response).

    Accepts both `term` (LMS CLI standard) and `search` (legacy/alias) parameters.

    Note: The LMS CLI spec returns separate contributors_loop, albums_loop, and
    tracks_loop in the response. This implementation returns a single flat item_loop
    mixing all result types, which is the expected format for SlimBrowse/SqueezePlay
    menu rendering on hardware Controllers.
    """
    offset = int(args[0]) if args else 0
    limit = int(args[1]) if len(args) > 1 else 10
    term = kwargs.get("term", kwargs.get("search", ""))

    if not term:
        return _paginate([], 0)

    results = await mass.music.search(
        search_query=str(term),
        media_types=[MediaType.ARTIST, MediaType.ALBUM, MediaType.TRACK, MediaType.PLAYLIST],
        limit=limit,
        library_only=True,
    )

    all_items: list[dict[str, Any]] = []
    for artist in results.artists:
        all_items.append(_artist_to_item(mass, artist))
    for album in results.albums:
        all_items.append(_album_to_item(mass, album))
    for track in results.tracks:
        all_items.append(_track_to_item(mass, track))
    for playlist in results.playlists:
        all_items.append(_playlist_to_item(mass, playlist))

    page = all_items[offset : offset + limit]
    return _paginate(page, offset, total_count=len(all_items))


async def _handle_playlistcontrol(
    mass: MusicAssistant,
    player_id: str,
    *args: Any,
    **kwargs: Any,
) -> SlimBrowsePlaylistControlResponse:
    """Handle the 'playlistcontrol' browse command (SlimBrowse response).

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
        queue_items = mass.player_queues.get_item(queue.queue_id)
        removed = 0
        for item in list(queue_items) if queue_items else []:
            if getattr(item, "uri", None) == uri:
                await mass.player_queues.delete_item(queue.queue_id, item.queue_item_id)
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
) -> SlimBrowseItemResponse:
    """Handle the 'favorites' browse command (SlimBrowse response).

    Note: The LMS CLI spec uses 'favorites items <start> <count>' with params like
    item_id, search, want_url, feedMode. This implementation is a Music Assistant
    adaptation that returns all favorited media (tracks, albums, artists, playlists)
    from the MA library as a flat SlimBrowse item_loop. It does not implement the
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

    items: list[dict[str, Any]] = []
    for track in tracks:
        items.append(_track_to_item(mass, track))
    for album in albums:
        items.append(_album_to_item(mass, album))
    for artist in artists:
        items.append(_artist_to_item(mass, artist))
    for playlist in playlists:
        items.append(_playlist_to_item(mass, playlist))

    page = items[offset : offset + limit]
    return _paginate(page, offset, total_count=len(items))


def register_browse_handlers(mass: MusicAssistant, slimproto: Any) -> None:
    """
    Register library browsing command handlers on the SlimServer.

    Handlers are dynamically set as methods on the SlimProtoCLI instance so that
    the CLI's command dispatch (which uses getattr) can find and invoke them.

    :param mass: The MusicAssistant instance for library access.
    :param slimproto: The SlimServer instance to register handlers on.
    """

    async def handle_artists(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_artists(mass, player_id, *args, **kwargs)

    async def handle_albums(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_albums(mass, player_id, *args, **kwargs)

    async def handle_tracks(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_tracks(mass, player_id, *args, **kwargs)

    async def handle_playlists(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_playlists(mass, player_id, *args, **kwargs)

    async def handle_genres(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_genres(mass, player_id, *args, **kwargs)

    async def handle_search(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_search(mass, player_id, *args, **kwargs)

    async def handle_playlistcontrol(
        player_id: str, *args: Any, **kwargs: Any
    ) -> SlimBrowsePlaylistControlResponse:
        return await _handle_playlistcontrol(mass, player_id, *args, **kwargs)

    async def handle_favorites(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        return await _handle_favorites(mass, player_id, *args, **kwargs)

    # Build the library menu items for the Squeezebox Controller's home menu
    library_menu_items = build_library_menu_items()

    # Wrap the existing menu handler to include library entries
    cli = slimproto.cli
    original_handle_menu = cli._handle_menu

    async def handle_menu(player_id: str, *args: Any, **kwargs: Any) -> SlimBrowseItemResponse:
        """Return library menu items merged with the original menu items."""
        original = await original_handle_menu(player_id, *args, **kwargs)
        original_items = original.get("item_loop", [])
        all_items = library_menu_items + original_items
        offset = int(args[0]) if args else int(kwargs.get("_index", 0))
        limit = int(args[1]) if len(args) > 1 else int(kwargs.get("_quantity", 200))
        page = all_items[offset : offset + limit]
        return {
            "item_loop": page,
            "offset": offset,
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
