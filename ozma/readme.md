<h1>Ozma File Renamer</h1>

<h2>Settings File</h2>
The settings file should be placed in the root directory (ie ozma_renamer) and should look like this:

```ini
[settings]
tv_schema = /home/user/tv/{series_name}/{series_name} Season{season_number}/{series_name}.S{season_number}E{episode_number}.{episode_name}.{extension}
movie_schema = /home/user/movies/{movie_name} ({year_of_release})/{movie_name} ({year_of_release}).{extension}
book_schema = /home/user/books/{author}/{series_name}/{book_title} ({year_of_release}){extension}
thetvdbkey = 754F7A3F73B01774
main_language = en
```
