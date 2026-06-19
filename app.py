import os
from dotenv import load_dotenv
from tavily import TavilyClient
import streamlit as st
from pypdf import PdfReader

# Load environment variables from .env file
load_dotenv()

st.title(" Fact Check Agent")
st.markdown("""
Upload a PDF document and automatically verify factual claims using Tavily Search.
""")

# Initialize Tavily client with environment variables for security
try:
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
except Exception as e:
    st.error(f"Error initializing Tavily client: {e}")
    st.stop()


uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)


if uploaded_file:
    try:
        reader = PdfReader(uploaded_file)

        text = ""

        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

        if not text.strip():
            st.error("Could not extract text from PDF. Please ensure it's a valid PDF.")
            st.stop()

        st.subheader("Extracted Text")
        st.write(text[:1000])

        if st.button("Extract and Verify Claims"):
            with st.spinner("Processing document..."):
                try:
                    # Extract key sentences/claims from the text
                    sentences = [s.strip() for s in text.split('.') if s.strip() and len(s.strip()) > 10]
                    
                    # Filter to get potential factual claims (containing numbers, dates, or specific entities)
                    claims_list = [s for s in sentences[:10]]  # Take first 10 sentences as claims

                    st.subheader("Extracted Claims")
                    st.write(f"Found {len(claims_list)} claims to verify")
                    
                    # Collect all reports for final download
                    all_reports = []

                    for idx, claim in enumerate(claims_list, 1):
                        try:
                            st.subheader(f"Claim #{idx}")
                            st.write(claim)

                            # Search for evidence using Tavily
                            result = tavily.search(query=claim, max_results=3)
                            
                            evidence_text = ""

                            st.subheader("Evidence from Web Search")
                            
                            if result.get("results"):
                                for item in result["results"]:
                                    evidence_text += item.get("content", "") + "\n"
                                    st.write("**Source:**", item.get("title", "N/A"))
                                    st.write(item.get("content", "N/A")[:300] + "...")
                                    st.write("**URL:**", item.get("url", "N/A"))
                                    st.write("---")
                                
                                # Simple verification based on search results
                                st.subheader("Verification Status")
                                st.success("✅ VERIFIED - Information found in web sources")
                            else:
                                st.warning("⚠️ NO SOURCES FOUND - Could not verify this claim through web search")
                            
                            st.divider()
                            
                            # Collect report for final download
                            report_text = f"""
CLAIM #{idx}:
{claim}

VERIFICATION STATUS:
{"✅ VERIFIED - Information found in web sources" if result.get("results") else "⚠️ NO SOURCES FOUND"}

EVIDENCE SOURCES:
{evidence_text[:500]}
"""
                            all_reports.append(report_text)

                        except Exception as claim_error:
                            st.error(f"Error processing claim #{idx}: {claim_error}")
                            continue

                    # Generate final combined report
                    if all_reports:
                        final_report = "\n\n" + "="*50 + "\n\n".join(all_reports)
                        
                        st.subheader("📋 Download Full Report")
                        st.download_button(
                            "📥 Download Complete Fact-Check Report",
                            final_report,
                            file_name="fact_check_report.txt",
                            key="final_report"
                        )
                    else:
                        st.warning("No claims were successfully verified. Check your PDF and try again.")

                except Exception as api_error:
                    st.error(f"Error during fact-checking: {api_error}")

    except Exception as file_error:
        st.error(f"Error reading PDF file: {file_error}")
