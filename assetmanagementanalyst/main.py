import streamlit as st
from dotenv import load_dotenv
import os
from assetmanagementanalyst.scraper import WebsiteScraper
from assetmanagementanalyst.analyzer import ContentAnalyzer
from assetmanagementanalyst.adv_analyzer import ADVAnalyzer
from assetmanagementanalyst.fund_matcher import LLMFundMatcher
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_openai_api_key() -> str:
    """Get OpenAI API key from .env locally or secrets in Streamlit Cloud."""
    # Local development: Get from .env
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        return api_key
    
    # Streamlit Cloud: Get from secrets
    try:
        return st.secrets['OPENAI_API_KEY']
    except:
        st.error("""
        OpenAI API key not found! Please set it up:
        
        Local Development:
        - Add OPENAI_API_KEY to your .env file
        
        Streamlit Cloud:
        - Add OPENAI_API_KEY in your app secrets
        """)
        st.stop()

def init_session_state():
    if 'analyses' not in st.session_state:
        st.session_state.analyses = {}
    if 'adv_analyses' not in st.session_state:
        st.session_state.adv_analyses = {}
    if 'fund_matches' not in st.session_state:
        st.session_state.fund_matches = {}
    if 'meeting_notes' not in st.session_state:
        st.session_state.meeting_notes = ""

def clean_content(content) -> dict:
    """Parse the content string into a structured format."""
    sections = {}
    current_section = None
    current_content = []
    
    # Convert content to string, handling AIMessage objects
    if hasattr(content, 'content'):
        content = content.content
    content = str(content)
    
    # Split content into lines and process
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for section headers
        if '**Key Numerical Data**' in line or '**Main Points**' in line or '**Important Disclosures**' in line:
            if current_section and current_content:
                sections[current_section] = current_content
            current_section = line.replace('**', '')
            current_content = []
        # Check for bullet points
        elif line.startswith('•') or line.startswith('-'):
            cleaned_line = line.replace('•', '').replace('-', '').strip()
            if cleaned_line:
                current_content.append(cleaned_line)
            
    # Add the last section
    if current_section and current_content:
        sections[current_section] = current_content
        
    return sections

def display_analysis_results(content, title: str):
    """Display the analysis results in a clean format."""
    st.subheader(title)
    
    try:
        sections = clean_content(content)
        
        if not sections:
            st.write("Raw content:")
            st.write(content)
            return
            
        for section, points in sections.items():
            st.write(f"**{section}**")
            for point in points:
                st.write(f"• {point}")
            st.write("")  # Add space between sections
            
    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")
        st.write("Raw content:")
        st.write(content)

def display_website_analysis(url: str, data: dict, expanded: bool = True):
    """Display website analysis results in an expander."""
    with st.expander(f"Website Analysis for {url}", expanded=expanded):
        article = data['article']
        analysis = data['analysis']
        
        st.subheader("Article Information")
        if article.title:
            st.write(f"Title: {article.title}")
        if article.author:
            st.write(f"Author: {article.author}")
        if article.date:
            st.write(f"Date: {article.date}")
        
        st.subheader("Analysis")
        st.write("Investment Themes:")
        for theme in analysis.investment_themes:
            st.write(f"- {theme}")
        
        st.write("Key Points:")
        for point in analysis.key_points:
            st.write(f"- {point}")
        
        st.write("Summary:")
        st.write(analysis.summary)

def display_adv_analysis(adv_data, expanded: bool = True):
    """Display ADV analysis results in an expander."""
    with st.expander("ADV Analysis Results", expanded=expanded):
        if adv_data.aum_summary:
            display_analysis_results(
                adv_data.aum_summary,
                "Assets Under Management Summary"
            )
        else:
            st.warning("Could not extract AUM information")
        
        st.markdown("---")
        
        if adv_data.fees_summary:
            display_analysis_results(
                adv_data.fees_summary,
                "Fees Summary"
            )
        else:
            st.warning("Could not extract fees information")

def display_fund_matches(matches: list):
    """Display mutual fund matching results with enhanced UI."""
    st.header("🎯 Mutual Fund Recommendations")
    
    # Introduction
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>
        Based on comprehensive analysis of the RIA's website content and ADV filing, we've identified the following 
        mutual fund matches, ranked by compatibility score.
    </div>
    """, unsafe_allow_html=True)
    
    # Display each fund match
    for match in matches:
        score = match['score']
        score_color = get_score_color(score)
        
        with st.container():
            # Fund header with score
            st.markdown(f"""
            <div style='background-color: {score_color}; padding: 1rem; border-radius: 0.5rem 0.5rem 0 0;'>
                <h3 style='color: white; margin: 0;'>
                    {match['fund_name']} 
                    <span style='float: right;'>Match Score: {score}/5</span>
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Fund details
            with st.container():
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("##### 📝 Match Rationale")
                    st.markdown(match['rationale'])
                
                with col2:
                    # Strengths
                    st.markdown("##### 💪 Key Strengths")
                    for strength in match['strengths']:
                        st.markdown(f"✅ {strength}")
                    
                    # Considerations
                    if match['concerns']:
                        st.markdown("##### ⚠️ Considerations")
                        for concern in match['concerns']:
                            st.markdown(f"• {concern}")
            
            st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Footer note
    st.markdown("""
    <div style='padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;'>
        <p style='margin: 0;'>
            <strong>💡 Note:</strong> These recommendations are based on AI analysis of your firm's 
            characteristics and investment approach. Consider them as starting points for further due diligence.
        </p>
    </div>
    """, unsafe_allow_html=True)

def get_score_color(score: float) -> str:
    """Return color based on match score."""
    if score >= 4.5:
        return "#2e7d32"  # Dark green
    elif score >= 4.0:
        return "#558b2f"  # Green
    elif score >= 3.5:
        return "#f9a825"  # Orange
    elif score >= 3.0:
        return "#ef6c00"  # Dark orange
    else:
        return "#c62828"  # Red

def main():
    st.set_page_config(
        page_title="Asset Management Analyst",
        page_icon="📊",
        layout="wide"
    )
    
    init_session_state()
    
    st.title("Advanced AI Analyst to Analyze RIA and Suggest Mutual Funds")

    api_key = get_openai_api_key()
    
    # Initialize components
    scraper = WebsiteScraper()
    analyzer = ContentAnalyzer(api_key)
    
    # Sidebar
    with st.sidebar:
        st.header("Analyze RIA")

        # RIA Website Section
        website_urls = st.text_area(
            "RIA Website URLs (one per line)", 
            value="https://www.sandhillglobaladvisors.com/blog/positioning-for-the-future/",
            height=100,
            help="Enter multiple URLs, one per line"
        )

        # Meeting Notes Section
        meeting_notes = st.text_area(
            "Meeting Notes (optional)",
            value=st.session_state.meeting_notes,
            height=150,
            help="Enter any additional context from client meetings"
        )
        st.session_state.meeting_notes = meeting_notes

        # Convert text area input to list of URLs
        urls = [url.strip() for url in website_urls.split('\n') if url.strip()]
        analyze_button = st.button("Step 1: Review RIA Info")

        # ADV Filing Section
        adv_url = st.text_input(
            "ADV Filing URL",
            value="https://adviserinfo.sec.gov/firm/summary/111295"
        )
        analyze_adv_button = st.button("Step 2: Review ADV Filing")

        if st.button("Clear All Analyses"):
            st.session_state.analyses = {}
            st.session_state.adv_analyses = {}
            st.session_state.fund_matches = {}
            st.rerun()
        
        # Mutual Fund Matching Section
        st.markdown("---")
        st.subheader("Suggest Mutual Funds")
        st.markdown("""
        Our AI-powered matching engine analyzes RIA characteristics against mutual funds based on:
        
        🎯 **Strategic Fit**
        - AUM compatibility
        - Fee structure alignment
        - Investment philosophy
        
        👥 **Client Alignment**
        - Client type match
        - Minimum investment requirements
        - Service model compatibility
        
        📊 **Operational Factors**
        - Investment style
        - Risk management approach
        - Operational capabilities
        
        *Click below after analyzing website and ADV to get personalized fund suggestions.*
        """)
        suggest_funds_button = st.button("Step 3: Suggest Mutual Funds")

    # Handle Website Analysis
    if analyze_button and (urls or st.session_state.meeting_notes):
        with st.spinner("Analyzing websites..."):
            for url in urls:
                if url not in st.session_state.analyses:
                    article = scraper.parse_article(url)
                    if article and article.content:
                        analysis = analyzer.analyze_content(article.content)
                        st.session_state.analyses[url] = {
                            'article': article,
                            'analysis': analysis
                        }
                    else:
                        st.error(f"Failed to fetch content from: {url}")
            
            # Display all analyses
            for url, data in st.session_state.analyses.items():
                display_website_analysis(url, data)
    

    # Handle ADV Analysis
    if analyze_adv_button and adv_url:
        with st.spinner("Analyzing ADV filing..."):
            try:
                adv_analyzer = ADVAnalyzer(api_key)
                adv_content = adv_analyzer.analyze_adv(adv_url)
                    
                if adv_content:
                    st.session_state.adv_analyses[adv_url] = adv_content
                    display_adv_analysis(adv_content)
                else:
                    st.error("Failed to analyze ADV filing - please check the URL format")
                    
            except Exception as e:
                st.error(f"Error during ADV analysis: {str(e)}")
                logger.error(f"Error during ADV analysis: {e}")

    # Handle Fund Matching
    if suggest_funds_button:
        if not st.session_state.analyses or not st.session_state.adv_analyses:
            st.error("Please analyze both website and ADV filing first")
        else:
            try:
                # Get the latest analyzed data
                adv_data = next(iter(st.session_state.adv_analyses.values()))
                
                # Prepare RIA data
                website_data = {
                    "website_analyses": [
                        {
                            "url": url,
                            "investment_themes": data['analysis'].investment_themes,
                            "key_points": data['analysis'].key_points,
                            "summary": data['analysis'].summary
                        }
                        for url, data in st.session_state.analyses.items()
                    ],
                    "aum_summary": adv_data.aum_summary,
                    "fees_summary": adv_data.fees_summary,
                    "meeting_notes": st.session_state.meeting_notes if st.session_state.meeting_notes else None
                }
                
                # Get fund matches
                with st.spinner("Analyzing mutual fund matches..."):
                    fund_matcher = LLMFundMatcher(api_key)
                    matches = fund_matcher.analyze_matches(website_data)
                    st.session_state.fund_matches = matches
                
                # Display results in order
                display_fund_matches(matches)
                st.markdown("---")
                display_adv_analysis(adv_data)
                st.markdown("---")
                # Display all website analyses
                for url, data in st.session_state.analyses.items():
                    display_website_analysis(url, data)
                
            except Exception as e:
                st.error(f"Error generating fund suggestions: {str(e)}")
                logger.error(f"Error in fund matching: {e}")

if __name__ == "__main__":
    main()