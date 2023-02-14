from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from dashboard.components import main_wrapper
from dashboard.app import app
from ada.main import data_analyst_action
from ada.agents.data import Files
import pandas as pd
import ast
import pickle


def layout(sidebar_context, debug=False):
    conversation = html.Div(
        html.Div(id="display-conversation"),
        style={
            "overflow-y": "auto",
            "display": "flex",
            "height": "calc(90vh - 132px)",
            "flex-direction": "column-reverse",
        },
    )
    controls = dbc.InputGroup(
        [
            dbc.Input(
                id="user-input", placeholder="Write to the chatbot...", type="text"
            ),
            dbc.Button("Submit", id="submit", style={"background-color": "#218aff"}),
        ]
    )
    chat_window = dbc.Container(
        [
            dcc.Store(id="store-conversation", data=[]),
            conversation,
            controls,
            dbc.Spinner(html.Div(id="loading-component")),
        ],
        fluid=False,
    )
    return main_wrapper(
        [chat_window],
        sidebar_context,
    )


def textbox(input, box="AI"):
    style = {
        "max-width": "100%",
        "width": "max-content",
        "padding": "5px 10px",
        "border-radius": 25,
        "margin-bottom": 20,
    }

    if box == "user":
        assert type(input) == type("text"), "User input must be a string."
        style["margin-left"] = "auto"
        style["margin-right"] = 0
        style["background-color"] = "#218aff"
        style["color"] = "white"
        return dbc.Card(
            input,
            style=style,
            body=True,
            inverse=True,
        )

    elif box == "AI":
        action, data = input["action"], input["data"]
        if action["tool"] == "Text":
            input = action["input"]
            style["margin-left"] = 0
            style["margin-right"] = "auto"
            style["background-color"] = "#d8d8d8"
            style["color"] = "black"
            return dbc.Card(input, style=style, body=True, inverse=False)
        elif action["tool"] == "Plot":
            df = pd.read_json(data["data"])
            code = data["code"]

            # Use ast to execute the code and extract the variable `fig`
            node = ast.parse(code)
            local_namespace = {"df": df}
            exec(compile(node, "<ast>", "exec"), local_namespace)
            fig = local_namespace.get("fig")

            return dcc.Graph(figure=fig, style=style)
        else:
            raise ValueError("Incorrect tool in `action`.")

    else:
        raise ValueError("Incorrect option for `box`.")


@app.callback(
    Output("display-conversation", "children"), [Input("store-conversation", "data")]
)
def update_display(chat_history):
    return [
        textbox(x, box="user") if i % 2 == 0 else textbox(x, box="AI")
        for i, x in enumerate(chat_history)
    ]


@app.callback(
    Output("user-input", "value"),
    [Input("submit", "n_clicks"), Input("user-input", "n_submit")],
)
def clear_input(n_clicks, n_submit):
    return ""


@app.callback(
    [Output("store-conversation", "data"), Output("loading-component", "children")],
    [Input("submit", "n_clicks"), Input("user-input", "n_submit")],
    [
        State("user-input", "value"),
        State("store-conversation", "data"),
        State("openai-api-key", "data"),
        State("file-dir", "data"),
    ],
)
def run_chatbot(n_clicks, n_submit, user_input, chat_history, openai_api_key, file_dir):
    if n_clicks == 0 and n_submit is None:
        return "", None

    if user_input is None or user_input == "":
        return chat_history, None

    data_agent = Files.load(file_dir)

    # First add the user input to the chat history
    chat_history.append(user_input)
    # Get Ada's response
    ada_action = data_analyst_action(
        user_input, data_agent=data_agent, openai_api_key=openai_api_key
    )
    chat_history.append(ada_action)

    return chat_history, None


if __name__ == "__main__":
    app.run_server(debug=False)
