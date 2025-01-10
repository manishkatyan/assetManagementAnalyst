from dataclasses import dataclass
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json

@dataclass
class MutualFund:
    name: str
    description: str
    key_attributes: Dict[str, str]

class LLMFundMatcher:
    def __init__(self, openai_api_key: str):
        self.funds = self._create_sample_funds()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=openai_api_key
        )

    def _create_sample_funds(self) -> List[MutualFund]:
        return [
            MutualFund(
                name="Global Equity Growth Fund",
                description="Active global equity strategy focusing on high-quality growth companies with strong market positions and sustainable competitive advantages. Designed for sophisticated investors seeking long-term capital appreciation.",
                key_attributes={
                    "Investment Style": "Active management with quality growth focus",
                    "Min Investment": "$250,000",
                    "Management Fee": "0.75% annually",
                    "Target Client": "High-net-worth individuals and institutions",
                    "AUM Range": "$10B - $20B"
                }
            ),
            MutualFund(
                name="Core Fixed Income Fund",
                description="Conservative fixed income strategy investing in investment-grade securities. Focuses on capital preservation while generating steady income through diversified bond portfolio.",
                key_attributes={
                    "Investment Style": "Core fixed income with blend approach",
                    "Min Investment": "$100,000",
                    "Management Fee": "0.45% annually",
                    "Target Client": "Conservative investors seeking income",
                    "AUM Range": "$20B - $30B"
                }
            ),
            MutualFund(
                name="ESG Leaders Fund",
                description="Sustainable equity strategy focusing on companies with strong environmental, social, and governance practices. Targets long-term growth through responsible investing.",
                key_attributes={
                    "Investment Style": "Active ESG-focused management",
                    "Min Investment": "$500,000",
                    "Management Fee": "0.85% annually",
                    "Target Client": "Institutional investors with ESG mandate",
                    "AUM Range": "$5B - $10B"
                }
            ),
            MutualFund(
                name="Multi-Asset Income Fund",
                description="Diversified multi-asset strategy focusing on income generation through various asset classes including equities, fixed income, and alternatives.",
                key_attributes={
                    "Investment Style": "Multi-asset income focused",
                    "Min Investment": "$150,000",
                    "Management Fee": "0.65% annually",
                    "Target Client": "Income-seeking high-net-worth individuals",
                    "AUM Range": "$10B - $15B"
                }
            ),
            MutualFund(
                name="Small Cap Value Fund",
                description="Active small-cap value strategy focusing on undervalued companies with strong fundamentals and potential catalysts for value realization.",
                key_attributes={
                    "Investment Style": "Active small-cap value",
                    "Min Investment": "$200,000",
                    "Management Fee": "0.95% annually",
                    "Target Client": "Long-term investors comfortable with volatility",
                    "AUM Range": "$5B - $10B"
                }
            )
        ]

    def analyze_matches(self, ria_data: dict) -> List[Dict]:
        """Use LLM to analyze and match RIA with mutual funds."""
        
        template = """You are an expert investment consultant tasked with matching an RIA to suitable mutual funds.

        RIA Information:
        {ria_data}

        Available Mutual Funds:
        {funds_data}

        Analyze the compatibility between the RIA and each fund based on:
        1. AUM Compatibility (size appropriateness)
        2. Fee Structure Alignment
        3. Client Type Match
        4. Investment Philosophy Alignment
        5. Operational Fit

        For each fund, provide:
        1. A match score (1-5, where 5 is best)
        2. Detailed rationale for the score
        3. Key strengths of the match
        4. Potential concerns

        Return the analysis in the following JSON format, ordered by highest to lowest score:
        {{
            "matches": [
                {{
                    "fund_name": "string",
                    "score": float,
                    "rationale": "string",
                    "strengths": ["string"],
                    "concerns": ["string"]
                }}
            ]
        }}

        Focus on practical business considerations and strategic fit.
        Ensure scores reflect true compatibility based on all available information.
        Consider both quantitative factors (AUM, fees) and qualitative aspects (investment philosophy, client focus)."""

        # Prepare fund data for prompt
        funds_data = []
        for fund in self.funds:
            funds_data.append(f"""
            Fund: {fund.name}
            Description: {fund.description}
            Attributes: {json.dumps(fund.key_attributes, indent=2)}
            """)

        # Create prompt
        prompt = ChatPromptTemplate.from_template(template)

        # Get LLM analysis
        chain = prompt | self.llm
        result = chain.invoke({
            "ria_data": json.dumps(ria_data, indent=2),
            "funds_data": "\n".join(funds_data)
        })

        # Parse LLM response
        try:
            # Clean the response content
            content = result.content
            # Remove markdown code block indicators if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()

            response_dict = json.loads(content)
            return response_dict['matches']
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {result.content}")
            return []

    def format_results_for_display(self, matches: List[Dict]) -> str:
        """Format the matching results for display."""
        output = []
        for match in matches:
            output.append(f"""
### {match['fund_name']} (Score: {match['score']}/5)

**Rationale:**
{match['rationale']}

**Key Strengths:**
{"".join([f'- {s}\n' for s in match['strengths']])}

**Potential Concerns:**
{"".join([f'- {c}\n' for c in match['concerns']])}
            """)
        return "\n".join(output)