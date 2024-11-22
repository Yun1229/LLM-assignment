from typing import List, Dict, Any, Union


def flatten(arg: List[str]) -> List[str]:
    if not isinstance(arg, list):  # if not list
        return [arg]
    return [x for sub in arg for x in flatten(sub)]


def get_nested_value(
    data: Dict[str, Union[str, List[str]]], keys2: str
) -> Union[str, List[str]]:
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
