import LLM
import mongoDB as db
from pymongo.collection import Collection
from typing import Dict, Any
from config import api_key


def add_dict_pair(opkey: str, opvalue: str, results_dict: Dict[str, Any]):
    if opkey not in results_dict:
        results_dict[opkey] = []
    results_dict[opkey].append(opvalue)


# Function to process trials and extract conditions
def extract_info(collection: Collection, field: str, content: str) -> Dict[str, Any]:
    results_dict = {}

    for trial in collection.find({}):
        opkey = db.get_nested_value(trial, field)
        opvalue = db.get_nested_value(trial, content)
        if opvalue:
            if content == "eligibilityCriteria":
                inclusion_text = LLM.preprocess_text(opvalue)
                client = LLM.get_client(api_key=api_key)
                opvalue = LLM.LLM_model(client, inclusion_text)
            if isinstance(opkey, list):
                for opkeysingle in opkey:
                    add_dict_pair(opkeysingle, opvalue, results_dict)

            else:
                add_dict_pair(opkey, opvalue, results_dict)

    return results_dict
