#!/usr/bin/env python3

import connexion
from application import encoder
from application.controllers import recommendation_controller
from flask import render_template
from flask import redirect
from flask import abort
from application.services import keywordextractor
from collections import Counter
import urllib.request
from application.util import helper
from logging.handlers import TimedRotatingFileHandler
import logging
import os


external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
helper.substitute_host_in_swagger("localhost", external_ip)
app = connexion.App(__name__, specification_dir='./swagger/')


def main():
    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    handler = TimedRotatingFileHandler(os.path.join(helper.LOG_PATH, "activity.log"), when='midnight', interval=1)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    app.app.logger.addHandler(handler)
    app.app.logger.setLevel(logging.DEBUG)
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'OpenReq Requirement Prioritization Recommendation Service'})
    helper.init_config()
    helper.substitute_host_in_swagger(external_ip, "localhost")
    app.run(port=helper.app_port())


@app.route("/prioritizer/view/i/<issue_id>/k/<unique_key>")
def view_issue(issue_id, unique_key):
    assert(issue_id.isdigit())
    agent_id, assignee, components, products, keywords = unique_key.split("_#_")
    components = components.replace("set()", "")
    products = products.replace("set()", "")
    keywords = keywords.replace("set()", "")
    components = list(filter(lambda c: len(c) > 1, map(lambda c: c.strip(), components[1:-1].replace("'", "").split(","))))
    products = list(filter(lambda c: len(c) > 1, map(lambda c: c.strip(), products[1:-1].replace("'", "").split(","))))
    keywords = list(filter(lambda c: len(c) > 1, map(lambda c: c.strip(), keywords[1:-1].replace("'", "").split(","))))
    request = {
        'agent_id': agent_id,
        'assignee': assignee,
        'components': components,
        'products': products,
        'keywords': keywords
    }
    version = recommendation_controller.db.get("VERSION_{}".format(agent_id))
    app.app.logger.info("View Issue: version={}, id={}, request=({}), unique_key={}".format(version, issue_id,
                                                                                            request, unique_key))
    return redirect("https://bugs.eclipse.org/bugs/show_bug.cgi?id={}".format(issue_id), code=303)


@app.route("/prioritizer/chart/c/<chart_key>")
def show_chart(chart_key):
    if chart_key not in recommendation_controller.CHART_REQUESTs:
        abort(404)

    chart_request = recommendation_controller.CHART_REQUESTs[chart_key]
    keyword_extractor = keywordextractor.KeywordExtractor()

    resolved_requirements = recommendation_controller.ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[chart_request.unique_key()]
    keyword_extractor.extract_keywords(resolved_requirements, lang="en")

    # consider keywords of past requirements
    keyword_frequencies = Counter([t for r in resolved_requirements for t in r.summary_tokens])
    return render_template(
        "chart.html",
        assignee_email_address=chart_request.assignee,
        keyword_frequencies=keyword_frequencies)


def cronjob_update_profiles():
    print("Triggered cronjob...")
    # TODO: implement cronjob that rebuilds the profiles with higher limit!


if __name__ == '__main__':
    main()

