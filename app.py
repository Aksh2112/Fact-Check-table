import os
from tavily import TavilyClient
import streamlit as st
from pypdf import PdfReader
from google import genai

st.title(" Fact Check Agent")
st.markdown("""
Upload a PDF document and automatically verify factual claims using Gemini AI and Tavily Search.
""")

# Initialize clients with environment variables for security
try:
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    st.error(f"Error initializing API clients: {e}")
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

        if st.button("Check Facts"):
            with st.spinner("Fact checking..."):
                try:
                    prompt = f"""
                    Extract factual claims from this document.

                    Only give:
                    - dates
                    - numbers
                    - statistics
                    - financial facts

                    Document:
                    {text}
                    """

                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    
                    st.subheader("Extracted Claims")

                    claims = response.text  
                    st.write(claims)
                    
                    # Parse claims into list
                    claims_list = [claim.strip() for claim in claims.split("\n") if claim.strip()]

                    for claim in claims_list:
                        try:
                            st.subheader("Claim")
                            st.write(claim)

                            # Search for evidence
                            result = tavily.search(query=claim)
                            
                            evidence_text = ""

                            st.subheader("Evidence")
                            
                            if result.get("results"):
                                for item in result["results"][:3]:
                                    evidence_text += item.get("content", "") + "\n"
                                    st.write("Source:", item.get("title", "N/A"))
                                    st.write(item.get("content", "N/A"))
                                    st.write(item.get("url", "N/A"))
                                    st.write("---")
                            else:
                                st.info("No search results found for this claim.")

                            # Verify claim
                            verification_prompt = f"""
                            You are a professional fact checker.
                            Claim:
                            {claim}

                            Evidence:
                            {evidence_text}

                            Based on the evidence, classify the claim as:
                            - VERIFIED (matches current data)
                            - INACCURATE (partially correct or outdated)
                            - FALSE (contradicted by evidence)

                            Return only:

                            Verdict: VERIFIED / INACCURATE / FALSE

                            Reason:
                            <2 lines explanation>
                            """
                            
                            verification_response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=verification_prompt
                            )

                            st.subheader("Verdict")
                            verdict = verification_response.text

                            if "VERIFIED" in verdict:
                                st.success(verdict)
                            elif "FALSE" in verdict:
                                st.error(verdict)
                            elif "INACCURATE" in verdict:
                                st.warning(verdict)
                            else:
                                st.info(verdict)

                            st.divider()
                            
                            # Generate report
                            report_text = f"""
                            Claim:
                            {claim}

                            Verdict:
                            {verification_response.text}
                            """

                            st.download_button(
                                "Download Report",
                                report_text,
                                file_name="fact_check_report.txt"
                            )

                        except Exception as claim_error:
                            st.error(f"Error processing claim: {claim_error}")
                            continue

                except Exception as api_error:
                    st.error(f"Error during fact-checking: {api_error}")

    except Exception as file_error:
        st.error(f"Error reading PDF file: {file_error}")
