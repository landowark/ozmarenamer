<h1>Ozma File Renamer</h1>

<h2>Settings File</h2>
Ozma will look for a file called "config.ini" in three places, taking the first one it finds:
1. The user's .config/ozma directory (/home/<user>/.config/ozma)
2. The user's .ozma directory (/home/<user>/.ozma)
3. The root directory of the ozma install directory.

The config.ini file should look like this:

```ini
[settings]
tv_schema = /home/user/tv/{series_name}/{series_name} Season{season_number}/{series_name}.S{season_number}E{episode_number}.{episode_name}.{extension}
movie_schema = /home/user/movies/{movie_name} ({year_of_release})/{movie_name} ({year_of_release}).{extension}
book_schema = /home/user/books/{author}/{series_name}/{book_title} ({year_of_release}){extension}
thetvdbkey = 754F7A3F73B01774
main_language = en
```
