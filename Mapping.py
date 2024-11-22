import nestedField as nf


### Functions for data mapping
def get_date(study):
    start = nf.get_nested_value(
        study, "protocolSection.statusModule.startDateStruct.date"
    )

    end = nf.get_nested_value(
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
    phase = nf.get_nested_value(study, "protocolSection.designModule.phases")

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
    overall_officials = nf.get_nested_value(
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
    locations = nf.get_nested_value(
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
        "trialId": nf.get_nested_value(
            study, "protocolSection.identificationModule.nctId"
        ),
        "title": nf.get_nested_value(
            study, "protocolSection.identificationModule.officialTitle"
        ),
        "startDate": get_date(study)[0],
        "endDate": get_date(study)[1],
        "phase": get_phase(study),
        "principalInvestigator": get_principal_investigator(study),
        "locations": get_locations(study),
        "eligibilityCriteria": nf.get_nested_value(
            study, "protocolSection.eligibilityModule.eligibilityCriteria"
        ),
    }


def map_data(input_data):
    transformed_data = []
    for study in input_data["studies"]:
        transformed_data.append(transform_study(study))
    return transformed_data
