import re
from bs4 import BeautifulSoup
import datetime


def create_grade_to_link_dict(SESSION, PARAMS):
    """
    Creates dict of type {grade1: link_to_journal, ..., gradeN: link_to_journal} handling only selected grades
    :return: dict {str: str}
    """
    d = {}
    for class_num in range(PARAMS.class1, PARAMS.class2 + 1):
        r = SESSION.get('https://edu.tatar.ru/school/journal/select_edu_class?number={}'.format(class_num))
        soup = BeautifulSoup(r.text, 'html.parser')

        grades = []
        links_to_journal = []

        lis = soup.find('div', {'class': 'h'}).find_all('li')

        for li in lis:
            grade = li.text.split('\t', maxsplit=1)[0]
            grades.append(grade)

        for tag in soup.find_all('a', href=True):
            if tag.text == 'Журнал класса':
                links_to_journal.append(tag['href'])

        d.update(dict(zip(grades, links_to_journal)))
    return d


def get_initial_data(SESSION, link_to_grade):
    """
    Gets grade id and list of subject ids for exact grade
    :return grade_id, subjects_ids: list
    """
    grade_id = re.findall(r'\d+', link_to_grade)[0]
    r = SESSION.get(link_to_grade)
    init_page = BeautifulSoup(r.text, 'html.parser')

    subject_ids = get_subjects_ids(init_page)

    return grade_id, subject_ids


def get_subjects_ids(html):
    """
    Collects subjects' ids and name from grade's tables initial page. Excluding 'Электив'.
    The're to be used for subjects changing
    (url -> 'criteria=' parameter)
    :param html:
    :return: dict: {subj1: id, ..., subjN: id}
    """
    subject_to_id = {}
    for option in html.find('select', id='criteria').find_all(name='option'):  # extract subject values to get tables
        id_ = option['value']
        name = option.text.split('/')[1]
        name = name.strip().replace('\xa0', ' ')
        if not name.startswith('Электив'):
            subject_to_id.update({name: id_})

    return subject_to_id


def get_years(SESSION):
    """
    Fetches this schoolyear eg 2019/2020
    :return: list: int [year1, year2]
    """
    r = SESSION.get('https://edu.tatar.ru/school')
    html = BeautifulSoup(r.text, 'html.parser')

    h3 = html.find('h3')
    years = list(map(int, re.findall(r'\d+', h3.text)))

    return years
