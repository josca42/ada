# flake8: noqa E501
from dash import html, dcc, Input, Output, State
import base64
from dashboard.app import app
import dash_bootstrap_components as dbc
import tempfile
import os
from ada.config import config
from ada.agents.data import Files
import uuid
import pickle


def main_wrapper(element, sidebar_context):
    return html.Div(
        [
            sidebar(sidebar_context),
            html.Div(
                [
                    navigation(),
                    html.Div(
                        element,
                        className="container-fluid flex-grow-1 d-flex flex-column",
                    ),
                ],
                id="content-wrapper",
                className="d-flex flex-column",
            ),
        ],
        id="wrapper",
    )


def sidebar(sidebar_context):
    return html.Ul(
        [
            html.H1("", className="h3"),
            *(
                [
                    sidebar_item(elem["title"], elem["icon"], elem["href"])
                    for elem in sidebar_context
                ]
            ),
            html.Hr(className="sidebar-divider d-none d-md-block"),
            html.Div(
                html.Button(className="rounded-circle border-0", id="sidebarToggle"),
                className="text-center d-none d-md-inline",
            ),
        ],
        className="navbar-nav bg-gradient-primary sidebar sidebar-dark accordion",
    )


def sidebar_item(title, icon, href, active=False):
    class_name = "nav-item" + (" active" if active else "")
    return html.Li(
        dcc.Link(
            [html.I(className=icon), html.Span(title)],
            className="nav-link",
            href=href,
        ),
        className=class_name,
    )


def upload_data_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader("Upload data to be analysed"),
            dbc.ModalBody(
                [
                    dcc.Upload(
                        id="upload-data-file",
                        children=html.Div(
                            ["Drag and Drop or ", html.A("Select Files")]
                        ),
                        style={
                            "width": "100%",
                            "height": "60px",
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "margin": "10px",
                        },
                    ),
                    html.Div(id="data-uploaded"),
                ],
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Close",
                        id="modal-close-settings",
                        className="ml-auto",
                    ),
                ],
            ),
        ],
        id="upload-data-modal",
        is_open=False,  # True, False
        size="lg",  # "sm", "lg", "xl"
        backdrop="static",
    )


def navigation():
    return html.Nav(
        [
            html.Div(
                dbc.Button(
                    "Upload data",
                    color="primary",
                    id="upload-data-button",
                    size="md",
                    outline=True,
                ),
                className="navbar-nav me-auto",
            ),
            upload_data_modal(),
            html.Div(
                dcc.Input(
                    placeholder="Insert openai api key",
                    id="openai-api-key-input",
                    debounce=True,
                    type="text",
                    value="",
                    className="form-control form-control-user",
                ),
                className="navbar-nav ml-auto",
                style={"marginRight": "1rem"},
            ),
        ],
        className="navbar navbar-expand navbar-light bg-white topbar mb-4 static-top shadow",
    )


@app.callback(
    [Output("openai-api-key-input", "value"), Output("openai-api-key", "data")],
    Input("openai-api-key-input", "value"),
)
def update_openai_api_key(openai_api_key):
    if openai_api_key:
        openai_key_hide = "................"
    else:
        openai_key_hide = ""
    return openai_key_hide, openai_api_key


@app.callback(
    Output("upload-data-modal", "is_open"),
    [
        Input("upload-data-button", "n_clicks"),
        Input("modal-close-settings", "n_clicks"),
    ],
    [
        State("upload-data-modal", "is_open"),
    ],
)
def update_upload_data_modal(button_upload, button_close, is_open):
    if button_upload or button_close:
        return not is_open
    return is_open


@app.callback(
    [Output("data-uploaded", "children"), Output("file-dir", "data")],
    Input("upload-data-file", "contents"),
    State("upload-data-file", "filename"),
    prevent_initial_call=True,
)
def save_uploaded_file_to_disk(content, filename):
    if content is None:
        return html.H5("No file uploaded", style={"textAlign": "center"}), None

    try:
        upload_dir = config["DATA_DIR"] / "uploaded_data" / str(uuid.uuid4())
        upload_dir.mkdir()
        data = content.encode("utf8").split(b";base64,")[1]
        with open(upload_dir / filename, "wb") as fp:
            fp.write(base64.decodebytes(data))

        data_agent = Files(files_dir_path=upload_dir)
        data_agent.save(upload_dir)

    except Exception as e:
        print(e)
        return html.H5(f"There was an error processing {filename}")

    return html.H5(f"{filename} has been uploaded", style={"textAlign": "center"}), str(
        upload_dir
    )
