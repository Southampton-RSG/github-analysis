import typing

from decouple import config
import pymongo

database_url = config('DATABASE_URL', default='mongodb://localhost:27017/')
client = pymongo.MongoClient(database_url)
db = client['github']


def collection(name: str, indexes: typing.Optional[typing.Iterable[str]] = None):
    collection = db[name]
    collection.create_index('_repo_name')

    if indexes is not None:
        for index in indexes:
            collection.create_index(index)

    return collection
