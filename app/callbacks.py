from app.kakao_env import run_class, run_free, run_one_shot_class
from app import db
from firebase_admin import firestore
from utils import prune_string, readable

import multiprocessing
import requests
from datetime import datetime


def intro_callback_request(callback_url, input, user):
    try:
        output = "Hello I'm Lukas, who will teach you from now on.\nIf you want to start a class please tell me anytime, like \"Let's start a class\".🧑‍🏫\n\nAnyway, let's have a free conversation first. How do you feel today?😄"

        call_back = requests.post(callback_url, json={
            "version": "2.0", "template": {"outputs": [{
                "simpleText": {"text": output}
            }]}})

        user_ref = db.collection('users').document(user.id)

        user_ref.collection('chat_history').add({
            'content': output,
            'whom': 'Tutor',
            'mode': 'free',
            'course': None,
            'chapter': None,
            'timestamp': datetime.now()
        })

        user_ref.update({'curr_mode': 'free'})

        print(call_back.status_code, call_back.json())

    except Exception as e:
        print('[[INTRO ERROR]]', e)


def select_callback_request(callback_url, input, user):
    try:
        user_ref = db.collection('users').document(user.id)

        if "[Course" in input:
            user_ref.update({
                'curr_course': input[7]
            })

            chapters = db.collection('class_topics').document(
                'course_'+input[7]).collection('chapters').get()

            chapters_list, quik_replies = [
                "What chapter would you like to take?\n"], []
            for c in chapters:
                n = c.id[8]
                title = c.to_dict().get("title")
                chapters_list.append(f'{n}: {title}')
                quik_replies.append({
                    "messageText": f'[Chapter{n}] {title}',
                    "action": "message",
                    "label": n
                })
            chapters_desc = '\n'.join(chapters_list)

            call_back = requests.post(
                callback_url,
                json={
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": chapters_desc
                                }
                            },
                        ],
                        "quickReplies": quik_replies
                    }
                }
            )

        elif "[Chapter" in input:
            chapter = input[8]
            user_ref.update({
                'curr_mode': 'class',
                'curr_chapter': chapter
            })

            chapter = db.collection('class_topics').document(
                'course_'+user.get('curr_course')).collection('chapters').document(
                'chapter_'+input[8]).get().to_dict()

            first_class_msg = "(System: Now that the class has started, introduce the class topic first.)"

            _, assist_output, tutor_output, _, _, new_cost = run_one_shot_class(
                class_topic=chapter.get('topic'),
                input=first_class_msg,
                turns=0,
                user_memory=None,
                prev_word_set=[]
            )

            costs = user.get("costs")
            costs.append(new_cost)
            user_ref.update({
                "class_turn_cnt": user.get('class_turn_cnt') + 1,
                "costs": costs
            })

            user_ref.collection('class_chat_history').add({
                'content': first_class_msg,
                'whom': 'User',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': chapter,
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            user_ref.collection('class_chat_history').add({
                'content': assist_output,
                'whom': 'Thought',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': chapter,
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            user_ref.collection('class_chat_history').add({
                'content': tutor_output,
                'whom': 'Tutor',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': chapter,
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            tutor_output = readable(tutor_output)
            tutor_output = prune_string(tutor_output)

            call_back = requests.post(callback_url, json={
                "version": "2.0", "template": {"outputs": [
                    {
                        "basicCard": {
                            "title": "",
                            "description": tutor_output,
                            "thumbnail": {
                                "imageUrl": chapter.get('image_url')
                            }
                        }
                    }
                ]}})

        else:
            call_back = requests.post(
                callback_url,
                json={
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": "보기의 버튼을 눌러 응답해주세요 :)\nWhat course would you like to take?"
                                }
                            },
                        ],
                        "quickReplies": [
                            {
                                "messageText": "[Course1] Daily",
                                "action": "message",
                                "label": "Daily"
                            },
                            {
                                "messageText": "[Course2] Business",
                                "action": "message",
                                "label": "Business"
                            }
                        ]
                    }
                }
            )

        print(call_back.status_code, call_back.json())

    except Exception as e:
        print('[[SELECT ERROR]]', e)


def free_callback_request(callback_url, input, user):
    try:
        user_ref = db.collection('users').document(user.id)

        post_content = db.collection('posts').where(
            'id', '==', '1').get()[0].get('content')

        free_chat_memory = user_ref.collection('chat_history').order_by(
            'timestamp', direction=firestore.Query.DESCENDING).limit(15).stream()

        user_memory = []
        for i in list(free_chat_memory)[::-1][:-1]:
            user_memory.append(i.get('whom')+': '+i.get('content'))
        user_memory_string = '\n'.join(user_memory)

        output = run_free(
            post_content=post_content,
            input=input,
            user_memory=user_memory_string
        )

        # free -> class
        if 'START' in output:

            call_back = requests.post(
                callback_url,
                json={
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": "What course would you like to take?"
                                }
                            },
                        ],
                        "quickReplies": [
                            {
                                "messageText": "[Course1] Daily",
                                "action": "message",
                                "label": "Daily"
                            },
                            {
                                "messageText": "[Course2] Business",
                                "action": "message",
                                "label": "Business"
                            }
                        ]
                    }
                }
            )

            user_ref.update({
                'curr_mode': 'select'
            })

            user_ref.collection('chat_history').add({
                'content': "The class has progressed and is over. Go back to your normal conversation. Ouput 'START' whenever the user wants to start the class.",
                'whom': 'System',
                'mode': 'free',
                'course': None,
                'chapter': None,
                'timestamp': datetime.now()
            })

        else:
            user_ref.collection('chat_history').add({
                'content': output,
                'whom': 'Tutor',
                'mode': 'free',
                'course': None,
                'chapter': None,
                'timestamp': datetime.now()
            })

            call_back = requests.post(callback_url, json={
                "version": "2.0", "template": {"outputs": [{
                    "simpleText": {"text": readable(output)}
                }]}})

        print(call_back.status_code, call_back.json())
    except Exception as e:
        print('[[FREE ERROR]]', e)


def class_callback_request(callback_url, input, user):
    try:
        user_ref = db.collection('users').document(user.id)

        # get chapter info
        chapter = db.collection('class_topics').document(
            'course_'+str(user.get('curr_course'))).collection('chapters').document(
            'chapter_'+str(user.get('curr_chapter'))).get().to_dict()

        # get class_chat_history
        class_chat_memory = user_ref.collection('class_chat_history').where(
            'n_class', '==', user.get('n_class')).where(
            'whom', 'in', ['User', 'Tutor']).order_by(
            'timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        user_memory = []
        for i in list(class_chat_memory)[::-1][:-1]:
            user_memory.append([i.get('whom'), i.get('content')])

        # run class chain with timeout
        result = run_with_timeout(
            func=run_one_shot_class,
            timeout=55,
            class_topic=chapter.get('topic'),
            input=input,
            turns=user.get('class_turn_cnt'),
            user_memory=user_memory,
            prev_word_set=user.get('word_set')
        )

        if result is None:
            timeout_error_msg = "[시간 초과 오류] 다시 시도해주세요 :)"
            call_back = requests.post(callback_url, json={
                "version": "2.0", "template": {"outputs": [{
                    "simpleText": {"text": timeout_error_msg}
                }]}})

        else:
            checker_output, assist_output, tutor_output, updated_word_set, review_note, new_cost = result

            # add chat_history
            user_ref.collection('class_chat_history').add({
                'content': checker_output,
                'whom': 'Checker',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': user.get('curr_chapter'),
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            user_ref.collection('class_chat_history').add({
                'content': assist_output,
                'whom': 'Thought',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': user.get('curr_chapter'),
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            user_ref.collection('class_chat_history').add({
                'content': tutor_output,
                'whom': 'Tutor',
                'mode': 'class',
                'course': user.get('curr_course'),
                'chapter': user.get('curr_chapter'),
                'n_class': user.get('n_class'),
                'timestamp': datetime.now()
            })

            # user update
            costs = user.get('costs')
            costs[-1] += new_cost

            user_ref.update({
                "class_turn_cnt": user.get('class_turn_cnt') + 1,
                "word_set": updated_word_set,
                "costs": costs
            })
            if review_note:
                prev_review_note = user.get("review_note")
                prev_review_note.append(review_note)
                user_ref.update({"review_note": prev_review_note})

            tutor_output = readable(tutor_output)

            # class -> free
            if "goodbye~" in tutor_output.lower():

                word_cnt = user.get('word_cnt')
                word_cnt.append(len(updated_word_set))

                user_ref.update({
                    'curr_mode': 'free',
                    'curr_course': None,
                    'curr_chapter': None,
                    'class_turn_cnt': 0,
                    'word_cnt': word_cnt,
                    'n_class': user.get('n_class') + 1
                })

                tutor_output = prune_string(tutor_output)

                call_back = requests.post(callback_url, json={
                    "version": "2.0", "template": {"outputs": [
                        {
                            "basicCard": {
                                "title": 'Class End',
                                "description": tutor_output,
                                "thumbnail": {
                                    "imageUrl": chapter.get('image_url')
                                },
                                "buttons": [
                                    {
                                        "action": "webLink",
                                        "label": "Open Report",
                                        "webLinkUrl": f"https://lukas-tutor.herokuapp.com/report/{user.id}"
                                    }
                                ]
                            }
                        }
                    ]}})

            else:
                call_back = requests.post(callback_url, json={
                    "version": "2.0", "template": {"outputs": [{
                        "simpleText": {"text": tutor_output}
                    }]}})

            print(call_back.status_code, call_back.json())

    except Exception as e:
        print('[[CLASS ERROR]]', e)


def run_with_timeout(func, timeout, **kwargs):
    pool = multiprocessing.Pool(processes=1)
    result = pool.apply_async(func, args=(), kwds=kwargs)
    try:
        return result.get(timeout)
    except multiprocessing.TimeoutError:
        return None
