from pathlib import Path

from groq import Groq

from config import (
    GROQ_API_KEY,
    LLM_MODEL,
)


class InformationExtractor:

    def __init__(self):

        self.client = Groq(
            api_key=GROQ_API_KEY,
        )

        self.prompt = Path(
            "prompts/extraction_prompt.txt"
        ).read_text(
            encoding="utf-8"
        )

    def extract(
        self,
        transcript: str,
    ) -> str:

        response = self.client.chat.completions.create(

            model=LLM_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": self.prompt,
                },
                {
                    "role": "user",
                    "content": transcript,
                },
            ],

            temperature=0,
        )

        return response.choices[0].message.content


information_extractor = InformationExtractor()