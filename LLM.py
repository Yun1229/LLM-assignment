import re
from openai import OpenAI


### Functions for LLM


def get_client(api_key: str) -> OpenAI:
    client = OpenAI(api_key=api_key)
    return client


# Minimize API Calls by Using Local Processing First
def preprocess_text(eligibility_text: str) -> str:
    # Extract the "Inclusion Criteria" section using regex or keyword-based filtering
    match = re.search(
        r"Inclusion Criteria:.*?(Exclusion Criteria:|$)",
        eligibility_text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(0)
    return eligibility_text


def LLM_model(client: OpenAI, eligibility_text: str) -> str:
    # Construct a prompt to extract diseases/conditions only from inclusion criteria
    prompt = f"""
    Extract all diseases, conditions, or criteria related to medical treatments or exposures.

    Important:
    - Include diseases, conditions, demographic criteria (e.g., gender, age, ethnicity), and medical treatments or exposures (e.g., "FIX products exposure") while excluding numeric thresholds or detailed qualifiers.
    - Combine demographic criteria into a single entry
    - Retain contextual information or negations when they are part of the condition (e.g., "no FIX inhibitor formation").
    - Ensure the output is concise and excludes extra text or formatting.
    
    Eligibility Criteria: {eligibility_text}
    
    Please list only the diseases or conditions without any extra text.
    """

    # Call the OpenAI API with the prompt
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You're a helpful clinical trial assistant"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=100,
        temperature=0,
    )

    # Extract the response text containing the diseases/conditions
    extracted_conditions = response.choices[0].message.content
    return extracted_conditions
