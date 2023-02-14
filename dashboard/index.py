import re
from dash import dcc, html, Input, Output
from dashboard import chat
from dashboard.app import app, server  # noqa: F401


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
            "file-dir",
            data="/Users/josca/projects/ada/data/uploaded_data/d3a3ddc1-0376-4c67-b6e3-a73eae937352",
            storage_type="session",
        ),
    ]
)
sidebar_context = [
    {"title": "New chat", "href": "/new", "icon": "fa-solid fa-plus"},
    {"title": "Chat 1", "href": "/", "icon": "fa-regular fa-message"},
]


@app.callback(Output("content", "children"), [Input("urlNoRefresh", "pathname")])
def route(pathname):
    if pathname == "/":
        return chat.layout(sidebar_context)
    elif pathname == "/new":
        return chat.layout(sidebar_context)

    return chat.layout(sidebar_context)


if __name__ == "__main__":
    app.run_server(port=8050, debug=True)
