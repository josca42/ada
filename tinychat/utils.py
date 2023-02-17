import openai
from loguru import logger
from ada import db
from ada.config import config
import time


# openai.api_key = config["OPENAI_API_KEY"]

logger.add(config["DATA_DIR"] / "logs" / "ada.log")
logger = logger.opt(ansi=True)
logger.level("planner", no=33, color="<green>")
logger.level("data", no=33, color="<blue>")
logger.level("info", no=33, color="<black>")


def openai_completion(
    prompt,
    stop=None,
    model="text-davinci-003",
    temperature=0,
    max_tokens=2_000,
    api_key=None,
):
    completion = db.Completion(
        prompt=prompt,
        stop=stop,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )
    completion_stored = db.crud_completion.get(completion.hash_id)
    if completion_stored:
        return completion_stored.completion
    else:
        response = openai.Completion.create(
            prompt=prompt,
            model=model,
            temperature=temperature,
            stop=stop,
            max_tokens=max_tokens,
            api_key=api_key,
        )
        text = response["choices"][0].text
        completion.completion = text
        db.crud_completion.create(completion)
        return completion.completion


def log_input_output(log_input: bool = True, log_output: bool = True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            module_name = func.__module__.split(".")[-1]
            module_name = module_name if module_name in ["planner", "data"] else "info"
            if log_input:
                logger.log(module_name, f"Input arguments: {args[1:]}, {kwargs}")
            result = func(*args, **kwargs)
            if log_output:
                logger.log(module_name, f"Output result: {result}")
            return result

        return wrapper

    return decorator
