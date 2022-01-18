import logging
import sys
from difflib import SequenceMatcher
from typing import List

import spotipy
from plexapi.exceptions import BadRequest, NotFound
from plexapi.server import PlexServer

################### Spotify helpers ###################
logger = logging.getLogger("spotify-plex-sync")


def get_sp_user_playlists(sp: spotipy.Spotify, userId: str):
    """Gets all the playlist URIs for the given userId

    Args:
        sp (spotipy.Spotify): Spotify configured instance
        userId (str): UserId of the spotify account (get it from open.spotify.com/account)

    Returns:
        tuple(list[str], list[str]): list of URIs, list of playlist names
    """
    playlists = sp.user_playlists(userId)
    return [[playlist['uri'], playlist['name']] for playlist in playlists['items']]

def get_sp_user_saved_tracks(sp: spotipy.Spotify):
    results = sp.current_user_saved_tracks()
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def get_sp_playlist_tracks(sp, userId: str, playlistId: str):
    """Gets tracks in a given playlist

    Args:
        sp ([type]): Spotify configured instance
        userId (str): UserId of the spotify account (get it from open.spotify.com/account)
        playlistId (str): Playlist URI

    Returns:
        List: A list of track objects
    """
    results = sp.user_playlist_tracks(userId, playlistId)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

######################## Deezer Helpers #########################

def get_dz_track_from_name(dz, track_name: str, artist: str, album: str):
    result = dz.api.advanced_search(track=track_name, artist=artist, album=album)
    if result["total"] == 0:
        logger.warning(f"Not results found for track {track_name} by {artist}")
        return None
    return result

################### Playlist Creation helpers ###################


def get_available_plex_tracks(plex: PlexServer, trackZip: List) -> List:
    """For the given spotify track names returns a list of plex.audio.track objects
        - Empty list if none of the tracks are found in Plex

    Args:
        plex (PlexServer): A configured PlexServer instance
        trackNames (List): List of track names

    Returns:
        List: of track objects
    """
    musicTracks = []
    for track, artist in trackZip:
        try:
            search = plex.search(track, mediatype='track', limit=5)
        except BadRequest:
            logger.warning("failed to search %s on plex", track)
            search = []
        if not search:
            logger.debug("retrying search for %s", track)
            try:
                search = plex.search(
                    track.split('(')[0], mediatype='track', limit=5
                )
                logger.debug("search for %s successful", track)
            except BadRequest:
                logger.warning("unable to query %s on plex", track)
                search = []

        if search:
            for s in search:
                try:
                    artistSimilarity = SequenceMatcher(
                        None, s.artist().title.lower(), artist.lower()
                    ).quick_ratio()
                    if s.artist().title.lower() == artist.lower() or artistSimilarity >= 0.8:
                        musicTracks.extend(s)
                        break

                except IndexError:
                    logger.info(
                        "Looks like plex mismatched the search for %s, retrying with next result", track)
    return musicTracks


def create_new_plex_playlist(plex: PlexServer, tracksList: List, playlistName: str) -> None:
    """Creates a new plex playlist with given name and tracks

    Args:
        plex (PlexServer): A configured PlexServer instance
        tracksList (List): List of plex.audio.track objects
        playlistName (str): Name of the playlist
    """
    plex.createPlaylist(title=playlistName, items=tracksList)


def create_plex_playlist(plex: PlexServer, tracksList: List, playlistName: str) -> None:
    """Deletes existing playlist (if exists) and
    creates a new playlist with given name and playlist name

    Args:
        plex (PlexServer): A configured PlexServer instance
        tracksList (List):List of plex.audio.track objects
        playlistName (str): Name of the playlist
    """
    if tracksList:
        try:
            plexPlaylist = plex.playlist(playlistName)
            plexPlaylist.delete()
            logger.info("Deleted existing playlist %s", playlistName)
            create_new_plex_playlist(plex, tracksList, playlistName)
            logger.info("Created playlist %s", playlistName)

        except NotFound:
            create_new_plex_playlist(plex, tracksList, playlistName)
            logger.info("Created playlist %s", playlistName)
    else:
        logger.info(
            "No songs for playlist %s were found on plex, skipping the playlist", playlistName)

def update_plex_library(plex: PlexServer, library_name: str) -> None:
    plex.library.section(library_name).update()