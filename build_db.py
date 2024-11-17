from pytrials.client import ClinicalTrials
import pymongo
from pymongo import UpdateOne, InsertOne
import json
import pickle
import re
from openai import OpenAI
from config import api_key


#### Load the variables for reproducibility
"""
with open("retrieved_studies.pkl", "rb") as f:
    retrieved_studies = pickle.load(f)

with open("mapped_data_all.pkl", "rb") as f:
    mapped_data_all = pickle.load(f)

"""


def create_col(client, db_name, col_name, schema=None):
    db = client[db_name]

    if col_name in db.list_collection_names():
        db.drop_collection(col_name)

    if schema is None:
        # Create collection without validation
        collection = db.create_collection(col_name)
    else:
        # Database validation.
        collection = db.create_collection(
            col_name, validator={"$jsonSchema": schema}, validationAction="warn"
        )
        print("Database validated with schema.")
    return collection


def flatten(arg):
    if not isinstance(arg, list):  # if not list
        return [arg]
    return [x for sub in arg for x in flatten(sub)]


def get_nested_value(data, keys2):
    keys = keys2.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list):
            valuelist = []
            for ele in data:
                valuelist.append(ele.get(key))
            data = flatten(valuelist)
    return data


### Functions for data mapping


def get_date(study):
    start = get_nested_value(study, "protocolSection.statusModule.startDateStruct.date")

    end = get_nested_value(
        study, "protocolSection.statusModule.completionDateStruct.date"
    )

    def modify_date(date):
        if date is None:
            return "NA"
        if len(date) == 7:
            return date + "-01"
        else:
            return date

    return modify_date(start), modify_date(end)


def get_phase(study):
    phase = get_nested_value(study, "protocolSection.designModule.phases")

    if phase == None:
        return "Other"
    return next(
        (
            f"Phase {p[-1]}"
            for p in phase
            if p.upper() in ["PHASE1", "PHASE2", "PHASE3", "PHASE4"]
        ),
        "Other",
    )


def get_principal_investigator(study):
    overall_officials = get_nested_value(
        study, "protocolSection.contactsLocationsModule.overallOfficials"
    )
    if not overall_officials:  # Check if overall_officials is None or empty
        return []

    return [
        {
            "name": official.get("name", "NA"),
            "affiliation": official.get("affiliation", "NA"),
        }
        for official in overall_officials
        if official.get("role") == "PRINCIPAL_INVESTIGATOR"
    ]


def get_locations(study):
    locations = get_nested_value(
        study, "protocolSection.contactsLocationsModule.locations"
    )

    if not locations:  # Check if overall_officials is None or empty
        return []
    return [
        {
            "facility": loc.get("facility", ""),
            "city": loc.get("city", ""),
            "country": loc.get("country", ""),
        }
        for loc in locations
    ]


def transform_study(study):

    return {
        "trialId": get_nested_value(
            study, "protocolSection.identificationModule.nctId"
        ),
        "title": get_nested_value(
            study, "protocolSection.identificationModule.officialTitle"
        ),
        "startDate": get_date(study)[0],
        "endDate": get_date(study)[1],
        "phase": get_phase(study),
        "principalInvestigator": get_principal_investigator(study),
        "locations": get_locations(study),
        "eligibilityCriteria": get_nested_value(
            study, "protocolSection.eligibilityModule.eligibilityCriteria"
        ),
    }


def map_data(input_data):
    transformed_data = []
    for study in input_data["studies"]:
        transformed_data.append(transform_study(study))
    return transformed_data


### Functions to insert or update data in MongoDB
def upsert_data_to_db(data, collection):
    requests = []

    # Fetch original documents before updating
    for entry in data:
        trial_id = entry["trialId"]
        original_document = collection.find_one({"trialId": trial_id})
        if original_document:
            requests.append(
                UpdateOne({"trialId": trial_id}, {"$set": entry})
            )  # upsert=False
            for key, value in entry.items():
                old_value = original_document.get(key)
                if old_value != value:  # Identify modified fields
                    print(
                        f"Trial ID: {trial_id}, Field: {key}, From: {old_value} To: {value}"
                    )
        else:
            requests.append(InsertOne(entry))

    if requests:
        result = collection.bulk_write(requests)  # Use bulk_write for batch processing
        if result.inserted_count > 0:
            print(f"Number of documents inserted: {result.inserted_count}")

        if result.modified_count > 0:
            print(f"Number of documents updated: {result.modified_count}")

    collection.create_index("trialId")


### Functions for LLM
# Minimize API Calls by Using Local Processing First
def preprocess_text(eligibility_text):
    # Extract the "Inclusion Criteria" section using regex or keyword-based filtering
    match = re.search(
        r"Inclusion Criteria:.*?(Exclusion Criteria:|$)",
        eligibility_text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(0)
    return eligibility_text


def LLM_model(eligibility_text):
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


def add_dict_pair(opkey, opvalue, results_dict):
    if opkey not in results_dict:
        results_dict[opkey] = []
    results_dict[opkey].append(opvalue)


# Function to process trials and extract conditions
def extract_info(collection, field, content):
    results_dict = {}

    for trial in collection.find({}):
        opkey = get_nested_value(trial, field)
        opvalue = get_nested_value(trial, content)
        if opvalue:
            if content == "eligibilityCriteria":
                inclusion_text = preprocess_text(opvalue)
                opvalue = LLM_model(inclusion_text)
            if isinstance(opkey, list):
                for opkeysingle in opkey:
                    add_dict_pair(opkeysingle, opvalue, results_dict)

            else:
                add_dict_pair(opkey, opvalue, results_dict)

    return results_dict


def store_in_collection(field, content, results_dict, collection, batch_size=100):
    operations = []

    for key, value in results_dict.items():
        operations.append(
            UpdateOne(
                {field: key},
                {"$set": {content: value}},
            )
        )

        if len(operations) == batch_size:
            collection.bulk_write(operations)
            operations = []

    if operations:
        collection.bulk_write(operations)


if __name__ == "__main__":

    mongoDB_client = pymongo.MongoClient("mongodb://localhost:27017/")

    # Load schema from JSON file
    with open("schema.json", "r") as schema_file:
        schema = json.load(schema_file)

    # Create a collection
    print("Create a collection.")
    final_collection = create_col(
        mongoDB_client, "ClinicalTrialsDB", "clinical_trial_collection", schema
    )

    # Retrieve metadata via clinicaltrials.gov API
    ct = ClinicalTrials()
    print("Retrieve metadata via clinicaltrials.gov API.")
    # """
    retrieved_studies = ct.get_full_studies(
        search_expr="AREA[LastUpdatePostDate]RANGE[2024-10-20, 2024-10-21]",
        max_studies=1000,  # if more than 1000?
        fmt="json",
    )
    # """

    # Transform the input data
    print("Transform the input data.")
    mapped_data_all = map_data(retrieved_studies)
    print("Insert the mapped data to the collection.")
    upsert_data_to_db(mapped_data_all, final_collection)

    # Perform LLM
    print("Perform LLM")
    client = OpenAI(api_key=api_key)
    print("Extracting info...")
    results_dict = extract_info(final_collection, "trialId", "eligibilityCriteria")
    """
    with open("results_dict.pkl", "rb") as f:
        results_dict = pickle.load(f)
    """

    print("Storing the extracted info in the collection as 'extractedDiseases'...")
    store_in_collection("trialId", "extractedDiseases", results_dict, final_collection)

    mongoDB_client.close()
    print("Pipeline finished!")

    # If we were to a link the PI to a researcher profile:
    """
    extract_info(final_collection, "principalInvestigator.name", "trialId")
    results_dict = extract_info(
        final_collection, "principalInvestigator.name", "trialId"
    )




    store_in_collection(
        "principalInvestigator.name", "conducted_trial", results_dict, final_collection
    )  ## or other collection
    """
