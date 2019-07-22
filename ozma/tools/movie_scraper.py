# I mean, I can do thhis, but... why do I want to?


def get_extras(movie, tvdb_ai):
    movie = tvdb_ai.get_movie(movie.getID())
    # get cast, limit to 15
    cast_ids = [(person, person.getID()) for person in movie['cast'][:15]]
