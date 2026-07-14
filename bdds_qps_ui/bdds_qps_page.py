import os

from flask import send_from_directory
from main_app import app

from bluecat import route
from bluecat.gateway.decorators import page_exc_handler, require_permission


@route(app, "/bdds_qps_ui/page")
@page_exc_handler(default_message="Failed to load BDDS Performance Statistics workflow.")
@require_permission("bdds_qps_page")
def bdds_qps_ui_page():
    return send_from_directory(os.path.dirname(os.path.abspath(str(__file__))), "bddsQpsPage/index.html")
