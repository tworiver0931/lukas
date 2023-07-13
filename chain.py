from langchain import LLMChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from langchain.base_language import BaseLanguageModel

from utils import load_prompt


class PromptChain(LLMChain):

    @classmethod
    def from_llm(
        cls,
        system_prompt_path: str,
        human_prompt_path: str,
        llm: BaseLanguageModel,
        verbose: bool = True
    ) -> LLMChain:

        system_prompt = load_prompt(system_prompt_path)
        human_prompt = load_prompt(human_prompt_path)

        system_message_prompt = SystemMessagePromptTemplate(
            prompt=system_prompt)
        human_message_prompt = HumanMessagePromptTemplate(prompt=human_prompt)

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                system_message_prompt,
                human_message_prompt
            ]
        )

        return cls(prompt=chat_prompt, llm=llm, verbose=verbose)
