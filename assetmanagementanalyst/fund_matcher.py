from dataclasses import dataclass
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json
import logging

# Get logger instance
logger = logging.getLogger(__name__)

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
        """Use LLM to analyze and match RIA with mutual funds.
        
        Args:
            ria_data (dict): Dictionary containing RIA information including:
                - meeting_notes (str, optional): Notes from client meetings
                - website_analyses (list): List of website analysis results
                - aum_summary (str): Summary of AUM information
                - fees_summary (str): Summary of fee structures
        
        Returns:
            List[Dict]: List of fund matches with scores and rationales
        """
        
        template = """You are an expert investment consultant tasked with matching an RIA to suitable mutual funds.

        CRITICAL INFORMATION - Meeting Notes:
        {meeting_notes}

        Additional RIA Information:
        Website Analysis Summary:
        {website_analyses}

        ADV Summary:
        {adv_data}

        Available Mutual Funds:
        {funds_data}

        MATCHING INSTRUCTIONS:
        1. First, identify any specific preferences or requirements from meeting notes:
        - Investment preferences or restrictions
        - Mentioned fund types or strategies
        - Key personnel relationships
        - Client-specific needs
        - Risk tolerance indicators
        - Fee sensitivity

        2. Then analyze fund compatibility in this priority order:
        a) Direct alignment with meeting notes preferences (highest weight)
        b) Investment strategy fit with stated preferences
        c) AUM and minimum investment compatibility
        d) Fee structure alignment
        e) Target client type match
        f) Investment philosophy alignment
        g) Operational considerations

        For each fund, provide:
        1. Match score (1-5, where 5 is best)
        - Score of 5: Perfect alignment with meeting notes and other criteria
        - Score of 4: Strong alignment with most key preferences
        - Score of 3: Good general fit but some misalignment
        - Score of 2: Multiple areas of concern
        - Score of 1: Significant misalignment
        2. Detailed rationale (explicitly reference meeting notes where relevant)
        3. Key strengths (prioritize alignment with meeting notes)
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

        IMPORTANT GUIDELINES:
        - Meeting notes represent the most current and direct client input - prioritize this information
        - If specific funds or strategies were mentioned positively or negatively in meetings, these should heavily influence scores
        - Consider both explicit preferences and implicit needs from meeting discussions
        - Use website and ADV data as supporting information only
        - If no meeting notes are provided, base analysis on website and ADV data"""

        # Prepare fund data for prompt
        funds_data = []
        for fund in self.funds:
            funds_data.append(f"""
            Fund: {fund.name}
            Description: {fund.description}
            Attributes: {json.dumps(fund.key_attributes, indent=2)}
            """)

        # Format meeting notes with clear indication if none provided
        meeting_notes = ria_data.get("meeting_notes")
        formatted_meeting_notes = (
            "No meeting notes provided - analysis based on website and ADV data only"
            if not meeting_notes
            else f"Meeting Notes:\n{meeting_notes}"
        )

        # Create prompt
        prompt = ChatPromptTemplate.from_template(template)

        # Get LLM analysis
        chain = prompt | self.llm
        result = chain.invoke({
            "meeting_notes": formatted_meeting_notes,
            "website_analyses": json.dumps([{
                "url": analysis["url"],
                "investment_themes": analysis["investment_themes"],
                "key_points": analysis["key_points"],
                "summary": analysis["summary"]
            } for analysis in ria_data["website_analyses"]], indent=2),
            "adv_data": json.dumps({
                "aum_summary": ria_data.get("aum_summary"),
                "fees_summary": ria_data.get("fees_summary")
            }, indent=2),
            "funds_data": "\n".join(funds_data)
        })

        # Parse LLM response
        try:
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
            logger.error(f"Error parsing LLM response: {str(e)}")
            logger.error(f"Raw response: {result.content}")
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