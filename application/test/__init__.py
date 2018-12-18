import logging
import connexion
from flask_testing import TestCase
from application.encoder import JSONEncoder
from application import __main__
from application.util import helper
from jinja2 import ChoiceLoader
from jinja2 import FileSystemLoader
import os


class BaseTestCase(TestCase):

    def create_app(self):
        logging.getLogger('connexion.operation').setLevel('ERROR')
        app = connexion.App(__name__, specification_dir="../swagger/")
        app.app.json_encoder = JSONEncoder
        app.add_api('swagger.yaml')
        my_loader = ChoiceLoader([
            app.app.jinja_loader,
            FileSystemLoader([os.path.join(helper.APP_PATH, "templates")]),
        ])
        app.app.jinja_loader = my_loader

        @app.route("/prioritizer/chart/c/<chart_key>")
        def show_chart(chart_key):
            return __main__.show_chart(chart_key)

        return app.app
