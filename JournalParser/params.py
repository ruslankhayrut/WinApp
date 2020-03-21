import re

class Params:
    def __init__(self, kwargs):
        self.CONTROL_WORKS = ('КР', 'Д')
        self.MARKS_COL_TYPES = ('КР', 'ЛР', 'СР', 'ПР', 'Д', 'С', 'И', 'Т', 'СД', 'З')
        self.STR_MARKS = ('1', '2', '3', '4', '5')

        self.login = kwargs.get('login', '')
        self.password = kwargs.get('password', '')
        self.class1 = int(kwargs.get('class1', 1))
        self.class2 = int(kwargs.get('class2', 1))
        self.term1 = int(kwargs.get('term1', 1))
        self.term2 = int(kwargs.get('term2', 1))
        self.min_for_5 = round(float(kwargs.get('min_for_5', 4.5)), 2)
        self.min_for_4 = round(float(kwargs.get('min_for_4', 3.5)), 2)
        self.min_for_3 = round(float(kwargs.get('min_for_3', 2.5)), 2)
        self.lesson_percent = int(kwargs.get('lesson_percent', 25))
        self.term_percent = int(kwargs.get('term_percent', 30))
        self.allowed_not_row = tuple(re.findall('[А-Яа-яЁё]+', kwargs.get('allowed_not_row', '')))

        self.check_RO = kwargs.get('check_RO', False)
        self.check_meta = kwargs.get('check_meta', False)
        self.check_lessons_fill = kwargs.get('check_lessons_fill', False)
        self.check_students_fill = kwargs.get('check_students_fill', False)
        self.check_double_two = kwargs.get('check_double_two', False)
        self.check_term_marks = kwargs.get('check_term_marks', False)


        self.group_by_alias = {'По учителям': 'teachers', 'По классам': 'grades'}
        self.group_by = self.group_by_alias[kwargs.get('group_by', 'По классам')]

        if self.class1 > self.class2:
            self.class2 = self.class1

        if self.term1 > self.term2:
            self.term2 = self.term1

        if (not self.check_RO and not self.check_meta and not self.check_lessons_fill
        and not self.check_students_fill and not self.check_double_two):
            self.only_term = True
        else:
            self.only_term = False