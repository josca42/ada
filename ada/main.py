from ada.agents.data import Files
from ada.agents.planner import Planner
from ada.agents.plotter import get_plot_code


# files = Files(files_dir_path="/Users/josca/projects/ada/data/data_files")


def data_analyst_action(question: str, data_agent, openai_api_key: str) -> dict:
    data = {}
    data_agent.openai_api_key = openai_api_key
    plan = Planner(question=question, openai_api_key=openai_api_key)
    for action in plan:
        if action["tool"] == "FooBar DB":
            obs = data_agent.query(question=action["input"])
            data["data"] = obs["data"]
            plan.add_information(obs["text"])
        elif action["tool"] == "Plotter":
            input_context = plan.prompt.replace(plan.prompt_intro, "").strip()
            code = get_plot_code(
                input_context=input_context,
                question=action["input"],
                openai_api_key=openai_api_key,
            )
            data["code"] = code
            plan.add_information(code)
        else:
            pass
    return dict(action=action, data=data)


if __name__ == "__main__":
    question = "What is the most common movie rating?"
    answer = data_analyst_action(question)

    question = "Show how the mean movie rating has changed over time?"
    answer = data_analyst_action(question)
