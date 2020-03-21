from JournalParser.edutatarauth import edu_auth
from JournalParser.params import Params
from JournalParser.objects import SubjectTables, GlobalsContainer
from JournalParser.funcs import create_grade_to_link_dict as journal_gtl, get_initial_data
from Report.get_links import get_links, get_years
from Report.params import base_url
from Report.objects import \
    OverallTable, OverallQualitiesTable, OverallSubjectsTable, SubjectsQualitiesTable, GradePerformanceTable, \
    StudentsPerformanceTables
from Report.funcs import fetch_grade
from Report.excel import excelify_oqt, excelify_spt, excelify_sqt, excelify_bst
from bs4 import BeautifulSoup



def create_report(params, pBar, label):

    PARAMS = Params(params)
    START_GRADE = PARAMS.class1
    TERM = PARAMS.term1
    label.emit('Входим в аккаунт...')
    SESSION = edu_auth(PARAMS.login, PARAMS.password)
    label.emit('Успешный вход в аккаунт')
    SESSION.get(base_url)
    label.emit('Сбор нужных данных...')
    LINKS, YEAR_IDS = get_links(SESSION)


    YEARS = list(map(str, get_years(SESSION)))

    globals_cont = GlobalsContainer(SESSION, PARAMS, YEARS)


    def get_teachers_ids():
        """
        Fetches teachers ids from <select> on page 'Итоги успеваемости класса...'
        :return: list of ids
        """
        grades_perf_url = base_url + LINKS['Итоги успеваемости класса за учебный период'] + 'academic_year_id={}'.format(
            YEAR_IDS['this'])
        grades_perf_main_page = SESSION.get(grades_perf_url)
        grades_perf_main_page = BeautifulSoup(grades_perf_main_page.text, 'html.parser')
        options = grades_perf_main_page.find('select').findChildren()
        ids = [option['value'] for option in options if option.text.endswith(YEARS[0])]
        return ids


    def get_grade_and_link(teacher_id, term, crop):
        """
        Finds grade number and a link to required table from a page with teacher_id
        :return: (grade_str, raw_page)
        """
        URL = base_url + LINKS['Итоги успеваемости класса за учебный период']
        url = URL + 'worker_id={}'.format(teacher_id)
        r = SESSION.get(url)

        empty_grade_page = BeautifulSoup(r.text, 'html.parser')
        div = empty_grade_page.find('div', {'class': 'h'})

        labels = div.find_all('label')


        label_texts = [label.nextSibling.strip() for label in labels]

        grade_str = label_texts[-3]

        if crop and (fetch_grade(grade_str) not in range(crop[0], crop[1] + 1)):
            return

        st_year = label_texts[-4]

        label_texts = label_texts[:-4]

        row_ind = 0

        for i in range(1, len(label_texts), 2):
            if label_texts[i] == st_year and label_texts[i + 1] == grade_str:
                row_ind = i
                break

        grade_row = labels[row_ind]

        a = grade_row.find_next('a')
        required_a_text = '{} полугодие'.format(term // 4 + 1) if grade_str.startswith(
            ('10', '11')) else '{} четверть'.format(term)

        a_text = a.text.strip()
        while a_text != required_a_text:
            try:
                a = a.find_next('a')
                a_text = a.text.strip()
            except AttributeError:
                print('Не получилось найти ссылку на четверть/полугодие в {} классе'.format(grade_str))
                print(url)

        required_journal_link = URL + a['href']

        return grade_str, required_journal_link


    def create_grade_to_link_dict(teacher_ids, term, crop=None):
        """
        Creates a sorted dict with required tables' links sorted by grade
        :param teacher_ids:
        :param term: required term's number
        :param crop: arr of needed grades. Default is None (all grades needed)
        :return: dict {grade1: link1, ..., gradeN: linkN}
        """
        grade_and_link = {}
        for id_ in teacher_ids:
            ret = get_grade_and_link(id_, term=term, crop=crop)
            if ret:
                grade, link = ret
                grade_and_link[grade] = link
        grade_and_link = {grade: link for grade, link in sorted(grade_and_link.items(), key=lambda item: int(item[0][:-1]))}
        return grade_and_link


    def stringify_params(**kwargs):
        """
        Creates string of type 'key=value&' to put in into URL
        :param kwargs: query params
        :return: string
        """
        s = ''
        for key, val in kwargs.items():
            s += '{}={}&'.format(key, val)

        s = s.rstrip('&')
        return s


    def get_overall_page(**kwargs):
        """
        Returns page 'Результативность работы школы за учебный период/год" with given params
        :param kwargs: query params
        :return: response text (html)
        """
        url = base_url
        if kwargs.get('academic_year_id', YEAR_IDS['this']) == YEAR_IDS['past']:
            url += LINKS['Результативность работы школы за учебный год']
        else:
            url += LINKS['Результативность работы школы за учебный период']

        url += stringify_params(**kwargs)
        r = SESSION.get(url)

        return r.text


    def get_overall_subjects_page(**kwargs):
        """
        Returns page 'Результативность работы школы (по предметам) за учебный период/год" with given params
        :param kwargs: query params
        :return: response text (html)
        """
        url = base_url
        if kwargs.get('academic_year_id', YEAR_IDS['this']) == YEAR_IDS['past']:
            url += LINKS['Результативность работы школы (по предметам) за учебный год']
        else:
            url += LINKS['Результативность работы школы (по предметам) за учебный период']

        url += stringify_params(**kwargs)
        r = SESSION.get(url)

        return r.text


    def check_ovrls(table):
        """
        Finds students whose overall is less than 3
        :param html:
        :return: list: [[name1, overall1], ..., [nameN, overallN]]
        """
        w = []


        rows = table.find('tbody').find_all('tr')

        for row in rows:
            cells = row.find_all('td')
            try:
                avg_m = cells[-2].text.strip().replace(',', '.')
                avg_m = float(avg_m)

                if avg_m < 3:
                    name = cells[1]
                    name = ' '.join(w.strip() for w in name.text.split()[:2])
                    w.append([name, avg_m])
            except (IndexError, ValueError):
                pass

        return w

    """
    Helpers are above
    Main funcs are below
    """
    #TODO:
    # simplify funcs below

    def create_report_from_overall_table():
        """
        Creates .xlsx from 'Результативность работы школы за учебный период/год' depending on the term number
        :return:
        """
        if TERM == 1:
            first_term_overall_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            first_term_overall_table = OverallTable(first_term_overall_page)
            ft_quals = first_term_overall_table.qualities

            past_year_overall_page = get_overall_page(academic_year_id=YEAR_IDS['past'])
            past_year_overall_table = OverallTable(past_year_overall_page, past_year=True, crop=[START_GRADE, 8])
            py_quals = past_year_overall_table.qualities

            quals_table = OverallQualitiesTable(ft_quals, py_quals)
            quals_table.header = ['Класс', 'Прошлый уч.год, %', '1 четверть, %', 'Динамика, %']

            excelify_oqt(total=(first_term_overall_table, quals_table), pred=(past_year_overall_table,))

        elif TERM == 2:
            second_term_overall_page_young = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4,
                                                              term_number=2)
            second_term_overall_table = OverallTable(second_term_overall_page_young)

            second_term_overall_page_old = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=1)
            second_term_overall_table_old = OverallTable(second_term_overall_page_old)

            second_term_overall_table.merge_tables(second_term_overall_table_old)  # create one table from 6-9 and 10-11
            st_y_o_quals = second_term_overall_table.qualities

            first_term_overall_page_young = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4,
                                                             term_number=1)
            first_term_overall_table = OverallTable(first_term_overall_page_young)

            past_year_overall_page = get_overall_page(academic_year_id=YEAR_IDS['past'])
            past_year_overall_table_old = OverallTable(past_year_overall_page, crop=[9, 10], past_year=True)

            first_term_overall_table.merge_tables(past_year_overall_table_old)  # merge 1 term 6-9 and past year 10-11 to one table
            ft_y_o_quals = first_term_overall_table.qualities

            quals_table = OverallQualitiesTable(st_y_o_quals, ft_y_o_quals)
            quals_table.header = ['Класс', '1 четверть/Прошлый год, %', '2 четверть/1 полугодие, %', 'Динамика, %']

            excelify_oqt(total=(second_term_overall_table, quals_table), term1=(first_term_overall_table,))

        elif TERM == 3:

            t3_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=3)
            t3_table = OverallTable(t3_page)
            t3_quals = t3_table.qualities

            t2_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            t2_table = OverallTable(t2_page)
            t2_quals = t2_table.qualities

            t1_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            t1_table = OverallTable(t1_page)
            t1_quals = t1_table.qualities

            quals_table = OverallQualitiesTable(t3_quals, t2_quals, t1_quals)
            quals_table.header = ['Класс', '1 четверть, %', '2 четверть, %', '3 четверть, %', 'Динамика, %']

            excelify_oqt(total=(t3_table, quals_table), term2=(t2_table,), term1=(t1_table,))

        else:
            t4_page_y = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=4)
            t4_table = OverallTable(t4_page_y)

            t4_page_o = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=2)
            t4_table.merge_tables(OverallTable(t4_page_o))
            t4_quals = t4_table.qualities

            t3_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=3)
            t3_table = OverallTable(t3_page)
            t3_quals = t3_table.qualities

            t2_page_y = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            t2_table = OverallTable(t2_page_y)

            t2_page_o = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=1)
            t2_table.merge_tables(OverallTable(t2_page_o))
            t2_quals = t2_table.qualities

            t1_page = get_overall_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            t1_table = OverallTable(t1_page)
            t1_quals = t1_table.qualities

            quals_table = OverallQualitiesTable(t4_quals, t3_quals, t2_quals, t1_quals)
            quals_table.header = ['Класс', '1 четверть, %', '2 четверть, %', '3 четверть, %', '4 четверть, %', 'Динамика, %']

            excelify_oqt(total=(t4_table, quals_table), term3=(t3_table,), term2=(t2_table,), term1=(t1_table,))

    def create_report_from_overall_subj_table():
        """
        Creates .xlsx from 'Результативность работы школы (по предметам) за учебный период/год'
        :return:
        """
        if TERM == 1:
            first_term_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            first_term_table_young = OverallSubjectsTable(first_term_page)
            ft_quals = first_term_table_young.qualities

            prev_year_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['past'])
            prev_year_table = OverallSubjectsTable(prev_year_page, crop=[START_GRADE, 8], past_year=True)
            py_quals = prev_year_table.qualities

            qualities = SubjectsQualitiesTable(ft_quals, py_quals)
            qualities.header = ['Класс', 'Прошлый год', '1 четверть', 'Динамика']

            excelify_sqt(po_predm=(first_term_table_young, qualities), pred=(prev_year_table,))

        elif TERM == 2:
            second_term_page_young = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            second_term_table_young = OverallSubjectsTable(second_term_page_young)

            second_term_page_old = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=1)
            second_term_table_old = OverallSubjectsTable(second_term_page_old)
            second_term_table_young.merge_tables(second_term_table_old)
            st_quals = second_term_table_young.qualities

            first_term_page_young = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            first_term_table_young = OverallSubjectsTable(first_term_page_young)

            prev_year_page_old = get_overall_subjects_page(academic_year_id=YEAR_IDS['past'])
            prev_year_table_old = OverallSubjectsTable(prev_year_page_old, crop=[9, 10], past_year=True)
            first_term_table_young.merge_tables(prev_year_table_old)
            ft_quals = first_term_table_young.qualities

            qualities = SubjectsQualitiesTable(st_quals, ft_quals)
            qualities.header = ['Класс', '1 четверть', '2 четверть', 'Динамика']

            excelify_sqt(po_predm=(second_term_table_young, qualities), pred=(first_term_table_young,))


        elif TERM == 3:
            t1_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            t1_table = OverallSubjectsTable(t1_page)
            t1_quals = t1_table.qualities

            t2_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            t2_table = OverallSubjectsTable(t2_page)
            t2_quals = t2_table.qualities

            t3_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=3)
            t3_table = OverallSubjectsTable(t3_page)
            t3_quals = t2_table.qualities

            qualities = SubjectsQualitiesTable(t3_quals, t2_quals, t1_quals)
            qualities.header = ['Класс', '1 четверть', '2 четверть', '3 четверть', 'Динамика']

            excelify_sqt(po_predm=(t3_table, qualities), term2=(t2_table,), term1=(t1_table,))


        else:
            t1_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=1)
            t1_table = OverallSubjectsTable(t1_page)
            t1_quals = t1_table.qualities

            t2_page_y = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            t2_table = OverallSubjectsTable(t2_page_y)
            t2_page_o = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=1)
            t2_table.merge_tables(OverallSubjectsTable(t2_page_o))
            t2_quals = t2_table.qualities

            t3_page = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=3)
            t3_table = OverallSubjectsTable(t3_page)
            t3_quals = t2_table.qualities

            t4_page_y = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=4, term_number=2)
            t4_table = OverallSubjectsTable(t4_page_y)
            t4_page_o = get_overall_subjects_page(academic_year_id=YEAR_IDS['this'], terms_count=2, term_number=2)
            t4_table.merge_tables(OverallSubjectsTable(t4_page_o))

            t4_quals = t4_table.qualities

            qualities = SubjectsQualitiesTable(t4_quals, t3_quals, t2_quals, t1_quals)
            qualities.header = ['Класс', '1 четверть', '2 четверть', '3 четверть', '4 четверть', 'Динамика']

            excelify_sqt(po_predm=(t4_table, qualities), term3=(t3_table,), term2=(t2_table,), term1=(t1_table,))

    def create_report_from_grade_overall():
        """
        Creates .xlsx from 'Итоги успеваемости класса за учебный период'
        :return:
        """
        teacher_ids = get_teachers_ids()

        if TERM == 1:
            gr_to_link = create_grade_to_link_dict(teacher_ids, term=1, crop=[START_GRADE, 9])
            data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in gr_to_link.items()}
            tables = StudentsPerformanceTables(data)
            tables.header_for_exc = ['Класс', '1 четверть']
            tables.header_for_count = ['Класс', '1 четверть']

            excelify_spt(tables)

        elif TERM == 2:

            second_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=2)

            st_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in second_term_gr_to_link.items()}

            first_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=1, crop=[START_GRADE, 9])

            ft_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in first_term_gr_to_link.items()}

            tables = StudentsPerformanceTables(st_data, ft_data)

            tables.header_for_exc = ['Класс', '1 четверть', '', '2 четверть', '']
            tables.header_for_count = ['Класс', '1 четверть', '2 четверть', 'Динамика']

            excelify_spt(tables)

        elif TERM == 3:
            t3_gr_to_link = create_grade_to_link_dict(teacher_ids, term=3, crop=[START_GRADE, 9])
            t3_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in t3_gr_to_link.items()}

            second_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=2, crop=[START_GRADE, 9])

            t2_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in second_term_gr_to_link.items()}

            first_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=1, crop=[START_GRADE, 9])

            t1_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in first_term_gr_to_link.items()}

            tables = StudentsPerformanceTables(t3_data, t2_data, t1_data)
            tables.header_for_exc = ['Класс', '1 четверть', '', '2 четверть', '', '3 четверть', '']
            tables.header_for_count = ['Класс', '1 четверть', '2 четверть', '3 четверть', 'Динамика']

            excelify_spt(tables)

        else:
            t4_gr_to_link = create_grade_to_link_dict(teacher_ids, term=4)
            t4_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in t4_gr_to_link.items()}

            t3_gr_to_link = create_grade_to_link_dict(teacher_ids, term=3, crop=[START_GRADE, 9])
            t3_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in
                       t3_gr_to_link.items()}

            second_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=2)

            t2_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in
                       second_term_gr_to_link.items()}

            first_term_gr_to_link = create_grade_to_link_dict(teacher_ids, term=1, crop=[START_GRADE, 9])

            t1_data = {grade: GradePerformanceTable(SESSION, SESSION.get(link).text) for grade, link in
                       first_term_gr_to_link.items()}

            tables = StudentsPerformanceTables(t4_data, t3_data, t2_data, t1_data)
            tables.header_for_exc = ['Класс', '1 четверть', '', '2 четверть', '', '3 четверть', '', '4 четверть', '']
            tables.header_for_count = ['Класс', '1 четверть', '2 четверть', '3 четверть', '4 четверть', 'Динамика']

            excelify_spt(tables)

    def find_bad_students():
        journal_grade_to_link = journal_gtl(SESSION, PARAMS)

        warns = []

        for grade, link in journal_grade_to_link.items():
            if not (TERM in (1, 3) and grade.startswith(('10', '11'))):
                grade_id, subj_to_id = get_initial_data(SESSION, link)

                for subj_name, id_ in subj_to_id.items():
                    label.emit(f'{grade} {subj_name}...')
                    table = SubjectTables(globals_cont, grade, PARAMS.term1, grade_id, subj_name, id_)
                    teacher = table.teacher

                    if table.raw_pages:
                        html_table = table.raw_pages[0]
                        ws = check_ovrls(html_table)

                        for w in ws:
                            warns.append([grade, *w, subj_name, teacher]) #[Класс, ФИО, балл, предмет, учитель]

        excelify_bst(warns)


    label.emit('Результативность работы школы за уч. период')
    create_report_from_overall_table()
    pBar.emit(25)
    label.emit('Результативность работы школы (по предм.) за уч. период')
    create_report_from_overall_subj_table()
    pBar.emit(50)
    label.emit('Отчеты кл. руководителей за уч. период')
    create_report_from_grade_overall()
    pBar.emit(75)
    label.emit('Ученики со средним баллом <3')
    find_bad_students()
    pBar.emit(100)
    label.emit('Завершено!')
