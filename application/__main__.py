#!/usr/bin/env python3

import connexion
from application import encoder
from application.controllers import recommendation_controller
from flask import render_template
from flask import abort
from application.services import keywordextractor
from application.util import helper
from collections import Counter


app = connexion.App(__name__, specification_dir='./swagger/')


def main():
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'OpenReq Requirement Prioritization Recommendation Service'})
    app.run(port=helper.app_port())


@app.route("/prioritizer/chart/c/<chart_key>")
def show_chart(chart_key):
    if chart_key not in recommendation_controller.CHART_REQUESTs:
        abort(404)

    chart_request = recommendation_controller.CHART_REQUESTs[chart_key]
    keyword_extractor = keywordextractor.KeywordExtractor()

    resolved_requirements = recommendation_controller.ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[chart_request.unique_key()]
    new_requirements = recommendation_controller.ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER[chart_request.unique_key()]
    user_extracted_keywords = keyword_extractor.extract_keywords(resolved_requirements, enable_pos_tagging=False, enable_lemmatization=False, lang="en")
    _ = keyword_extractor.extract_keywords(new_requirements, enable_pos_tagging=False, enable_lemmatization=False, lang="en")

    # only count those keywords that occur in NEW requirements as well as are part of the user profile (i.e., keywords of past/resolved requirements)
    #keyword_frequencies = Counter(filter(lambda t: t in user_extracted_keywords, [t for r in new_requirements for t in r.summary_tokens]))

    # consider keywords of past requirements
    keyword_frequencies = Counter([t for r in resolved_requirements for t in r.summary_tokens])
    return render_template(
        "chart.html",
        assignee_email_address=chart_request.assignee,
        keyword_frequencies=dict(keyword_frequencies)
    )


def test_prioritization():
    print('Test Prioritization')
    recommendation_controller.perform_prioritization()


if __name__ == '__main__':
    main()
    #test_prioritization()

