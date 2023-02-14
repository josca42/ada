from __future__ import annotations
from loguru import logger
from .utils import complete_prompt, log_input_output


planner_prompt_intro = """Answer the following questions as best you can. You have access to the following tools:

Summarizer: useful for when you need to summarize a text.
Plotter: userful for when you need to show a graph.
FooBar DB: useful for when you need to answer questions about FooBar or need to get data to show in graph. Input should be in the form of a question containing full context

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [Summarizer, Plotter, FooBar DB]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Action: the action to take, should be one of [Text, Plot] 
Final Answer: the final answer to the original input question

Begin!

"""

planner_prompt_context = """Question: {question}
Thought:"""


class Planner:
    """Base class for all orchestrator agents."""

    @log_input_output(log_input=True, log_output=False)
    def __init__(self, question: str, openai_api_key: str):
        self.question = question
        self.openai_api_key = openai_api_key
        self.prompt_intro = planner_prompt_intro
        self.prompt = planner_prompt_intro + planner_prompt_context.format(
            question=question
        )

    def next_step(self, stop: str = "\nObservation:", max_tokens: int = 2_000) -> str:
        action = complete_prompt(
            self.prompt,
            stop=stop,
            max_tokens=max_tokens,
            openai_api_key=self.openai_api_key,
        )
        self.prompt = self.prompt + f"{action.completion}"
        return action.completion

    def add_information(self, observation: str) -> None:
        self.prompt = self.prompt + "\nObservation: " + observation + "\nThought:"

    def __iter__(self, max_steps=5) -> str:
        for i in range(max_steps):
            step = self.next_step()
            thought, action, action_input = step.split("\n")
            action_out = dict(
                tool=action.split(":")[-1].strip(),
                input=action_input.split(":")[-1].strip(),
            )
            if "\nFinal Answer:" in step:
                break
            else:
                yield action_out
        yield action_out
