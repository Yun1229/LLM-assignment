from pytrials.client import ClinicalTrials
from openai import OpenAI
from config import api_key
import pymongo
import json
import pickle
import mongoDB as db
import LLM
import mapping
import transform


#### Load the variables for reproducibility
"""
with open("retrieved_studies.pkl", "rb") as f:
    retrieved_studies = pickle.load(f)
"""
"""

with open("mapped_data_all.pkl", "rb") as f:
    mapped_data_all = pickle.load(f)

"""
if __name__ == "__main__":
    try:
        try:
            mongoDB_client = pymongo.MongoClient("mongodb://localhost:27017/")
        except pymongo.errors.ConnectionError as e:
            print(f"Failed to connect to MongoDB: {e}")
            exit(1)

        try:
            # Load schema from JSON file
            with open("schema.json", "r") as schema_file:
                schema = json.load(schema_file)
        except Exception as e:
            print()
            exit()

        # Create a collection
        print("Create a collection.")
        try:
            final_collection = db.create_col(
                mongoDB_client, "ClinicalTrialsDB", "clinical_trial_collection", schema
            )
        except Exception as e:
            print(f"Error creating a collection: {e}")
            exit(1)

        # Retrieve metadata via clinicaltrials.gov API
        ct = ClinicalTrials()
        print("Retrieve metadata via clinicaltrials.gov API.")
        try:
            # """
            retrieved_studies = ct.get_full_studies(
                search_expr="AREA[LastUpdatePostDate]RANGE[2024-10-20, 2024-10-21]",
                max_studies=1000,  # if more than 1000?
                fmt="json",
            )
            # """
            if not retrieved_studies:
                raise ValueError("No studies retrieved or invalid response structure.")
        except Exception as e:
            print(f"Error fetching data from the API: {e}")
            exit(1)

        # Transform the input data
        print("Transform the input data.")
        try:
            mapped_data_all = mapping.map_data(retrieved_studies)

        except KeyError as e:
            print(f"KeyError during data transformation: Missing key {e}")
        except Exception as e:
            print(f"Unexpected error during data transformation: {e}")

        print("Insert the mapped data to the collection.")
        try:
            db.upsert_data_to_db(mapped_data_all, final_collection)
        except pymongo.errors.BulkWriteError as e:
            print(f"Error during bulk write: {e.details}")
        except Exception as e:
            print(f"Unexpected error during MongoDB operations: {e}")

        # Perform LLM
        print("Perform LLM")
        client = LLM.get_client(api_key=api_key)
        print("Extracting info...")
        try:
            # """
            results_dict = transform.extract_info(
                final_collection, "trialId", "eligibilityCriteria"
            )
            # """
            """
            with open("results_dict.pkl", "rb") as f:
                results_dict = pickle.load(f)
            """
        except OpenAI.error.OpenAIError as e:
            print(f"OpenAI API Error: {e}")
        except Exception as e:
            print(f"Unexpected error during LLM processing: {e}")

        print("Storing the extracted info in the collection as 'extractedDiseases'...")
        try:
            db.store_in_collection(
                "trialId", "extractedDiseases", results_dict, final_collection
            )
        except Exception as e:
            print(f"Unexpected error during storing processing: {e}")
    except Exception as pipeline_error:
        print(f"Pipeline execution failed: {pipeline_error}")
    finally:
        mongoDB_client.close()
    print("Pipeline finished!")

    # If we were to a link the PI to a researcher profile:
    """
    transform.extract_info(final_collection, "principalInvestigator.name", "trialId")
    results_dict = transform.extract_info(
        final_collection, "principalInvestigator.name", "trialId"
    )


    db.store_in_collection(
        "principalInvestigator.name", "conducted_trial", results_dict, final_collection
    )  ## or other collection
    """
