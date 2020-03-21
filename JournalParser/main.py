""""Author: Ruslan Khairutdinov onsunday1703@gmail.com"""

from JournalParser.edutatarauth import edu_auth
from JournalParser.params import Params
from JournalParser.objects import SubjectTables, GlobalsContainer, Warnings
from JournalParser.excel import excelify
from JournalParser.funcs import get_years, create_grade_to_link_dict, get_initial_data



def execute(PARAMS, pBar, label):
    PARAMS = Params(PARAMS)

    SESSION = edu_auth(PARAMS.login, PARAMS.password)
    SESSION.get('https://edu.tatar.ru')
    label.emit('Успешный вход в аккаунт')

    YEARS = get_years(SESSION)
    label.emit('Сбор нужных данных...')
    global_vars = GlobalsContainer(SESSION, PARAMS, YEARS)

    grades_to_link = create_grade_to_link_dict(SESSION, PARAMS)

    grades_count = len(grades_to_link.keys())
    grade_val = 95 / (grades_count if grades_count else 1)#each grade's value in progress

    data = {}

    v = 0
    for grade, link in grades_to_link.items():
        grade_id, subj_to_id = get_initial_data(SESSION, link)

        data[grade] = {}

        subjs_count = len(subj_to_id.keys())
        subj_value = grade_val / (subjs_count if subjs_count else 1)   # each subjs value in grade's value

        for subj_name, id_ in subj_to_id.items():
            data[grade][subj_name] = []

            if grade.startswith(('10', '11')):
                terms_range = range(1, PARAMS.term2 // 3 + 2)
            else:
                terms_range = range(PARAMS.term1, PARAMS.term2 + 1)

            for term in terms_range:
                label.emit(f'{grade} {subj_name} {term} четверть...')
                grade_subj_term_tables = SubjectTables(global_vars, grade, term, grade_id, subj_name, id_)

                if grade_subj_term_tables.raw_pages:
                    data[grade][subj_name].append(Warnings(global_vars, grade_subj_term_tables))

            if not data[grade][subj_name]:
                data[grade].pop(subj_name) #remove subj with no Warnings instance

            v += subj_value
            pBar.emit(v)
    """
    Here we should get
    data = {grade1: {subj1: [Warnings1t, Warnings2t, ...]}, ... subjN: Warnings}, ..., gradeN: {...}}
    """
    excelify(data, PARAMS.group_by)
    pBar.emit(100)
