#!/usr/bin/env python3

import connexion
from application import encoder
from application.controllers import recommendation_controller
from flask import render_template
from flask import abort
from application.services import keywordextractor
from collections import Counter
import urllib.request
from application.util import helper
#from apscheduler.schedulers.background import BackgroundScheduler


external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
helper.substitute_host_in_swagger("localhost", external_ip)
app = connexion.App(__name__, specification_dir='./swagger/')


def main():
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'OpenReq Requirement Prioritization Recommendation Service'})
    helper.init_config()
    helper.substitute_host_in_swagger(external_ip, "localhost")
    #scheduler = BackgroundScheduler()
    #scheduler.add_job(func=cronjob_update_profiles, trigger="interval", seconds=3)
    #scheduler.start()
    app.run(port=helper.app_port())


@app.route("/prioritizer/chart/c/<chart_key>")
def show_chart(chart_key):
    if chart_key not in recommendation_controller.CHART_REQUESTs:
        abort(404)

    chart_request = recommendation_controller.CHART_REQUESTs[chart_key]
    keyword_extractor = keywordextractor.KeywordExtractor()

    resolved_requirements = recommendation_controller.ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[chart_request.unique_key()]
    #new_requirements = recommendation_controller.ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER[chart_request.unique_key()]
    _ = keyword_extractor.extract_keywords(resolved_requirements, enable_pos_tagging=False,
                                           enable_lemmatization=False, lang="en")
    #_ = keyword_extractor.extract_keywords(new_requirements, enable_pos_tagging=False,
    #                                       enable_lemmatization=False, lang="en")

    # only count those keywords that occur in NEW requirements as well as are part of the user profile (i.e., keywords of past/resolved requirements)
    #keyword_frequencies = Counter(filter(lambda t: t in user_extracted_keywords, [t for r in new_requirements for t in r.summary_tokens]))

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

