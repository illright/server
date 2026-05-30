"""Tests for the squeezelite browse module."""

from __future__ import annotations

import importlib.util
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from music_assistant_models.enums import QueueOption
from music_assistant_models.media_items import (
    Album,
    Artist,
    Playlist,
    ProviderMapping,
    Track,
)

# Load the browse module directly to avoid the full music_assistant import chain
# which requires Python 3.14+ and many heavy dependencies not needed for unit tests.
_browse_spec = importlib.util.spec_from_file_location(
    "squeezelite_browse",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "music_assistant",
        "providers",
        "squeezelite",
        "browse.py",
    ),
)
_browse_mod = importlib.util.module_from_spec(_browse_spec)

# Stub the TYPE_CHECKING import of MusicAssistant
_browse_mod.__dict__["TYPE_CHECKING"] = False
_browse_spec.loader.exec_module(_browse_mod)

_build_library_menu_items = _browse_mod._build_library_menu_items
_handle_albums = _browse_mod._handle_albums
_handle_artists = _browse_mod._handle_artists
_handle_favorites = _browse_mod._handle_favorites
_handle_playlistcontrol = _browse_mod._handle_playlistcontrol
_handle_playlists = _browse_mod._handle_playlists
_handle_search = _browse_mod._handle_search
_handle_tracks = _browse_mod._handle_tracks
_paginate = _browse_mod._paginate
register_browse_handlers = _browse_mod.register_browse_handlers


# --- Fixtures ---


def _make_provider_mapping(item_id: str = "1") -> set[ProviderMapping]:
    return {ProviderMapping(item_id=item_id, provider_domain="test", provider_instance="test_1")}


def _make_artist(item_id: str = "1", name: str = "Test Artist") -> Artist:
    return Artist(
        item_id=item_id,
        provider="test",
        name=name,
        uri=f"test://artist/{item_id}",
        provider_mappings=_make_provider_mapping(item_id),
    )


def _make_album(item_id: str = "1", name: str = "Test Album", artists: list | None = None) -> Album:
    return Album(
        item_id=item_id,
        provider="test",
        name=name,
        uri=f"test://album/{item_id}",
        year=2024,
        artists=artists or [_make_artist()],
        provider_mappings=_make_provider_mapping(item_id),
    )


def _make_track(
    item_id: str = "1",
    name: str = "Test Track",
    artists: list | None = None,
    album: Album | None = None,
) -> Track:
    return Track(
        item_id=item_id,
        provider="test",
        name=name,
        uri=f"test://track/{item_id}",
        duration=240,
        artists=artists or [_make_artist()],
        album=album or _make_album(),
        provider_mappings=_make_provider_mapping(item_id),
    )


def _make_playlist(item_id: str = "1", name: str = "Test Playlist") -> Playlist:
    return Playlist(
        item_id=item_id,
        provider="test",
        name=name,
        uri=f"test://playlist/{item_id}",
        provider_mappings=_make_provider_mapping(item_id),
    )


def _make_mass_mock() -> MagicMock:
    """Create a MusicAssistant mock with library controllers."""
    mass = MagicMock()
    mass.metadata.get_image_url = MagicMock(return_value="")
    mass.music.artists.library_items = AsyncMock(return_value=[])
    mass.music.artists.get_library_item = AsyncMock()
    mass.music.artists.albums = AsyncMock(return_value=[])
    mass.music.albums.library_items = AsyncMock(return_value=[])
    mass.music.albums.get_library_item = AsyncMock()
    mass.music.albums.tracks = AsyncMock(return_value=[])
    mass.music.tracks.library_items = AsyncMock(return_value=[])
    mass.music.playlists.library_items = AsyncMock(return_value=[])
    mass.music.playlists.get_library_item = AsyncMock()
    mass.music.playlists.tracks = AsyncMock(return_value=[])
    mass.music.genres.library_items = AsyncMock(return_value=[])
    mass.music.search = AsyncMock()
    mass.player_queues.get_active_queue = MagicMock(return_value=None)
    mass.player_queues.play_media = AsyncMock()
    return mass


# --- Tests for _paginate ---


class TestPaginate:
    """Tests for the _paginate helper."""

    def test_basic_pagination(self):
        """Paginate returns items with offset and count."""
        items = [{"id": "1"}, {"id": "2"}]
        result = _paginate(items, 0)
        assert result == {"item_loop": items, "offset": 0, "count": 2}

    def test_with_total_count(self):
        """Count uses total_count when provided."""
        items = [{"id": "1"}]
        result = _paginate(items, 5, total_count=100)
        assert result["count"] == 100
        assert result["offset"] == 5


# --- Tests for _handle_artists ---


class TestHandleArtists:
    """Tests for the artists browse handler."""

    @pytest.mark.asyncio
    async def test_returns_artists_from_library(self):
        """Handler returns artist items from the library."""
        mass = _make_mass_mock()
        artists = [_make_artist("1", "Artist A"), _make_artist("2", "Artist B")]
        mass.music.artists.library_items = AsyncMock(return_value=artists)

        result = await _handle_artists(mass, "player1", 0, 50)

        assert len(result["item_loop"]) == 2
        assert result["item_loop"][0]["artist"] == "Artist A"
        assert result["item_loop"][1]["artist"] == "Artist B"
        mass.music.artists.library_items.assert_called_once_with(search=None, limit=50, offset=0)

    @pytest.mark.asyncio
    async def test_artist_id_redirects_to_albums(self):
        """When artist_id is given, returns albums for that artist."""
        mass = _make_mass_mock()
        artist = _make_artist("5", "Artist X")
        album = _make_album("10", "Album X", artists=[artist])
        mass.music.artists.get_library_item = AsyncMock(return_value=artist)
        mass.music.artists.albums = AsyncMock(return_value=[album])

        result = await _handle_artists(mass, "player1", 0, 50, artist_id="5")

        assert len(result["item_loop"]) == 1
        assert result["item_loop"][0]["album"] == "Album X"


# --- Tests for _handle_albums ---


class TestHandleAlbums:
    """Tests for the albums browse handler."""

    @pytest.mark.asyncio
    async def test_returns_albums_from_library(self):
        """Handler returns album items from the library."""
        mass = _make_mass_mock()
        albums = [_make_album("1", "Album A"), _make_album("2", "Album B")]
        mass.music.albums.library_items = AsyncMock(return_value=albums)

        result = await _handle_albums(mass, "player1", 0, 50)

        assert len(result["item_loop"]) == 2
        assert result["item_loop"][0]["album"] == "Album A"

    @pytest.mark.asyncio
    async def test_album_item_contains_go_action(self):
        """Album items include a 'go' action for drilling into tracks."""
        mass = _make_mass_mock()
        mass.music.albums.library_items = AsyncMock(return_value=[_make_album()])

        result = await _handle_albums(mass, "player1", 0, 50)

        item = result["item_loop"][0]
        assert "go" in item["actions"]
        assert item["actions"]["go"]["cmd"] == ["tracks"]


# --- Tests for _handle_tracks ---


class TestHandleTracks:
    """Tests for the tracks browse handler."""

    @pytest.mark.asyncio
    async def test_returns_tracks_from_library(self):
        """Handler returns track items from the library."""
        mass = _make_mass_mock()
        tracks = [_make_track("1", "Song A"), _make_track("2", "Song B")]
        mass.music.tracks.library_items = AsyncMock(return_value=tracks)

        result = await _handle_tracks(mass, "player1", 0, 50)

        assert len(result["item_loop"]) == 2
        assert result["item_loop"][0]["track"] == "Song A"

    @pytest.mark.asyncio
    async def test_album_id_returns_album_tracks(self):
        """When album_id is given, returns tracks for that album."""
        mass = _make_mass_mock()
        album = _make_album("3", "Album Y")
        tracks = [_make_track("10", "Track 1"), _make_track("11", "Track 2")]
        mass.music.albums.get_library_item = AsyncMock(return_value=album)
        mass.music.albums.tracks = AsyncMock(return_value=tracks)

        result = await _handle_tracks(mass, "player1", 0, 50, album_id="3")

        assert len(result["item_loop"]) == 2
        assert result["count"] == 2


# --- Tests for _handle_playlists ---


class TestHandlePlaylists:
    """Tests for the playlists browse handler."""

    @pytest.mark.asyncio
    async def test_returns_playlists(self):
        """Handler returns playlist items."""
        mass = _make_mass_mock()
        playlists = [_make_playlist("1", "My Playlist")]
        mass.music.playlists.library_items = AsyncMock(return_value=playlists)

        result = await _handle_playlists(mass, "player1", 0, 50)

        assert len(result["item_loop"]) == 1
        assert result["item_loop"][0]["playlist"] == "My Playlist"

    @pytest.mark.asyncio
    async def test_playlist_id_returns_tracks(self):
        """When playlist_id is given, returns tracks in that playlist."""
        mass = _make_mass_mock()
        playlist = _make_playlist("5", "Chill Mix")
        tracks = [_make_track("1", "Chill Song")]
        mass.music.playlists.get_library_item = AsyncMock(return_value=playlist)
        mass.music.playlists.tracks = AsyncMock(return_value=tracks)

        result = await _handle_playlists(mass, "player1", 0, 50, playlist_id="5")

        assert len(result["item_loop"]) == 1
        assert result["item_loop"][0]["track"] == "Chill Song"


# --- Tests for _handle_playlistcontrol ---


class TestHandlePlaylistControl:
    """Tests for the playlistcontrol handler."""

    @pytest.mark.asyncio
    async def test_play_media(self):
        """Handler calls play_media with correct queue option."""
        mass = _make_mass_mock()
        queue = MagicMock()
        queue.queue_id = "queue_1"
        mass.player_queues.get_active_queue = MagicMock(return_value=queue)

        result = await _handle_playlistcontrol(mass, "player1", cmd="play", uri="test://track/1")

        assert result == {"count": 1}
        mass.player_queues.play_media.assert_called_once_with(
            "queue_1", "test://track/1", option=QueueOption.PLAY
        )

    @pytest.mark.asyncio
    async def test_no_uri_returns_zero_count(self):
        """Handler returns count 0 when no URI is provided."""
        mass = _make_mass_mock()
        result = await _handle_playlistcontrol(mass, "player1", cmd="play", uri="")
        assert result == {"count": 0}

    @pytest.mark.asyncio
    async def test_no_queue_returns_zero_count(self):
        """Handler returns count 0 when no active queue exists."""
        mass = _make_mass_mock()
        mass.player_queues.get_active_queue = MagicMock(return_value=None)

        result = await _handle_playlistcontrol(mass, "player1", cmd="play", uri="test://track/1")
        assert result == {"count": 0}

    @pytest.mark.asyncio
    async def test_add_option(self):
        """Handler maps 'add' cmd to QueueOption.ADD."""
        mass = _make_mass_mock()
        queue = MagicMock()
        queue.queue_id = "queue_1"
        mass.player_queues.get_active_queue = MagicMock(return_value=queue)

        await _handle_playlistcontrol(mass, "player1", cmd="add", uri="test://track/1")

        mass.player_queues.play_media.assert_called_once_with(
            "queue_1", "test://track/1", option=QueueOption.ADD
        )


# --- Tests for _handle_favorites ---


class TestHandleFavorites:
    """Tests for the favorites handler."""

    @pytest.mark.asyncio
    async def test_returns_all_favorite_types(self):
        """Handler aggregates favorites across all media types."""
        mass = _make_mass_mock()
        mass.music.tracks.library_items = AsyncMock(return_value=[_make_track()])
        mass.music.albums.library_items = AsyncMock(return_value=[_make_album()])
        mass.music.artists.library_items = AsyncMock(return_value=[_make_artist()])
        mass.music.playlists.library_items = AsyncMock(return_value=[_make_playlist()])

        result = await _handle_favorites(mass, "player1", 0, 50)

        assert result["count"] == 4
        assert len(result["item_loop"]) == 4


# --- Tests for _build_library_menu_items ---


class TestBuildLibraryMenuItems:
    """Tests for the library menu builder."""

    def test_returns_expected_menu_entries(self):
        """Menu includes all required library categories."""
        items = _build_library_menu_items()
        ids = [item["id"] for item in items]
        assert "myMusicArtists" in ids
        assert "myMusicAlbums" in ids
        assert "myMusicTracks" in ids
        assert "myMusicPlaylists" in ids
        assert "myMusicFavorites" in ids
        assert "myMusicSearch" in ids

    def test_search_has_input_field(self):
        """Search menu item has an input configuration for text entry."""
        items = _build_library_menu_items()
        search_item = next(i for i in items if i["id"] == "myMusicSearch")
        assert "input" in search_item
        assert search_item["input"]["len"] == 1

    def test_all_items_have_go_action(self):
        """Every menu item has a 'go' action with a command."""
        items = _build_library_menu_items()
        for item in items:
            assert "go" in item["actions"]
            assert "cmd" in item["actions"]["go"]


# --- Tests for register_browse_handlers ---


class TestRegisterBrowseHandlers:
    """Tests for handler registration."""

    def test_registers_all_handlers_on_cli(self):
        """All library commands and menu override are registered on the CLI."""
        mass = _make_mass_mock()
        slimproto = MagicMock()
        slimproto.cli = MagicMock()
        # Set up original _handle_menu as an async function
        slimproto.cli._handle_menu = AsyncMock(
            return_value={"item_loop": [], "offset": 0, "count": 0}
        )

        register_browse_handlers(mass, slimproto)

        assert hasattr(slimproto.cli, "_handle_artists")
        assert hasattr(slimproto.cli, "_handle_albums")
        assert hasattr(slimproto.cli, "_handle_tracks")
        assert hasattr(slimproto.cli, "_handle_playlists")
        assert hasattr(slimproto.cli, "_handle_genres")
        assert hasattr(slimproto.cli, "_handle_search")
        assert hasattr(slimproto.cli, "_handle_playlistcontrol")
        assert hasattr(slimproto.cli, "_handle_favorites")
        assert hasattr(slimproto.cli, "_handle_menu")

    @pytest.mark.asyncio
    async def test_menu_handler_includes_library_items(self):
        """Overridden menu handler includes library items plus original presets."""
        mass = _make_mass_mock()
        slimproto = MagicMock()
        slimproto.cli = MagicMock()
        preset_item = {"id": "preset_1", "text": "My Preset"}
        slimproto.cli._handle_menu = AsyncMock(
            return_value={"item_loop": [preset_item], "offset": 0, "count": 1}
        )

        register_browse_handlers(mass, slimproto)

        # Call the overridden menu handler
        result = await slimproto.cli._handle_menu("player1", 0, 200)

        ids = [item["id"] for item in result["item_loop"]]
        assert "myMusicArtists" in ids
        assert "preset_1" in ids
