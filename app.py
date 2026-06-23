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


def analyze_claim(claim, search_results):
    """
    Analyze search results to determine verification status.
    Returns: status (VERIFIED, NOT_VERIFIED, POSSIBLY_FALSE), confidence (0-100), reasoning
    """
    
    if not search_results:
        return "NOT_VERIFIED", 0, "No sources found for this claim"
    
    # Collect evidence text
    evidence_texts = [item.get("content", "").lower() for item in search_results]
    combined_evidence = " ".join(evidence_texts)
    claim_lower = claim.lower()
    
    # Keywords that indicate contradiction/false information
    contradiction_keywords = ["not", "false", "incorrect", "wrong", "denied", "refuted", "debunked", "hoax", "fabricated"]
    
    # Keywords that indicate confirmation
    confirmation_keywords = ["confirmed", "verified", "true", "correct", "accurate", "fact", "proven", "evidence", "studies show", "research shows"]
    
    contradiction_count = sum(1 for keyword in contradiction_keywords if keyword in combined_evidence)
    confirmation_count = sum(1 for keyword in confirmation_keywords if keyword in combined_evidence)
    
    # Check for exact or strong matches
    claim_parts = [word for word in claim_lower.split() if len(word) > 3]
    matching_words = sum(1 for part in claim_parts if part in combined_evidence)
    match_ratio = matching_words / len(claim_parts) if claim_parts else 0
    
    # Determine status based on analysis
    if match_ratio > 0.6 and confirmation_count > contradiction_count:
        status = "VERIFIED"
        confidence = min(95, 60 + (confirmation_count * 10))
    elif contradiction_count > confirmation_count:
        status = "POSSIBLY_FALSE"
        confidence = min(90, 50 + (contradiction_count * 15))
    elif match_ratio > 0.4 and len(search_results) >= 2:
        status = "VERIFIED"
        confidence = min(85, 50 + (match_ratio * 30))
    elif len(search_results) >= 3:
        status = "NOT_VERIFIED"
        confidence = 45
    else:
        status = "NOT_VERIFIED"
        confidence = 25
    
    reasoning = f"Found {len(search_results)} sources. Match ratio: {match_ratio:.0%}. "
    if contradiction_count > 0:
        reasoning += f"{contradiction_count} contradictory indicators. "
    if confirmation_count > 0:
        reasoning += f"{confirmation_count} confirmation indicators."
    
    return status, confidence, reasoning


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
                    
                    # Track statistics
                    stats = {"VERIFIED": 0, "NOT_VERIFIED": 0, "POSSIBLY_FALSE": 0}

                    for idx, claim in enumerate(claims_list, 1):
                        try:
                            st.subheader(f"Claim #{idx}")
                            st.write(claim)

                            # Search for evidence using Tavily
                            result = tavily.search(query=claim, max_results=3)
                            search_results = result.get("results", [])
                            
                            # Analyze the claim
                            status, confidence, reasoning = analyze_claim(claim, search_results)
                            stats[status] += 1
                            
                            evidence_text = ""

                            st.subheader("Evidence from Web Search")
                            
                            if search_results:
                                for item in search_results:
                                    evidence_text += item.get("content", "") + "\n"
                                    st.write("**Source:**", item.get("title", "N/A"))
                                    st.write(item.get("content", "N/A")[:300] + "...")
                                    st.write("**URL:**", item.get("url", "N/A"))
                                    st.write("---")
                            else:
                                st.info("No sources found for this claim")
                            
                            # Display verification status with color coding
                            st.subheader("Verification Status")
                            
                            if status == "VERIFIED":
                                st.success(f"✅ VERIFIED - Information found in web sources (Confidence: {confidence}%)")
                                status_emoji = "✅"
                            elif status == "POSSIBLY_FALSE":
                                st.error(f"❌ POSSIBLY FALSE - Contradictory information found (Confidence: {confidence}%)")
                                status_emoji = "❌"
                            else:  # NOT_VERIFIED
                                st.warning(f"⚠️ NOT VERIFIED - Could not verify through web search (Confidence: {confidence}%)")
                                status_emoji = "⚠️"
                            
                            st.info(f"**Analysis Reasoning:** {reasoning}")
                            
                            st.divider()
                            
                            # Collect report for final download
                            report_text = f"""
CLAIM #{idx}:
{claim}

VERIFICATION STATUS: {status_emoji} {status}
Confidence Level: {confidence}%

ANALYSIS REASONING:
{reasoning}

EVIDENCE SOURCES:
{evidence_text[:500] if evidence_text else "No sources found"}
"""
                            all_reports.append(report_text)

                        except Exception as claim_error:
                            st.error(f"Error processing claim #{idx}: {claim_error}")
                            continue

                    # Display summary statistics
                    st.subheader("📊 Verification Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Verified", stats["VERIFIED"])
                    with col2:
                        st.metric("⚠️ Not Verified", stats["NOT_VERIFIED"])
                    with col3:
                        st.metric("❌ Possibly False", stats["POSSIBLY_FALSE"])

                    # Generate final combined report
                    if all_reports:
                        summary_section = f"""
FACT-CHECK REPORT SUMMARY
{'='*50}
Total Claims Analyzed: {len(claims_list)}
✅ Verified: {stats['VERIFIED']}
⚠️ Not Verified: {stats['NOT_VERIFIED']}
❌ Possibly False: {stats['POSSIBLY_FALSE']}
{'='*50}
"""
                        final_report = summary_section + "\n\n" + "="*50 + "\n\n".join(all_reports)
                        
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
