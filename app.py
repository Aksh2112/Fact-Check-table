from tavily import TavilyClient
import streamlit as st
from pypdf import PdfReader
from google import genai

st.title(" Fact Check Agent")
st.markdown("""
Upload a PDF document and automatically verify factual claims using Gemini AI and Tavily Search.
""")

tavily = TavilyClient(
    api_key="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"
)

client = genai.Client(
    api_key="AQ.Ab8RN6Kk1KFaTvT1f7Wtn7TM1jc-irQfNHkJFUTOU3ZTxzVrkQ"
)



uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)


if uploaded_file:

    reader = PdfReader(uploaded_file)

    text = ""

    for page in reader.pages:
        text += page.extract_text()


    st.subheader("Extracted Text")
    st.write(text[:1000])


    if st.button("Check Facts"):
      with st.spinner("Fact checking..."):

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
    contents=prompt)


        st.subheader("Extracted Claims")

        claims = response.text  
        st.write(claims)
        
        for claim in claims.split("\n"):

          if claim.strip():

            st.subheader("Claim")
            st.write(claim)

            result = tavily.search(
            query=claim
          )
          
          evidence_text= ""

          st.subheader("Evidence")
          for item in result["results"][:3]:
            
            evidence_text += item["content"] + "\n"

            st.write("Source:", item["title"])
            st.write(item["content"])
            st.write(item["url"])
            st.write("---")


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
        report_text = f"""
        Claim:
        {claim}

        Verdict:
        {verification_response.text}
        """

        st.download_button(
          "Download Report", report_text,
          file_name="fact_check_report.txt"
        )
