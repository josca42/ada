from functools import partial
from ada.utils import openai_completion
from ada import tools


def data_analyst(question: str, openai_api_key: str, data_dir) -> dict:
    action_data = {}
    llm = partial(
        openai_completion,
        api_key=openai_api_key,
        temperature=0,
        model="text-davinci-003",
        max_tokens=2_000,
    )
    data = tools.data.Files.load(data_dir=data_dir, llm=llm)
    plan = tools.plan.Planner(question=question, llm=llm)
    plot = partial(tools.plot.ploty_plots, llm=llm)

    for action in plan:
        if action["tool"] == "FooBar DB":
            obs = data.query(question=action["input"])
            action_data["data"] = obs["data"]
            plan.add_information(obs["text"])
        elif action["tool"] == "Plotter":
            input_context = plan.prompt.replace(plan.prompt_intro, "").strip()
            code = plot(
                input_context=input_context,
                question=action["input"],
            )
            action_data["code"] = code
            plan.add_information(code)
        else:
            pass
    return dict(action=action, action_data=action_data)


if __name__ == "__main__":
    question = "What is the most common movie rating?"
    answer = data_analyst(question)

    question = "Show how the mean movie rating has changed over time?"
    answer = data_analyst(question)
