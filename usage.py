import os
import time
import sys
import logging

from deezer import Deezer
import spotipy
from plexapi.server import PlexServer
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth, CacheFileHandler
from helper import *
from download import download_tracks

logger = logging.getLogger("spotify-plex-sync")
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S')

# Read ENV variables
PLEX_URL = os.environ.get('PLEX_URL')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
PLEX_MUSIC_LIBARY = os.getenv("PLEX_MUSIC_LIBRARY", "")

DEBUG = (os.getenv("DEBUG","False") == "True")

SPOTIPY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_USER_ID = os.environ.get('SPOTIFY_USER_ID')
DOWNLOAD_MISSING = (os.getenv("DOWNLOAD_MISSING",'False') == "True")
DOWNLOAD_ALBUM = (os.getenv("DOWNLOAD_ALBUM",'False') == "True")
MUSIC_PATH = os.getenv("MUSIC_PATH", "/music")
DEEZER_ARL = os.environ.get('DEEZER_ARL')

if DEBUG:
    logger.setLevel(logging.DEBUG)

def auth_spotify(client_id: str, client_secret: str, scope: str = "user-library-read"):
    """Creates a spotify authenticator

    Args:
        client_id (str): Spotify client ID
        client_secret (str): Spotify client secret

    Returns:
        sp: spotify configured client
    """
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost",
        scope=scope,
        open_browser=False,
        cache_handler=CacheFileHandler("/oauth/.cache")
        )
    )


if __name__ == "__main__":
    logger.info("Starting playlist sync")

    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    except Exception as e:
        if DEBUG:
            raise e
        logger.error("Plex Authorization error")
        sys.exit(1)

    if DOWNLOAD_MISSING:
        try:
            dz = Deezer()  
            dz.login_via_arl(DEEZER_ARL)
        except: 
            logger.error("Failed to authentication to Deezer")
            sys.exit(1)

    try:
        sp = auth_spotify(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET)
    except Exception as e:
        if DEBUG:
            raise e
        logger.info("Spotify Authorization error")
        sys.exit(1)

    logger.info("Starting spotify saved track sync")
    try:
        sp_saved_tracks = get_sp_user_saved_tracks(sp)
        if DOWNLOAD_MISSING:
            deemix_tracks = [(track['track']['name'], track['track']['artists'][0]['name'], track['track']['album']['name']) for track in sp_saved_tracks]
            download_tracks(dz, deemix_tracks, DOWNLOAD_ALBUM, DEBUG)
        plex_tracks = [(track['track']['name'], track['track']['artists'][0]['name']) for track in sp_saved_tracks]
        trackList = get_available_plex_tracks(plex, plex_tracks)
        create_plex_playlist(plex, tracksList=trackList,
                                playlistName="Saved Songs [Spotify]")
    except Exception as e:
        if DEBUG:
            raise e
        logger.error("Failed to retrieve saved tracks")


    logger.info("Starting spotify playlist sync")
    try:
        sp_playlists = get_sp_user_playlists(sp=sp, userId=SPOTIFY_USER_ID)
        for playlist, name in sp_playlists:
            tracks = get_sp_playlist_tracks(sp, SPOTIFY_USER_ID, playlist)
            if DOWNLOAD_MISSING:
                deemix_tracks = [(track['track']['name'], track['track']['artists'][0]['name'], track['track']['album']['name']) for track in tracks]
                download_tracks(dz, deemix_tracks, DOWNLOAD_ALBUM, DEBUG)
            plex_tracks = [(track['track']['name'], track['track']['artists'][0]['name']) for track in tracks]
            trackList = get_available_plex_tracks(plex, plex_tracks)
            create_plex_playlist(plex, tracksList=trackList,
                                playlistName=f"{name} [Spotify]")
        logger.info("Spotify playlist sync complete")
    except Exception as e:
        if DEBUG:
            raise e
        logger.error("Failed to retrieve playlists")

    if PLEX_MUSIC_LIBARY:
        logger.info(f"Updating Plex Library \"{PLEX_MUSIC_LIBARY}\"")
        update_plex_library(plex, PLEX_MUSIC_LIBARY)

    logger.info("All playlist(s) sync complete")
