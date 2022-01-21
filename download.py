import deemix
import logging
from typing import List, Tuple
from helper import get_dz_track_from_name
from deezer import TrackFormats
from deemix.downloader import Downloader

logger = logging.getLogger("spotify-plex-sync")

settings = deemix.settings.DEFAULTS
settings.update({
  "createArtistFolder": True,
  "createStructurePlaylist": True,
  "createSingleFolder": True,
  "maxBitrate": "9",
  "fallbackBitrate": True,
  "fallbackSearch": True,
  "albumNameTemplate": "%album% (%year%)",
})

def download_tracks(dz, track_list: List[Tuple[str,str,str]], download_album: bool = False, music_path: str = "/music", bitrate: TrackFormats = TrackFormats.FLAC):
  settings.update({"downloadLocation": music_path})
  for track_name, artist, album in track_list:
    try:
      track = get_dz_track_from_name(dz,track_name,artist,album)
      if not track: continue
      if download_album:
        album = dz.api.get_album(track["data"][0]["album"]["id"])
        link = album["link"]
      else:
        link = track["data"][0]["link"]
      dl = deemix.generateDownloadObject(dz, link, bitrate)
      downloader = Downloader(dz, dl, settings)
      downloader.start()
    except:
      logger.error(f"Failed to download track {track_name} by {artist}")