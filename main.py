from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from button import Ui_MainWindow
import sys
import traceback
import pickle
import requests
from os import path
from JournalParser.main import execute
from Report.main import create_report
from requests.exceptions import ConnectionError




def check_cred(func):
    def wrapper(self):
        if not application.ui.login.text() or not application.ui.password.text():
            self.error.emit('Нужно ввести логин и пароль')
            return self.finished.emit()
        else:
            return func(self)
    return wrapper

def launch(func):
    def launcher(self):
        self.thread = QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(func(self))

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.status.connect(self.text)
        self.worker.progress.connect(self.set_progress)
        self.worker.error.connect(self.show_error)
        self.worker.alert.connect(self.show_alert)

        return self.thread.start()

    return launcher

class Worker(QObject):
    finished = pyqtSignal()
    status = pyqtSignal(str) # pb label text
    progress = pyqtSignal(int) #pb value
    error = pyqtSignal(str) # error windows
    alert = pyqtSignal(str)

    @pyqtSlot(name='journal')
    @check_cred
    def startCheck(self):
        prms = {
            'login': application.ui.login.text(),
            'password': application.ui.password.text(),
            'class1': application.ui.class1.value(),
            'class2': application.ui.class2.value(),
            'term1': application.ui.term1.value(),
            'term2': application.ui.term2.value(),
            'check_RO': application.ui.check_RO.isChecked(),
            'check_meta': application.ui.check_meta.isChecked(),
            'check_lessons_fill': application.ui.check_lessons_fill.isChecked(),
            'lesson_percent': application.ui.lesson_percent.value(),
            'allowed_not_row': application.ui.allowed_not_row.text(),
            'check_students_fill': application.ui.check_students_fill.isChecked(),
            'term_percent': application.ui.term_percent.value(),
            'check_double_two': application.ui.check_double_two.isChecked(),
            'check_term_marks': application.ui.check_term_marks.isChecked(),
            'min_for_5': application.ui.min_for_5.value(),
            'min_for_4': application.ui.min_for_4.value(),
            'min_for_3': application.ui.min_for_3.value(),
            'group_by': application.ui.group_by.currentText(),
        }

        if not (prms['check_RO'] or prms['check_meta'] or prms['check_lessons_fill'] or prms['check_students_fill'] or
                prms['check_double_two'] or prms['check_term_marks']):
            self.error.emit('Нужно выбрать хотя бы один пункт для проверки')

        else:
            application.ui.check_journals.setEnabled(False)
            application.ui.create_report.setEnabled(False)

            execute(prms, self.progress, self.status)

            self.alert.emit('Журналы успешно проверены! Результат - Excel-файл в папке приложения.')

            application.ui.check_journals.setEnabled(True)
            application.ui.create_report.setEnabled(True)

        self.finished.emit()

    @pyqtSlot(name='report')
    @check_cred
    def createReport(self):
        prms = {
            'login': application.ui.login.text(),
            'password': application.ui.password.text(),
            'term1': application.ui.rep_term.value(),
            'term2': application.ui.rep_term.value(),
            'class1': application.ui.start_grade.value(),
            'class2': 11
        }

        application.ui.create_report.setEnabled(False)
        application.ui.start_check.setEnabled(False)

        if not application.check_login(prms['login']):
            self.alert.emit('Эта функция недоступна в бесплатной версии. Пожалуйста, приобретите полную версию приложения.')
        else:
            create_report(prms, self.progress, self.status)
            self.alert.emit('Отчеты составлены. Их вы найдете в Excel-файлах в папке приложения.')

        application.ui.create_report.setEnabled(True)
        application.ui.start_check.setEnabled(True)
        self.finished.emit()


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.icon = QtGui.QIcon('icon.png')
        self.setWindowIcon(self.icon)


        self.ui.group_by.addItems(['По классам', 'По учителям'])
        if path.exists('cr.pkl'):
            l, p = self.loadCred()
            self.ui.login.setText(l)
            self.ui.password.setText(p)

        self.ui.start_check.clicked.connect(self.start_check)
        self.ui.create_report.clicked.connect(self.create_report)

        self.ui.saveCred.clicked.connect(self.saveCred)

    @launch
    def start_check(self):
        return self.worker.startCheck

    @launch
    def create_report(self):
        return self.worker.createReport


    def text(self, text: str):
        self.ui.pb_label.setText(text)
        self.ui.rep_pb_label.setText(text)


    def set_progress(self, value: int):
        self.ui.progressBar.setValue(value)
        self.ui.rep_progressBar.setValue(value)

    def show_error(self, msg: str):
        err = QMessageBox()
        err.setWindowIcon(self.icon)
        err.setIcon(QMessageBox.Critical)
        err.setText(msg)
        err.setWindowTitle('Ошибка')
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        err.setSizePolicy(sizePolicy)
        err.exec_()

    def show_alert(self, msg: str):
        err = QMessageBox()
        err.setWindowIcon(self.icon)
        err.setIcon(QMessageBox.Information)
        err.setText(msg)
        err.setWindowTitle('Внимание!')
        err.exec_()

    def saveCred(self):
        cred = {
            "login": self.ui.login.text(),
            "password": self.ui.password.text(),
        }

        with open('cr.pkl', 'wb') as ouf:
            pickle.dump(cred, ouf)

    def loadCred(self):
        with open('cr.pkl', 'rb') as inf:
            cred = pickle.load(inf)
            login, password = cred.get('login', ''), cred.get('password', '')

            return login, password

    def check_login(self, login: str):
        data = {'login': login}
        r = requests.post('https://features.li79.ru/journal/lcheck', data)
        r = r.json()

        return r.get('status')



def excepthook(exc_type, exc_value, exc_traceback):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    if exc_type is PermissionError:
        application.worker.error.emit('Неверный логин/пароль или включена двухфакторная аутентификация.')
    elif exc_type is ConnectionError:
        application.worker.error.emit('Проблемы с соединением. Повторите попытку позже')
    else:
        application.worker.error.emit(tb)
    application.worker.finished.emit()

    application.ui.start_check.setEnabled(True)
    application.ui.create_report.setEnabled(True)


sys.excepthook = excepthook

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    application = MyWindow()
    application.show()
    sys.exit(app.exec())