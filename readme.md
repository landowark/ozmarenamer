<h1>Ozma File Renamer</h1>

<h2>Settings File</h2>
The settings file should be placed in the root directory (ie ozma_renamer) and should look like this:

```yaml
tv:
    tv_schema: /home/user/tv/{{series_name}}/{{series_name}} Season{{season_number}}/{{series_name}}.S{{season_number}}E{{episode_number}}.{{episode_name}}.{{extension}}
movie:
    movie_schema: /home/user/movies/{{movie_name}} ({{year_of_release}})/{{movie_name}} ({{year_of_release}}).{{extension}}
main_language: en
```
