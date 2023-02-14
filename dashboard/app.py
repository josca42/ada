from dash import Dash
import dash_bootstrap_components as dbc

CSS = [
    dbc.themes.BOOTSTRAP,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css",
    "https://cdn.datatables.net/1.10.23/css/dataTables.bootstrap4.min.css",
]
JS = [
    "https://code.jquery.com/jquery-3.5.1.slim.min.js",
    "https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.bundle.min.js",
]
app = Dash(
    __name__,
    external_scripts=JS,
    external_stylesheets=CSS,
    suppress_callback_exceptions=True,
)
server = app.server
