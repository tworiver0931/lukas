from flask import Blueprint, request
from app import executor, db
from app.callbacks import intro_callback_request, select_callback_request, free_callback_request, class_callback_request

from datetime import datetime

bp = Blueprint('input', __name__, url_prefix='/')


@bp.route('/input', methods=["POST"])
def call():
    body = request.get_json()
    callback_url = body['userRequest']['callbackUrl']
    user_id = body['userRequest']['user']['id']
    input = body['userRequest']['utterance']

    user = db.collection('users').where('id', '==', user_id).get()

    # create new user
    if len(user) == 0:
        db.collection('users').document(user_id).set({
            'id': user_id,
            'curr_mode': 'intro',
            'curr_course': None,
            'curr_chapter': None,
            'class_turn_cnt': 0,
            'word_set': [],
            'word_cnt': [],
            'review_note': [],
            'n_class': 0,
            'costs': [],
            'timestamp': datetime.now()
        })
        user = db.collection('users').where('id', '==', user_id).get()[0]
    else:
        user = user[0]

    user_ref = db.collection('users').document(user.id)

    mode = user.get('curr_mode')

    # save student's input
    if mode == 'class':
        user_ref.collection('class_chat_history').add({
            'content': input,
            'whom': 'User',
            'mode': user.get('curr_mode'),
            'course': user.get('curr_course'),
            'chapter': user.get('curr_chapter'),
            'n_class': user.get('n_class'),
            'timestamp': datetime.now()
        })
    else:
        user_ref.collection('chat_history').add({
            'content': input,
            'whom': 'User',
            'mode': user.get('curr_mode'),
            'course': user.get('curr_course'),
            'chapter': user.get('curr_chapter'),
            'timestamp': datetime.now()
        })

    skill_response = {
        "version": "2.0",
        "useCallback": True,
    }

    if mode == 'intro':
        executor.submit(intro_callback_request, callback_url, input, user)
    elif mode == 'select':
        executor.submit(select_callback_request, callback_url, input, user)
    elif mode == 'free':
        executor.submit(free_callback_request, callback_url, input, user)
    elif mode == 'class':
        executor.submit(class_callback_request, callback_url, input, user)

    return skill_response
