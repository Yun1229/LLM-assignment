from pymongo import UpdateOne, InsertOne


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
