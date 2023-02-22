from ada import data, data_analyst

# if sqlite database for caching has not been created uncomment below
# from ada import db_cache
# db_cache.create_db_and_tables()

openai_api_key = "insert your openai api key here"
data_dir = "data/imdb"
question = "Show how the average rating of movies has changed over time."

data_fetcher = data.Files(data_dir=data_dir, persist_data=False)
response = data_analyst(
    question=question,
    openai_api_key=openai_api_key,
    data_fetcher=data_fetcher,
)
