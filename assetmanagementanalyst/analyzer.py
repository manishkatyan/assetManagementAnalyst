from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import logging

class ContentAnalysis(BaseModel):
    investment_themes: List[str] = Field(description="List of investment themes mentioned in the content")
    key_points: List[str] = Field(description="Main points from the content")
    summary: str = Field(description="Brief summary of the content")

class ContentAnalyzer:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=openai_api_key
        )
        self.output_parser = PydanticOutputParser(pydantic_object=ContentAnalysis)

    def analyze_content(self, content: str) -> ContentAnalysis:
        template = """You are a financial analyst expert. Analyze the given content and extract information in the following format:

{format_instructions}

Content to analyze: {content}

Focus on financial and investment-related information.
"""
        
        prompt = ChatPromptTemplate.from_template(template)

        chain = prompt | self.llm | self.output_parser

        try:
            result = chain.invoke({
                "content": content,
                "format_instructions": self.output_parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logging.error(f"Error analyzing content: {str(e)}")
            return ContentAnalysis(
                investment_themes=["Error analyzing themes"],
                key_points=["Error analyzing content"],
                summary="Analysis failed due to formatting error. Please try again."
            )