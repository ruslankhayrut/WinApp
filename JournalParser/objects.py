from bs4 import BeautifulSoup
from JournalParser.str_to_date import str_to_date
import datetime
import locale

locale.setlocale(locale.LC_ALL, '')

class GlobalsContainer:
    """
    Class that stores all the global variables and is passed to SubjectTables constructor
    """
    def __init__(self, SESSION, PARAMS, YEARS):
        self._SESSION = SESSION
        self._PARAMS = PARAMS
        self._YEARS = YEARS

    @property
    def SESSION(self):
        return self._SESSION

    @property
    def PARAMS(self):
        return self._PARAMS

    @property
    def YEARS(self):
        return self._YEARS

class SubjectTables:
    """
    Class for getting storing an exact subject's data: grade, term, teacher, html <table> to be handled later
    We only pass there session, term, subject id and grade id
    """
    def __init__(self, globals_cont: 'GlobalsContainer', grade, term, grade_id, subj_name, subj_id):
        self._SESSION, self._PARAMS, self._YEARS = globals_cont.SESSION, globals_cont.PARAMS, globals_cont.YEARS

        self.grade = grade
        self.term = term
        self.grade_id = grade_id
        self.subj_name = subj_name
        self.subj_id = subj_id

        self._first_page = self.__get_first_page()
        self.teacher = self.__get_teacher()
        self._last_page = self.__get_last_page()
        self.raw_pages = self.__get_raw_pages()

        self.dates = []

    def __get_first_page(self):
        """
        Gets subjects' first page to extract last page and teacher
        :return: BS4 instance
        """
        url = 'https://edu.tatar.ru/school/journal/school_editor?term={0}' \
              '&criteria={1}&edu_class_id={2}&' \
              'show_moved_pupils=0'.format(self.term, self.subj_id, self.grade_id)

        r = self._SESSION.get(url)
        page = BeautifulSoup(r.text, 'html.parser')

        return page

    def __get_teacher(self):
        """
        Extracts teacher's name from self._first_page
        :return: str or None if not found
        """
        teacher = self._first_page.find('div', {'class': 'line last'})
        if teacher:
            try:
                teacher = teacher.text.strip().split(maxsplit=1)[1]
                return teacher
            except IndexError:
                pass
        return

    def __get_last_page(self):
        """
        Tries to find a number of the last page of subject's journal
        :return: int
        """

        if self._PARAMS.only_term:
            last_page = 1
        else:
            pages = self._first_page.find('p', {'class': 'pages'})

            if pages:
                pages = [p for p in pages.text.split() if (p.isdigit() or p == '>>')]
                if pages[-1] != '>>':
                    last_page = int(pages[-1])
                else:
                    r = self._SESSION.get('https://edu.tatar.ru/school/journal/school_editor?term={0}' \
                                    '&criteria={1}&edu_class_id={2}&' \
                                    'show_moved_pupils=0&page={3}'.format(self.term, self.subj_id, self.grade_id,
                                                                          int(pages[-2]) + 1))
                    html = BeautifulSoup(r.text, 'html.parser')
                    pages = html.find('div', {'class': 'pages'})
                    pages = [p for p in pages.text.split() if p.isdigit()]
                    last_page = int(pages[-1])
            else:
                last_page = 1
        return last_page

    def __get_raw_pages(self):
        """
        Collects BS4 <table> instances for each subject journal's page.
        If teacher doesn't exist returns empty list

        :return: list [table1, ..., table(LASTPAGE)]
        """
        if not self.teacher:
            return []

        tables = []
        for page_num in range(1, self._last_page + 1):
            url = 'https://edu.tatar.ru/school/journal/school_editor?term={0}' \
                  '&criteria={1}&edu_class_id={2}&' \
                  'show_moved_pupils=0&page={3}'.format(self.term, self.subj_id, self.grade_id, page_num)

            r = self._SESSION.get(url)
            page = BeautifulSoup(r.text, 'html.parser')
            table = page.find('table', {'class': 'table'})



            if self.__check_date(table):
                break

            tables.append(table)

        return tables

    def __check_date(self, table):
        """
        Checks whether table's last column date is bigger that today. Not to fetch extra empty tables from the future
        :param table: BS4 Page element
        :return: True if last column date is bigger than today else False
        """
        table_year = self._YEARS[self.term // 2] if self.grade.startswith(('10', '11')) else self._YEARS[self.term // 3]  # calendar year of the table
        header = table.find('thead')
        month_row = header.find_next('tr')
        date_row = month_row.find_next('tr')

        last_month = month_row.find_all('td')[-3].text.strip()
        last_date = int(date_row.find_all('td')[-1].text.strip())

        last_col_date = str_to_date(last_date, last_month, table_year)

        if last_col_date > datetime.date.today():

            return True
        return False

class Warnings:
    """
    Checks BS4 <table> instances in SubjectsTable and returns lists of warnings
    """
    def __init__(self, globals_cont: 'GlobalsContainer', subj_table: 'SubjectTables'):
        self._PARAMS, self._YEARS = globals_cont.PARAMS, globals_cont.YEARS
        self._subject_table = subj_table

        self.subject = self._subject_table.subj_name
        self.teacher = self._subject_table.teacher
        self.term = self._subject_table.term

        self.warnings = self.__check()

    def __check(self):
        """
        Performs needed checks with all the SubjectTables <table>s
        :return: global list of warnings
        """

        if self._PARAMS.only_term: #don't do deep check if we need to check only term marks
            tm_warns = self.__check_term_marks(self._subject_table.raw_pages[0])
            return tm_warns


        all_data = self.__merge_all_tables()
        warnings = self.__deepcheck(all_data)

        return warnings

    def __merge_all_tables(self):
        """
        Extracts dates, lesson_types, marks etc from <table>s given into one dict. And removes dates from the future
        :return:
        """
        super_dict = {
            'dates': [],
            'lesson_types': [],
            'lesson_metas': [], #optional
            'marks': [] #optional
        }

        for table in self._subject_table.raw_pages:
            new_dates = self.__create_dates(table)
            super_dict['dates'] += new_dates #dates needed anyway

            crop = len(new_dates)

            l_types, l_metas = self.__extract_lesson_types_and_metas(table)
            super_dict['lesson_types'] += l_types[:crop] #types may be needed while marks checking, so collect them too

            if l_metas:
                super_dict['lesson_metas'] += l_metas[:crop] #optional

            if (self._PARAMS.check_lessons_fill or self._PARAMS.check_students_fill or self._PARAMS.check_double_two): #collect marks only if they're needed
                if not super_dict['marks']:
                    super_dict['marks'] = [row[:crop] for row in self.__extract_marks(table)]
                else:
                    new_rows = self.__extract_marks(table)
                    for row_old, row_new in zip(super_dict['marks'], new_rows):
                        row_old += row_new[:crop]

        return super_dict

    def __check_term_marks(self, table):
        """
        Checks whether term marks correspond to averages
        :param table:
        :return: list of warnings
        """
        tm_warns = []
        rows = table.find('tbody').find_all('tr')

        counter = 1 #this is just to count row number
        for row in rows:
            cells = row.find_all('td')

            term_m = cells[-1].text.strip()

            if term_m.isdigit():
                term_m = int(term_m)
                avg_m = cells[-2].text.strip().replace(',', '.')
                try:
                    avg_m = float(avg_m)

                    if not self.__avg_and_term_compare(avg_m, term_m):
                        tm_warns.append(['Несоответствие средней и четвертной оценок. Строка {}'.format(counter)])

                except ValueError:
                    tm_warns.append(['Нет среднего балла. Строка {}'.format(counter)])
            else:
                tm_warns.append(['Нет четвертной оценки. Строка {}'.format(counter)])

            counter += 1

        return tm_warns

    def __avg_and_term_compare(self, average: float, term: int):
        """
        Checks whether average mark correspond to term mark
        :param average:
        :param term:
        :return: True if correspond else False
        """
        if average >= self._PARAMS.min_for_5 and term != 5:
            return False

        elif self._PARAMS.min_for_4 <= average < self._PARAMS.min_for_5 and term != 4:
            return False

        elif self._PARAMS.min_for_3 <= average < self._PARAMS.min_for_4 and term != 3:
            return False

        return True

    def __create_dates(self, table):
        """
        Creates datetime.date 's from table string dates
        :param table:
        :return: list of datetime.date() instances. It's cropped if there're dates from the future
        """
        header = table.find('thead')
        months_row = header.find_next('tr')
        dates_row = months_row.find_next('tr')

        months = {cell.text: int(cell['colspan']) for cell in months_row.find_all('td') if 'colspan' in cell.attrs}
        dts = dates_row.find_all('td')

        datenums = []
        for date in dts:
            joint = int(date['colspan'])
            datenums += [int(date.text)] * joint

        for name, count in months.items():
            months[name] = datenums[:count]
            datenums = datenums[count:]


        dates = []

        for name, date_nums in months.items():
            for day_num in date_nums:
                date = str_to_date(day_num, name, self._YEARS[self.term // 2] if self._subject_table.grade.startswith(('10', '11')) else self._YEARS[self.term // 3])

                if date > datetime.date.today():
                    return dates

                dates.append(date)

        return dates

    def __extract_lesson_types_and_metas(self, table):
        """
        Extracts type and task/HW from table header
        :param table:
        :return: list of types [type1, ...typeN], list of metas [(topic1, task1), ..., (topicN, taskN)]
        """
        header = table.find('thead')

        types = []
        metas = []

        lessons_row = header.find_all('tr')[-1]
        for lesson in lessons_row.find_all('td'):
            types.append(lesson.text.strip())

            if self._PARAMS.check_meta:
                try:
                    meta = lesson.get('title')
                    if meta:
                        meta = True
                except AttributeError:
                    meta = False

                metas.append(meta)

        return types, metas

    def __extract_marks(self, table):
        """
        Extracts marks rows
        :param table:
        :return: list of mark rows(lists)
        """
        marks_rows = []
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            marks_row = [cell.text.strip() for cell in cells[2: -2]]
            marks_rows.append(marks_row)

        return marks_rows

    def __deepcheck(self, all_data: dict):
        """
        Performs checking according to all the parameters listed
        :param all_data:
        :return: list of warnings
        """


        l_types = all_data.get('lesson_types', [])
        l_metas = all_data.get('lesson_metas', [])
        marks = all_data.get('marks', [])
        self.dates = all_data.get('dates', []) #make a property

        warns = []

        if self._PARAMS.check_RO:
            warns += self.__check_RO(l_types)

        if self._PARAMS.check_meta:
            warns += self.__check_meta(l_metas)

        if marks:
            warns += self.__check_marks(l_types, marks)

        if self._PARAMS.check_term_marks:
            warns += self.__check_term_marks(self._subject_table.raw_pages[0])

        return warns

    def __check_RO(self, l_types: list):
        """
        Checks 'После КР или Д должна быть РО'
        :param l_types:
        :return: warnings: list of lists[text, date]
        """
        w = []
        for i in range(len(l_types)):
            try:
                if (l_types[i] in self._PARAMS.CONTROL_WORKS and l_types[i+1] != 'РО'):
                    w.append(['После КР или Дикт. не работа над ошибками', datetime.datetime.strftime(self.dates[i], '%d %B')])
            except IndexError:
                pass

        return w

    def __check_meta(self, l_metas: list):
        """
        Checks 'Заполнены ли темы уроков и дз'
        :param l_meta:
        :return: warnings: list of lists[text, date]
        """
        w = []
        for i in range(len(l_metas)):
            if not l_metas[i]:
                w.append(['Нет темы урока или ДЗ', datetime.datetime.strftime(self.dates[i], '%d %B')])

        return w

    def __check_marks(self, l_types: list, marks: list):
        w = []

        lessons_count = len(marks[0])
        if self._PARAMS.check_students_fill or self._PARAMS.check_double_two:

            for i in range(len(marks)):
                row = marks[i]
                if self._PARAMS.check_students_fill:
                    marks_count = len([m for m in row if m in self._PARAMS.STR_MARKS])
                    if round(marks_count / lessons_count, 2) < round(self._PARAMS.term_percent / 100, 2):
                        w.append([f'У ученика мало оценок за четверть. Строка {i}'])

                if self._PARAMS.check_double_two:
                    for j in range(len(row)):
                        try:
                            if row[j] == '2' and row[j+1] == '2':
                                w.append(['Две двойки подряд', datetime.datetime.strftime(self.dates[j], '%d %B')])
                        except IndexError:
                            pass

        if self._PARAMS.check_lessons_fill:
            for i in range(lessons_count):
                l_type = l_types[i]
                col = [row[i] for row in marks]
                students_count = len(col)

                if l_type in self._PARAMS.MARKS_COL_TYPES and not (l_type == 'ПР' and self.subject.startswith(self._PARAMS.allowed_not_row)):
                    if col.count('') and self.dates[i] + datetime.timedelta(days=8) < datetime.date.today():
                        w.append(['Должен быть ряд оценок', datetime.datetime.strftime(self.dates[i], '%d %B')])

                else:
                    if round(col.count('') / students_count, 2) > 1 - round(self._PARAMS.lesson_percent / 100, 2):
                        if l_type in ('Р', 'П'):
                            if self.dates[i] + datetime.timedelta(days=8) < datetime.date.today():
                                w.append(['Мало оценок за урок', datetime.datetime.strftime(self.dates[i], '%d %B')])
                        else:
                            w.append(['Мало оценок за урок', datetime.datetime.strftime(self.dates[i], '%d %B')])

        return w


