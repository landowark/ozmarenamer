from mutagen.easymp4 import EasyMP4
from mutagen.oggopus import OggOpus
import logging
import jinja2

logger = logging.getLogger("ozma.tools.muta")

mp4_list = [".m4v", ".m4a", ".mp4"]
opus_list = [".opus"]

def mutate_song(media_info:dict):
    if media_info['filepath'].suffix in mp4_list:
        mut_file = EasyMP4(media_info['filepath'].__str__())
    elif media_info['filepath'].suffix in opus_list:
        mut_file = OggOpus(media_info['filepath'].__str__())
    else:
        return
    mut_file['TRACKNUMBER'] = str(media_info['track_number'])
    mut_file['TITLE'] = media_info['track_title']
    mut_file['ALBUM'] = media_info['album_name']
    mut_file['ARTIST'] = media_info['artist_name']
    logger.debug("Mutating song.")
    mut_file.save(media_info['filepath'].__str__())


def mutate_tv(media_info:dict):
    if media_info['filepath'].suffix in mp4_list:
        mut_file = EasyMP4(media_info['filepath'].__str__())
    template = jinja2.Template("{{ series_name }} S{{ '%02d' % season_number }}E{{ '%02d' % episode_number }} - {{ episode_name }}")
    mut_file['TITLE'] = template.render(media_info)
    logger.debug("Mutating tv episode.")
    mut_file.save(media_info['filepath'].__str__())


def mutate_movie(media_info:dict):
    if media_info['filepath'].suffix in mp4_list:
        mut_file = EasyMP4(media_info['filepath'].__str__())
    template = jinja2.Template("{{ movie_title }} - ({{ movie_release_year }})")
    mut_file['TITLE'] = template.render(media_info)
    logger.debug("Mutating movie.")
    mut_file.save(media_info['filepath'].__str__())