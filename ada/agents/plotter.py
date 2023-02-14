from .utils import complete_prompt, log_input_output

plotter_prompt_template = """I want you to act as a data scientist and code for me. Given an input question and an input summary please write code for visualizing the data in the dataframe df.

The figure should clearly and effectively communicate the information in the data, and should be visually appealing. Please use Plotly's features such as annotations, color scales, and subplots as appropriate to enhance the figure's readability and impact.

Use the following format:

Question: "Question here"
Code: "Code to run here"

### Input Summary
{input_summary}
###


Question: {question}
Code:"""


@log_input_output(log_input=False, log_output=True)
def get_plot_code(input_context: str, question: str, openai_api_key: str) -> str:
    prompt = plotter_prompt_template.format(
        input_summary=input_context, question=question
    )
    plot_code = complete_prompt(
        prompt=prompt,
        stop="\nfig.show()",
        max_tokens=2_000,
        openai_api_key=openai_api_key,
    )
    return plot_code.completion
