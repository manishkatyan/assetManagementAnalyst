import requests
from dataclasses import dataclass
from typing import Optional, Tuple
import tempfile
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import logging
import PyPDF2
import re

logger = logging.getLogger(__name__)

@dataclass
class ADVContent:
    url: str
    aum_summary: Optional[str] = None
    fees_summary: Optional[str] = None

class ADVAnalyzer:
    def __init__(self, openai_api_key: str):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=openai_api_key
        )

    def extract_firm_id(self, url: str) -> Optional[str]:
        """Extract firm ID from the URL."""
        print(f"Extracting firm ID from URL: {url}")
        match = re.search(r'/firm/summary/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def validate_sec_url(self, url: str) -> bool:
        """Validate if the SEC URL is accessible."""
        try:
            response = requests.get(url, headers=self.headers)
            print(f"SEC URL validation status code: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error validating SEC URL: {e}")
            return False

    def get_pdf_urls(self, firm_id: str) -> Tuple[str, str]:
        """Construct PDF URLs from firm ID."""
        adv_url = f"https://reports.adviserinfo.sec.gov/reports/ADV/{firm_id}/PDF/{firm_id}.pdf"
        crs_url = f"https://reports.adviserinfo.sec.gov/crs/crs_{firm_id}.pdf"
        return adv_url, crs_url

    def download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF content."""
        print(f"Downloading PDF from: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            print(f"PDF downloaded successfully: {url}")
            return response.content
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None

    def extract_section_from_pdf(self, pdf_content: bytes, section_title: str) -> Optional[str]:
        """Extract specific section from PDF content."""
        print(f"Extracting section: {section_title}")
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file.seek(0)
                
                reader = PyPDF2.PdfReader(temp_file.name)
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"

                print(f"Extracted {len(full_text)} characters from PDF")
                
                # For Form ADV, find the specific section
                if "Item 5" in section_title:
                    start_marker = "Item 5 Information About Your Advisory Business"
                    end_marker = "Item 6"  # Next section
                    start_idx = full_text.find(start_marker)
                    end_idx = full_text.find(end_marker, start_idx) if start_idx != -1 else -1
                    
                    if start_idx != -1 and end_idx != -1:
                        section_text = full_text[start_idx:end_idx]
                    else:
                        print("Could not find Item 5 section boundaries")
                        return None
                else:
                    start_marker = "WHAT FEES WILL I PAY?"
                    end_marker = "WHAT ARE YOUR LEGAL OBLIGATIONS"
                    start_idx = full_text.find(start_marker)
                    end_idx = full_text.find(end_marker, start_idx) if start_idx != -1 else -1
                    
                    if start_idx != -1 and end_idx != -1:
                        section_text = full_text[start_idx:end_idx]
                    else:
                        print(f"Could not find section: {section_title}")
                        return None

                print(f"Found relevant section: {len(section_text)} characters")
                
                template = """Analyze and summarize the following section from an SEC filing:

                {text}

                Provide a clear, concise summary in the following format:

                **Key Numerical Data**
                • [List numerical data points here]

                **Main Points**
                • [List main points here]

                **Important Disclosures**
                • [List important disclosures here]

                Ensure each point starts with a bullet point (•) and provides clear, specific information."""
                
                prompt = ChatPromptTemplate.from_template(template)
                chain = prompt | self.llm
                
                print("Starting LLM analysis...")
                result = chain.invoke({
                    "text": section_text
                })
                
                # Extract content from AIMessage
                if hasattr(result, 'content'):
                    result = result.content
                    
                print("LLM analysis complete")
                return result
            
        except Exception as e:
            print(f"Error extracting section: {e}")
            return None
        finally:
            if 'temp_file' in locals():
                os.unlink(temp_file.name)

    def analyze_adv(self, url: str) -> Optional[ADVContent]:
        """Main analysis function."""
        print(f"Starting ADV analysis for URL: {url}")
        
        # Extract firm ID and validate URL
        firm_id = self.extract_firm_id(url)
        if not firm_id:
            print("Invalid URL format - couldn't extract firm ID")
            return None
        
        if not self.validate_sec_url(url):
            print("Invalid or inaccessible SEC URL")
            return None
        
        # Get PDF URLs
        adv_url, crs_url = self.get_pdf_urls(firm_id)
        print(f"Generated URLs - ADV: {adv_url}, CRS: {crs_url}")
        
        adv_content = ADVContent(url=url)
        
        # Download and analyze Form ADV
        adv_pdf = self.download_pdf(adv_url)
        if adv_pdf:
            adv_content.aum_summary = self.extract_section_from_pdf(
                adv_pdf,
                "Item 5 Information About Your Advisory Business - Regulatory Assets Under Management"
            )
        
        # Download and analyze Relationship Summary
        crs_pdf = self.download_pdf(crs_url)
        if crs_pdf:
            adv_content.fees_summary = self.extract_section_from_pdf(
                crs_pdf,
                "WHAT FEES WILL I PAY?"
            )
        
        return adv_content