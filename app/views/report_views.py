from flask import Blueprint, render_template
import json

from app import db

bp = Blueprint('report', __name__, url_prefix='/report')


@bp.route('/<string:user_id>/')
def report(user_id):
    user = db.collection('users').where('id', '==', user_id).get()[0]
    word_cnt = user.get('word_cnt')

    display_word_cnt = []
    labels = []
    if len(word_cnt) > 10:
        display_word_cnt = word_cnt[-10:]
        labels = [n for n in range(len(word_cnt)-9, len(word_cnt)+1)]
    else:
        display_word_cnt = word_cnt + [0] * (10 - len(word_cnt))
        labels = [n for n in range(1, 11)]

    review_note_ = user.get('review_note')
    review_note = [n.split('|') for n in review_note_]

    return render_template('report.html', word_cnt=json.dumps(display_word_cnt), labels=json.dumps(labels), review_note=review_note)
