from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from chain import PromptChain

import requests

import re
import config
import os

os.environ["OPENAI_API_KEY"] = config.openai_api_key


def load_class_chains(verbose=False):

    assistant_llm = ChatOpenAI(
        model='gpt-4',
        temperature=1
    )

    tutor_llm = ChatOpenAI(
        model='gpt-4',
        temperature=1,
        max_tokens=250
    )

    assistant = PromptChain.from_llm(
        system_prompt_path="prompts/tutor/thought/system.yaml",
        human_prompt_path="prompts/tutor/thought/human.yaml",
        llm=assistant_llm,
        verbose=verbose
    )

    tutor = PromptChain.from_llm(
        system_prompt_path="prompts/tutor/response/system.yaml",
        human_prompt_path="prompts/tutor/response/human.yaml",
        llm=tutor_llm,
        verbose=verbose
    )

    return {
        'assistant': assistant,
        'tutor': tutor
    }


def load_free_chains(verbose=False):

    llm = ChatOpenAI(
        model='gpt-3.5-turbo',
        temperature=1,
        max_tokens=150
    )

    tutor = PromptChain.from_llm(
        system_prompt_path="prompts/lukas/system_prompt.yaml",
        human_prompt_path="prompts/lukas/human_prompt.yaml",
        llm=llm,
        verbose=verbose
    )

    return {
        'tutor': tutor,
    }


def checker(input, api_url):
    if input == "":
        checker_output = "No user input yet."
    else:
        checker_output = requests.get(
            api_url, params={'input': input})
        checker_output = checker_output.json().get('corrected')
        checker_output_ = re.sub("[^A-Za-z0-9]", "", checker_output).lower()
        input_ = re.sub("[^A-Za-z0-9]", "", input).lower()

        if checker_output_ == input_:
            checker_output = 'correct'

    return checker_output


def evaluate(prev_word_set, input, checker_output):
    prev_word_set = set(prev_word_set)
    words = re.findall(r'\w+', input)
    words = set([word.lower() for word in words])
    updated_word_set = list(prev_word_set.union(words))

    if checker_output != 'correct':
        review_note = input+'|'+checker_output
    else:
        review_note = None

    return updated_word_set, review_note


def run_class(class_topic, input, turns, user_memory, prev_word_set):
    cost = 0
    models = load_class_chains(True)

    checker_output = checker(
        input=input,
        api_url=config.gramformer_url)

    updated_word_set, review_note = evaluate(
        prev_word_set, input, checker_output)

    if user_memory:
        history = []
        for m in user_memory:
            if m[0] == 'User' or m[0] == 'Tutor':
                history.append(m[0] + ": " + m[1])
        history = "\n".join(history)
    else:
        history = ""

    if turns >= 10:
        input += "\n(System: It's time to end the class.)"

    with get_openai_callback() as cb:
        assist_output = models['assistant'].run(
            input=input,
            checker_output=checker_output,
            class_topic=class_topic,
            history=history
        )
        cost += cb.total_cost

    if "Tutor:" in assist_output:
        assist_output = assist_output.split("Tutor:")[0].strip()

    with get_openai_callback() as cb:
        tutor_output = models['tutor'].run(
            input=input,
            class_topic=class_topic,
            thought=assist_output,
            history=history
        )
        cost += cb.total_cost

    if 'User:' in tutor_output:
        tutor_output = tutor_output.split('User:')[0].strip()

    # print outputs
    print('-'*90)
    print('[[Checker]]')
    print(checker_output+'\n')
    print('[[Thought]]')
    print(assist_output+'\n')
    print('[[Tutor]]')
    print(tutor_output+'\n')
    print('-'*90)

    return checker_output, assist_output, tutor_output, updated_word_set, review_note, cost


def run_one_shot_class(class_topic, input, turns, user_memory, prev_word_set):
    cost = 0
    tutor = PromptChain.from_llm(
        system_prompt_path="prompts/one_shot/system.yaml",
        human_prompt_path="prompts/one_shot/human.yaml",
        llm=ChatOpenAI(model='gpt-4', temperature=1),
        verbose=True
    )

    checker_output = checker(
        input=input,
        api_url=config.gramformer_url)

    updated_word_set, review_note = evaluate(
        prev_word_set, input, checker_output)

    if user_memory:
        history = []
        for m in user_memory:
            if m[0] == 'User' or m[0] == 'Tutor':
                history.append(m[0] + ": " + m[1])
        history = "\n".join(history)
    else:
        history = ""

    if turns >= 10:
        input += "\n(System: It's time to end the class.)"

    with get_openai_callback() as cb:
        tutor_output = tutor.run(
            input=input,
            class_topic=class_topic,
            checker_output=checker_output,
            history=history
        )
        cost += cb.total_cost

    print('-'*90)
    print('[[OUTPUT]]')
    print(tutor_output+'\n')

    thought, response = tutor_output.replace(
        'Thought: ', '').replace('Response: ', '|').split('|')
    thought, response = thought.strip(), response.strip()

    # print outputs
    print('[[Checker]]')
    print(checker_output+'\n')
    print('[[Thought]]')
    print(thought+'\n')
    print('[[Tutor]]')
    print(response+'\n')
    print('-'*90)

    return checker_output, thought, response, updated_word_set, review_note, cost


def run_free(post_content, input, user_memory):
    models = load_free_chains(True)

    tutor_output = models['tutor'].run(
        input=input,
        day=post_content,
        history=user_memory
    )

    if 'User:' in tutor_output:
        tutor_output = tutor_output.split('User:')[0].strip()

    return tutor_output
