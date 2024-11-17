# Clinical Trials Data Pipeline
This repository contains a pipeline that retrieves data from ClinicalTrials.gov, transforms and stores it in MongoDB, and applies LLM to extract diseases/conditions from eligibility criteria.

## Features
* Uses the ```pytrials``` library to fetch clinical trials data from ClinicalTrials.gov.
* Maps raw data into a structured json schema.
* MongoDB
  * Creates collections with JSON schema validation.
  * Supports upsert operations for bulk data.
* LLM
  * Applies ```gpt-4o-mini``` model via OpenAI’s API, with key provided by AcademicLab.
  * Extracts the diseases/conditions mentioned in the inclusion criteria in the unstructured eligibilityCriteria field in each study.
* Supports saving and loading intermediate results with ```pickle```.

### Dependencies
* Python (v3.8+)
* MongoDB: A running MongoDB instance (default connection: localhost:27017)
* ```pytrials```
* ```pymongo```
* ```openai```
* ```pickle```

### Setup
1. Configure API Keys
   Add your OpenAI API key to a config.py file: ```api_key = "your_openai_api_key"```
2. Run the Script
   Ensure MongoDB is running and execute the script:```python build_db.py```

### Additional Files in the Project
* ```requirements.txt```: a list of  python dependencies.
* ```schema.json```: the JSON schema used to validate the MongoDB collection.
* ```API.pynb```: the Jupyter notebook of the build_db.py.
* ```retrieved_studies.pkl```: store the retrieved studies from ClinicalTrials.gov.
* ```mapped_data_all.pkl```: store the mapped data from the retrieved studies.
* ```results_dict.pkl```: store the LLM extracted diseases/conditions of each study.
