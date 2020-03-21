from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from .funcs import fetch_grade
import locale

locale.setlocale(locale.LC_ALL, '')


class Table(ABC):
    """
    A template for the future tables
    """
    def __init__(self, raw_page):
        self.raw_page = BeautifulSoup(raw_page, 'html.parser')

    @staticmethod
    def extract_data(data: str):
        """
        Exctacts int, float or str from data of type string
        :param data: string
        :return: number if possible or string
        """
        if data.isdigit():
            return int(data)
        elif not data:
            return ''
        try:
            data = data.rstrip('%').replace(',', '.')
            return float(data)
        except ValueError:
            return data

    @staticmethod
    def increment_grade(grade_string: str):
        """
        Increases grade string by 1. Used if the grade is taken from the past year table. E.g. 8A -> 9A
        :param grade_string:
        :return: increased_grade_string
        """
        try:
            n, letter = fetch_grade(grade_string), grade_string[-1]
            new_grade_string = '{}{}'.format(n + 1, letter)
            return new_grade_string
        except (ValueError, IndexError):
            return grade_string

    @property
    @abstractmethod
    def data(self):
        return NotImplementedError('Table should have a data')

    @property
    @abstractmethod
    def header(self):
        return NotImplementedError('Table must have a header')


class OverallTable(Table):
    """
    Table 'Результаты работы школы за учебный период/год'.
    """
    def __init__(self, raw_page: str, crop: list = None, past_year: bool = False):
        super().__init__(raw_page)
        self._table = self.raw_page.find('table')
        self.crop = crop
        self.past_year = past_year

        self._header = self.__get_header()
        self._data = self.__get_data()
        self._grades = self.__get_grades()
        self._qualities = self.__get_qualities()

    @property
    def header(self):
        return self._header

    @property
    def data(self):
        return self._data

    @property
    def grades(self):
        return self._grades

    @property
    def qualities(self):
        return self._qualities


    def __get_header(self):
        """
        Gets table header from <thead>
        :return: list of column names
        """
        head = [td.text.strip() for td in self._table.find_next('thead').find_next('tr').findChildren()]
        del head[2]

        return head


    def __get_data(self):
        """
        Returns numeric matrix with grades column slicing the last row
        :return: [[grade1, val1, val2, ..., valN], ..., [gradeN, ..., valN]]
        """

        data_table = []
        table = self._table.find_next('tbody').find_all_next('tr')

        if self.crop:
            start_grade, finish_grade = self.crop[0], self.crop[1]  # int
            allowed_st = [str(n) for n in range(start_grade, finish_grade + 1)]
            allowed_st += ['итог', '5-9']
            allowed_st = tuple(allowed_st)

            started = False
            st_index = end_index = 0
            for i in range(len(table[:-1])):
                row = table[i]
                data_row = [self.extract_data(td.text.strip()) for td in row.find_all('td')][:-3]
                grade = data_row[0]
                if not started and grade.startswith(str(start_grade)):
                    started = True
                    st_index = i
                elif started and not grade.startswith(allowed_st):
                    end_index = i
                    break

            for row in table[st_index: end_index]:
                data_row = [self.extract_data(td.text.strip()) for td in row.find_all('td')][:-3]
                del data_row[2]
                data_table.append(data_row)

        else:
            for row in table[:-1]:
                data_row = [self.extract_data(td.text.strip()) for td in row.find_all('td')][:-3]
                del data_row[2]
                data_table.append(data_row)

        if self.past_year: #increment grade from the past year
            for row in data_table:
                row[0] = self.increment_grade(row[0])

        return data_table


    def __get_grades(self):
        """
        Collects grades str
        :return: [grade1, grade2, ..., gradeN]
        """
        grades = []
        for row in self.data:
            grade_string = row[0]
            if grade_string.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')) and len(grade_string) in (2, 3):
                grades.append(grade_string)
        return grades


    def __get_qualities(self):
        """
        Makes a dict -> grade: [qual]
        :return: {grade1: [qual1], ..., gradeN: [qualN]}
        """

        grades, data = self.grades, self.data
        cleaned_data = [[row[3]] for row in data if row[0] in grades]

        quals = dict(zip(grades, cleaned_data))

        return quals

    def merge_tables(self, *tables: 'OverallTable'):
        """
        Extends this table adding other OverallTable's data and qualities to this table's fields.
        *tables must be OverallTable instances. E.g. if you need to merge 6-9 and 10-11 OverallTables.
        """
        for table in tables:
            if isinstance(table, OverallTable):
                self._data += table.data
                self._qualities.update(table.qualities)
                self._grades += table.grades
            else:
                raise TypeError('Table {} must be OverallTable instance, got {}'.format(tables.index(table), type(table)))


class OverallQualitiesTable(Table):
    """
    Creates qualities table from Overall tables. Dicts are to be placed from newer to older
    """
    def __init__(self, *dicts: dict, raw_page=''):
        super().__init__(raw_page)
        self.dicts = dicts
        self._data = self.__create_quals_table()
        self._header = []

    def __create_quals_table(self):
        """
        Creates table of qualities from several qualities dicts.
        :return [grade, qualN-k-1, qualN-k, ..., qualN]. Quals are sorted from older to newer
        """
        super_dict = self.dicts[0] #set last term's quals as super

        for d in self.dicts[1:]:
            for key in super_dict.keys():
                super_dict[key] += d.get(key, ['н/д'])

        data_table = [[key, *reversed(val)] for key, val in super_dict.items()]

        for row in data_table:
            try:
                row.append(row[-1] - row[-2])
            except TypeError:
                row.append('н/д')

        return data_table

    @property
    def data(self):
        return self._data

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, value: list):
        self._header = value

    @header.deleter
    def header(self):
        self._header = []


class OverallSubjectsTable(Table):
    def __init__(self, raw_page, crop=None, past_year=False):
        super().__init__(raw_page)
        self._table = self.raw_page.find('table', {'class': 'table no-print'})
        self.crop = crop
        self.past_year = past_year

        self._header = self.__get_header()
        self._subjects = self.__get_subjects()
        self._data = self.__get_data()
        self._grades = self.__get_grades()
        self._qualities = self.__get_qualities()

    def __get_header(self):
        """
        Collects table header
        :return: ['', subj1, ..., subjN]
        """
        head = [td.text.strip() for td in self._table.find('thead').find('tr').findChildren()]
        return head

    def __get_subjects(self):
        """
        Collects array of subjects' names
        :return: [subj1, subj2, ..., subjN]
        """
        return self._header[1:]

    def __get_data(self):
        """
        Makes a python-matrix from the html-table as you see it on a web-page, excluding academic performance column, which is not needed
        :return: [[grade1, qual1, ..., qualN], ..., [gradeN, qual1, ..., qualN]]
        """
        data_table = []
        table = self._table.find('tbody').find_all('tr')
        summary_rows = self._table.find('tbody').find_all('tr', {'class': 'tr_summary'})

        for row in summary_rows: #remove 'итог' '5-9' etc
            table.remove(row)


        for row in table:
            cells = row.findChildren()

            if self.crop:
                grade_string = cells[0].text[:-1]
                st_grade = str(self.crop[0])
                en_grade = str(self.crop[1])
                if st_grade <= grade_string <= en_grade:
                    data_table.append(self.row_handler(cells))
            else:
                data_table.append(self.row_handler(cells))

        if self.past_year:  # increment grade from the past year
            for row in data_table:
                row[0] = self.increment_grade(row[0])

        return data_table

    def __get_grades(self):
        """
        Collects array of grades' strings
        :return: [grade1, ..., gradeN]
        """

        grades = [row[0] for row in self.data]
        return grades

    def __get_qualities(self):
        """
        Collects grade and quality dict for each subject
        :return: {subj1: {grade1: [qual], ..., gradeN: [qual]}, ..., subjN: {grade1: [qual], ..., gradeN: [qual]}}
        """
        quals = {subj: {grade: [self.data[self.grades.index(grade)][self.subjects.index(subj) + 1]] for grade in self.grades} for subj in self.subjects}
        return quals

    @property
    def header(self):
        return self._header

    @property
    def subjects(self):
        return self._subjects

    @property
    def data(self):
        return self._data

    @property
    def qualities(self):
        return self._qualities

    @property
    def grades(self):
        return self._grades

    def merge_tables(self, *tables: 'OverallSubjectsTable'):
        """
        Extends this table appending grades and qualities from *tables. *tables must be OverallSubjectsTable instances.
        E.g. if you need to merge 6-9 and 10-11 OverallSubjectsTables.
        :param tables: OverallSubjectsTable
        :return: None
        """
        for table in tables:
            if isinstance(table, OverallSubjectsTable):
                self._data += table.data
                self._grades += table.grades
                for key in self._qualities.keys():
                    self._qualities[key].update(table.qualities.get(key, {}))
            else:
                raise TypeError(
                    'Table {} must be OverallSubjectsTable instance, got {}'.format(tables.index(table), type(table)))

    def row_handler(self, cells):
        data_row = [cells[0].text]
        for i in range(1, len(cells)):
            if i % 2 != 0:
                data_row.append(self.extract_data(cells[i].text))
        return data_row


class SubjectsQualitiesTable(Table):
    """
    Extends OverallQualitiesTable functionality with ability to create more complex qualities table.
    Quality dicts are to be placed from newer to older
    """

    def __init__(self, *dicts: dict, raw_page=''):
        super().__init__(raw_page)
        self.dicts = dicts
        self._data = self.__create_quals_table()
        self._header = []


    def __create_quals_table(self):
        """
        Creates more complex qualities table from given qualities dicts.
        :return: {subj1: [[grade1, prev2, prev1, ..., this], ..., [gradeN, prev2, ..., this]], ..., subjN: [[],..., []]}
        """
        super_dict = self.dicts[0] #take the newest dict as main

        for dict in self.dicts[1:]:
            for subj in super_dict.keys():
                if subj in dict.keys():
                    for grade in super_dict[subj]:
                        super_dict[subj][grade] += dict[subj].get(grade, ['н/д'])

        data_dict = {}

        for subj in super_dict.keys():
            subj_table = []
            for grade in super_dict[subj].keys():
                grade_row = [grade, *reversed(super_dict[subj][grade])]
                try:
                    grade_row.append(grade_row[-1] - grade_row[-2])
                except TypeError:
                    grade_row.append('н/д')
                subj_table.append(grade_row)
            data_dict[subj] = subj_table

        return data_dict

    @property
    def data(self):
        return self._data

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, value: list):
        self._header = value

    @header.deleter
    def header(self):
        self._header = []


class GradePerformanceTable(Table):
    def __init__(self, SESSION, raw_page):
        super().__init__(raw_page)
        self._SESSION = SESSION
        self._table = self.raw_page.find('table')
        self._header = self.__get_header()
        self._subjects = self.__get_subjects()
        self._data = self.__handle_table_data()
        self._excellents, self._one_fours, self._two_fours, self._one_threes, self._two_threes = self._data

    def __get_header(self):
        """
        Collects table header
        :return: ['NAME', subj1, ..., subjN, ovr]
        """
        head = [td.text.strip() for td in self._table.find('thead').find('tr').find_all('td')[1:]] #remove row number
        return head

    def __get_subjects(self):
        """
        Collects array of subjects' names
        :return: [subj1, subj2, ..., subjN]
        """
        return self.header[1:-1]

    def __handle_table_data(self):
        """
        Extracts data from the table
        :return: tuple of lists: (excellent, one_four, two_fours, one_three)
        """
        table_rows = self._table.find('tbody').find_all('tr')

        excellent = []
        one_four = []
        two_fours = []
        one_three = []
        two_threes = []
        for row in table_rows:
            cells = row.find_all('td')[1:] #remove row number
            cells[1:] = [td.text.strip() for td in cells[1:]] #leave 1st cell unchanged
            name, term_marks, avg = cells[0], cells[1:-1], cells[-1]

            if avg == '5':
                name, _ = self.__prettify_name(name)
                excellent.append(name)

            elif term_marks.count('3') == 0:

                if term_marks.count('4') == 1:
                    index = term_marks.index('4')
                    subj = self.subjects[index]
                    name, link = self.__prettify_name(name)
                    this_avg = self.__get_avg(index, link)
                    one_four.append((name, subj, this_avg))

                elif term_marks.count('4') == 2:
                    subjs = []
                    indexes = []
                    for i in range(len(term_marks)):
                        c = 0
                        if term_marks[i] == '4':
                            indexes.append(i)
                            subjs.append(self.subjects[i])
                            c += 1

                        if c == 2:
                            break

                    subj_string = '\n'.join(subjs)
                    name, link = self.__prettify_name(name)
                    this_avgs = [self.__get_avg(index, link) for index in indexes]
                    avgs_string = '\n'.join(this_avgs)
                    two_fours.append((name, subj_string, avgs_string))

            elif term_marks.count('3') == 1:
                index = term_marks.index('3')
                subj = self.subjects[index]
                name, link = self.__prettify_name(name)
                this_avg = self.__get_avg(index, link)
                one_three.append((name, subj, this_avg))

            elif term_marks.count('3') == 2:
                subjs = []
                indexes = []
                for i in range(len(term_marks)):
                    c = 0
                    if term_marks[i] == '3':
                        indexes.append(i)
                        subjs.append(self.subjects[i])
                        c += 1

                    if c == 2:
                        break

                subj_string = '\n'.join(subjs)
                name, link = self.__prettify_name(name)
                this_avgs = [self.__get_avg(index, link) for index in indexes]
                avgs_string = '\n'.join(this_avgs)
                two_threes.append((name, subj_string, avgs_string))

        return excellent, one_four, two_fours, one_three, two_threes

    @staticmethod
    def __prettify_name(name):
        """
        Makes readable student's name and a link to get avg mark
        :param name: <td> with ТБ, ПР
        :return: name, link
        """
        name_ = ' '.join(w.strip() for w in name.text.split()[:2]) #surname + name
        link = 'https://edu.tatar.ru/school/reports/' + name.find_all('a')[-1]['href']
        return name_, link

    def __get_avg(self, index, link):
        """
        Finds an average term mark for given subject's index
        :param index:
        :param link:
        :return: avg_mark: str
        """

        r = self._SESSION.get(link)
        info_letter_page = BeautifulSoup(r.text, 'html.parser')
        rows = info_letter_page.find('table').find('tbody').find_all('tr')
        needed_row = rows[index]

        cells = needed_row.find_all('td')
        avg_mark = cells[6].text.strip()

        return avg_mark


    @property
    def subjects(self):
        """
        Returns list of subjects
        :return: list: str
        """
        return self._subjects

    @property
    def header(self):
        return self._header

    @property
    def data(self):
        return self._data

    @property
    def excellents(self):
        """
        Returns names of students with all 5
        :return: list: [name1, name2,..., nameN]
        """
        return self._excellents

    @property
    def one_fours(self):
        """
        Returns list of students with no 3 and one 4.
        :return: list: [(name, subj, avg), ..., (nameN, subj, avg)]
        """
        return self._one_fours

    @property
    def two_fours(self):
        """
        Returns list of students with no 3 and two 4.
        :return: list: [(name, subj1\nsubj2, avg1\navg2), ..., (nameN, subj1\nsubj2, avg1\navg2)]
        """
        return self._two_fours

    @property
    def one_threes(self):
        """
        Returns list of students with one 3
        :return: list: [(name, subj, avg), ..., (nameN, subj, avg)]
        """
        return self._one_threes

    @property
    def two_threes(self):
        """
        Returns list of students with two 3
        :return: list: [(name, subj1\nsubj2, avg1\navg2), ..., (nameN, subj1\nsubj2, avg1\navg2)]
        """
        return self._two_threes

class StudentsPerformanceTables:
    """
    Creates tables 'Количество отличников', 'С одной 4', 'С двумя 4', 'С одной 3', 'С одной 3 (количество)'
    from GradePerformanceTable. Dicts are to be placed from newer to older
    """

    def __init__(self, *dicts):
        self.dicts = list(reversed(dicts))
        self._header_for_count = []
        self._header_for_exc = []
        self._header_for_list = ['Класс', 'Учащийся', 'Предмет', 'Ср. балл', 'Учитель'] #it's always the same but changeable if needed
        self.excellents, self.one_fours, self.one_fours_count, self.two_fours, self.two_fours_count, self.one_threes, \
        self.one_threes_count, self.two_threes, self.two_threes_count = self.__create_tables()

    @property
    def header_for_count(self):
        """
        Header to be placed in excel for tables: 'one fours count', 'two fours count', 'one threes count'
        :return: list
        """
        return self._header_for_count

    @header_for_count.setter
    def header_for_count(self, value: list):
        self._header_for_count = value

    @header_for_count.deleter
    def header_for_count(self):
        self._header_for_count = []

    @property
    def header_for_exc(self):
        """
        Header for excelifying 'excellents' table
        :return:
        """
        return self._header_for_exc

    @header_for_exc.setter
    def header_for_exc(self, value: list):
        self._header_for_exc = value

    @header_for_exc.deleter
    def header_for_exc(self):
        self._header_for_exc = []

    @property
    def header_for_list(self):
        """
        Header for excelifying 'one fours', 'two fours', 'one threes' tables
        :return:
        """
        return self._header_for_list

    @header_for_list.setter
    def header_for_list(self, value: list):
        self._header_for_list = value

    @header_for_list.deleter
    def header_for_list(self):
        self._header_for_list = []

    def __create_tables(self):
        """
        Creates dicts and lists for excelifying from given dicts type: { grade1: GradePerformanceTable, ..., gradeN: GradesPerformanceTable}
        :return: (exc: dict, one4: list, one4_count: dict, two4: list, two4_count: dict, one3: list, one3_count: dict)
        """
        exc = {}

        one4 = []
        one4_count = {}

        two4 = []
        two4_count = {}

        one3 = []
        one3_count = {}

        two3 = []
        two3_count = {}

        this_term_dict = self.dicts[-1]

        all_grades = this_term_dict.keys()

        for dict in self.dicts:
            for grade in all_grades:
                g_p_table = dict.get(grade)
                if g_p_table:
                    grade_exc = g_p_table.excellents
                    if grade_exc:
                        exc[grade] = exc.get(grade, []) + [len(grade_exc), '\n'.join(grade_exc)]
                    else:
                        exc[grade] = exc.get(grade, []) + ['-', '-']

                    grade_one4 = g_p_table.one_fours
                    one4_count[grade] = one4_count.get(grade, []) + [len(grade_one4)]

                    grade_two4 = g_p_table.two_fours
                    two4_count[grade] = two4_count.get(grade, []) + [len(grade_two4)]

                    grade_one3 = g_p_table.one_threes
                    one3_count[grade] = one3_count.get(grade, []) + [len(grade_one3)]

                    grade_two3 = g_p_table.two_threes
                    two3_count[grade] = two3_count.get(grade, []) + [len(grade_two3)]
                else:
                    exc[grade] = exc.get(grade, []) + ['-', '-']
                    one4_count[grade] = one4_count.get(grade, []) + ['н/д']
                    two4_count[grade] = two4_count.get(grade, []) + ['н/д']
                    one3_count[grade] = one3_count.get(grade, []) + ['н/д']
                    two3_count[grade] = two3_count.get(grade, []) + ['н/д']

        for d in (one4_count, two4_count, one3_count, two3_count):
            for arr in d.values():
                if len(arr) > 1:
                    try:
                        arr.append(arr[-1] - arr[-2]) #dynamics
                    except TypeError:
                        arr.append('н/д')
                else:
                    break

        this_term_dict = self.dicts[-1]
        for grade, g_p_table in this_term_dict.items():
            for row in g_p_table.one_fours:
                one4.append([grade, *row])

            for row in g_p_table.two_fours:
                two4.append([grade, *row])

            for row in g_p_table.one_threes:
                one3.append([grade, *row])

            for row in g_p_table.two_threes:
                two3.append([grade, *row])

        return exc, one4, one4_count, two4, two4_count, one3, one3_count, two3, two3_count
