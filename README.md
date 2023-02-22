### Automatic data analyst

This project is using the openai api to create a simple version of a data analyst. There is a frontend with a chat interface, where you can upload a dataset and then ask questions about it. When you ask a question then the "data analyst" will create a sql query, run it on the dataset and then either return a written conclusion or a plot (if the question for instance is "Show how the average movie rating has evolved over time" the answer will be a graph).

- You can see a short demo video here: https://youtu.be/aSLr4aKG6D4
- You can try it out here: http://146.190.232.44/

### Code
The frontend code is in the dashboard folder and the backend code is in the ada folder. The project can be installed by

```
conda env create -f environment.yml
conda activate ada
pip install -e .
```

Initial setup of the database, which is used for various caching can be done by running the following python code

```python
from ada import db_cache
from dashboard import db

db_cache.create_db_and_tables()
db.create_db_and_tables()
```

The dashboard can be started by running
```
python dashboard/chat.py
```

### Example
For reading the code the consider using the example provided in example.py and use that to debug through the code.


### Purpose
The purpose of this project is to play around with prompt engineering and see how easy it is to automate more cognitive demanding tasks. Some of the prompts used are heavily inspired by prompts used in langchain. I tried to code everything from scratch to see how much boilerplate code is needed to get a working system. The answer seems to be almost none.
