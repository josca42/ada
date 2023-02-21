from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from dashboard.components import main_wrapper
from dashboard.app import app, server
import pandas as pd
import ast
from ada import data_analyst
from dash import dcc, html, Input, Output
from dotenv import dotenv_values
import dash
from dashboard import db
from ada import data

data_dir = dotenv_values()["DATA_DIR"]
sidebar_context = {
    "/": {
        "title": "IMDB movies",
        "href": "/",
        "icon": "fa-regular fa-message",
        "data_dir": f"{data_dir}/imdb",
    },
}

app.layout = html.Div(
    [
        dcc.Location(id="urlNoRefresh"),
        dcc.Location(id="urlRefresh", refresh=True),
        html.Div(id="content"),
        dcc.Store(
            "openai-api-key",
            data="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",
            storage_type="session",
        ),
        dcc.Store(
            "app-state",
            data=sidebar_context,
            storage_type="session",
        ),
    ]
)


@app.callback(
    Output("content", "children"),
    Input("app-state", "data"),
)
def layout(sidebar_context):
    sidebar_context = [sidebar_item for path, sidebar_item in sidebar_context.items()]
    conversation = html.Div(
        html.Div(id="display-conversation"),
        style={
            "overflow-y": "auto",
            "display": "flex",
            "height": "calc(90vh - 132px)",
            "flex-direction": "column-reverse",
        },
    )
    recent_questions = db.crud_question.list_previous_questions()
    controls = dbc.InputGroup(
        [
            html.Datalist(
                id="list-suggested-inputs",
                children=[html.Option(value=question) for question in recent_questions],
            ),
            dbc.Input(
                id="user-input",
                placeholder="Write to the chatbot...",
                type="text",
                list="list-suggested-inputs",
            ),
            dbc.Button("Submit", id="submit", style={"background-color": "#218aff"}),
        ]
    )
    chat_window = dbc.Container(
        [
            dcc.Store(id="store-conversation", data={"/": []}),
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


@app.callback(
    Output("display-conversation", "children"),
    [Input("store-conversation", "data"), Input("urlNoRefresh", "pathname")],
)
def update_conversation(chats, pathname):
    chat_history = chats[pathname]
    return [
        textbox(x, box="AI") if i % 2 == 0 else textbox(x, box="user")
        for i, x in enumerate(chat_history)
    ]


@app.callback(
    [Output("store-conversation", "data"), Output("loading-component", "children")],
    [Input("submit", "n_clicks"), Input("user-input", "n_submit")],
    [
        State("user-input", "value"),
        State("store-conversation", "data"),
        State("openai-api-key", "data"),
        State("app-state", "data"),
        Input("urlNoRefresh", "pathname"),
    ],
)
def answer_question(
    n_clicks, n_submit, user_input, chats, openai_api_key, app_state, pathname
):
    callback_trigger = dash.callback_context.triggered[0]["prop_id"]

    # Get data fetcher and chat history
    if pathname not in chats:
        chats[pathname] = []
    chat_history = chats[pathname]
    data_fetcher_fp = app_state[pathname]["data_dir"] + "/data_fetcher.pkl"
    data_fetcher = data.Files.load(fp=data_fetcher_fp)

    # If the user has not entered any input, return dataset introduction
    if n_clicks is None and n_submit is None and chat_history == []:
        introduction = (
            f"Ask questions about the following table: {data_fetcher.tables_info}"
        )
        response = dict(
            action=dict(tool="Text", input=introduction), action_data=dict()
        )
        chat_history.append(response)
    elif callback_trigger == "urlNoRefresh.pathname":
        pass
    else:
        # If the user submitted an empty message return status quo
        if user_input is None or user_input == "":
            return chat_history, None

        # Get data analyst response
        response = data_analyst(
            user_input,
            openai_api_key=openai_api_key,
            data_fetcher=data_fetcher,
        )
        # Add the input and the response to the chat history
        chat_history.append(user_input)
        chat_history.append(response)

        # Save the user input to the database
        db.crud_question.create(db.Question(text=user_input))

    chats[pathname] = chat_history
    return chats, None


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
        action, action_data = input["action"], input["action_data"]
        if action["tool"] == "Text":
            input = action["input"]
            style["margin-left"] = 0
            style["margin-right"] = "auto"
            style["background-color"] = "#d8d8d8"
            style["color"] = "black"
            return dbc.Card(input, style=style, body=True, inverse=False)
        elif action["tool"] == "Plot":
            df = pd.read_json(action_data["data"])
            code = action_data["code"]

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


if __name__ == "__main__":
    # upload_dir = "/Users/josca/projects/ada/data/imdb"
    # data_agent = data.Files(data_dir=upload_dir)
    # data_agent.save(upload_dir + "/data_fetcher.pkl")

    app.run_server(port=8050, debug=True)
