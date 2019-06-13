import os
from .setup import get_config, get_params, get_filepath
from .tools import *
from pytvdbapi import api


class MediaParser():

    def __init__(self):
        self.settings = dict(**get_params(), **get_config())
        self.FUNCTION_MAP = {"book": self.search_book,
                             "tv": self.search_tv,
                             "movie": self.search_movie,
                             "audio": self.search_audio}

    def parse_file(self):
        self.filepath = get_filepath()
        self.extenstion = get_extension(self.filepath)
        self.mediatype = get_media_type(self.extenstion)
        self.filename, self.season, self.episode, self.disc = get_parsible_file_name(self.filepath)
        if self.mediatype == 'video':
            if self.season:
                self.mediatype = 'tv'
            else:
                self.mediatype = 'movie'
        self.mediapath = self.settings["{}_path".format(self.mediatype)]
        func = self.FUNCTION_MAP[self.mediatype]
        print(self.__dict__)
        func()
        return self.filepath, os.path.join(self.settings['tv_path'], self.final_filename)

    def search_book(self):
        print("searching book")

    def search_tv(self):
        print("searching tv")
        self.tvdb_apikey = self.settings['thetvdbkey']
        tvdb = api.TVDB(self.tvdb_apikey)
        series = tvdb.search(self.filename, self.settings['main_language'])[0]
        self.series_name = series.SeriesName
        if self.disc:
            # todo find way to get episode from dvd disc number / episode number
            pass
        self.episode_name = series[self.season][self.episode].EpisodeName
        self.final_filename = self.settings['tv_schema'].format(
            series_name=self.series_name,
            season_number=str(self.season).zfill(2),
            episode_number=str(self.episode).zfill(2),
            episode_name=self.episode_name,
            extension=self.extenstion)


    def search_movie(self):
        print("searching movie")


    def search_audio(self):
        print("searching audio")


def main():
    mParser = MediaParser()
    file_source, file_destination = mParser.parse_file()
    print("Moving {} to {}.".format(file_source, file_destination))