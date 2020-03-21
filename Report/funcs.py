import re

def fetch_grade(grade_str: str):
    """
    Returns grade int from grade str
    :param grade_str:
    :return:
    """

    return int(re.findall(r'\d+', grade_str)[0])