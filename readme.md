<h1>Ozma File Renamer</h1>

Ozma File Renamer is a commandline utility designed to rename your media files based on input from IMDB for movies and TV series and Lastfm for music.
Ozma supports local file movement as well as smb network file transfers.

<h2>Installation</h2>

Currently Ozma installation is handled through git only. The best practice is to create a virtualenv using python's venv module.

```bash
git clone https://github.com/landowark/ozmarenamer.git
cd ozmarenamer
python -m venv venv
/path/to/venv/bin/pip install -r requirements.txt
```
<h2>Usage</h2>

Ozma can be used by calling ozma_cli.py from the commandline and specifying the input file path.

```bash
python ozma_cli.py /home/{user}/DVDrips/futurama S02E18.m4v
```

<h3>Settings File</h3>
Current best practice for Ozma is to create a config.ini settings file.

Ozma will look for a file called "config.ini" in three places, taking the first one it finds:
1. The user's .config/ozma directory (/home/{user}/.config/ozma)
2. The user's .ozma directory (/home/{user}/.ozma)
3. The root directory of the ozma install directory.

The basic config.ini file should look something like this:

```ini
[settings]
destination_dir = smb://${smb:smb_host}/
main_language = en
move = False

[smb]
smb_user = {user}
smb_pass = {password}
smb_host = {host ip}

[song]
lastfmkey = {key}
lastfmsec = {secret}
song_schema = music/{{ artist_name }}/{{ album_name }}/{{ '%02d' % track_number }} - {{ track_title }}{{ extension }}

[tv]
tv_schema = tv/{{ series_name }}/{{ series_name }} Season{{ '%02d' % season_number }}/S{{ '%02d' % season_number }}E{{ '%02d' % episode_number }}.{{ episode_name }}/{{ series_name }}.S{{ '%02d' % season_number }}E{{ '%02d' % episode_number }}.{{ episode_name }}{{ extension }}

[movie]
movie_schema = movies/{{ movie_title }} ({{ movie_release_year }})/{{ movie_title }} ({{ movie_release_year }}){{ extension }}
```

By default Ozma will use 'destination_dir' in the settings section as the root directory for all media files. This can be overridden on a media type basis by including {media_type}_destination entry in the appropriate media section. For example:

```ini
[tv]
tv_destination = /home/{user}/tv/
tv_schema = {{ series_name }}/{{ series_name }} Season{{ '%02d' % season_number }}/{{ series_name }}.S{{ '%02d' % season_number }}E{{ '%02d' % episode_number }}.{{ episode_name }}{{ extension }}
```

...Will move an episode of Futurama to /home/{user}//tv/Futurama/Futurama Season02/Futurama.S02E18.The Problem with Popplers.m4v

<h3>Command Line</h3>

The destination directory can also be overridden using the commandline argument -d