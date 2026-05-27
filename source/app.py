from flask import Flask
from flask_cors import CORS

from source.core.config.config import load_runtime_config

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/api/v1/*": {
            "origins": "*",
            "methods": "GET, POST, PUT, DELETE, OPTIONS",
            "headers": "Origin, Content-Type, Authorization, X-Setup-Key, charset=utf-8",
        }
    },
)
app.config["JSON_AS_ASCII"] = False

load_runtime_config()

from source.controller import ctrl_account, ctrl_auth, ctrl_catalog, ctrl_crud, ctrl_main, ctrl_reports, ctrl_setup, ctrl_templates  # noqa: E402,F401
