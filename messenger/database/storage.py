import datetime

from sqlalchemy import Table, create_engine, MetaData, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import sessionmaker, mapper

from messenger.common.jim_variables import *


class ServerStorage:
    """
    Класс - Серверная БД. Реляционность необходима - является опорной и для клиентских БД
    """

    class AllUsers:
        """Класс, содержащий основные параметры пользователя"""

        def __init__(self, username, password_hash):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None
            self.password_hash = password_hash

    class ActiveUsers:
        "Класс - описание активного пользователя"

        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    class LoginHistory:
        """
        История входа
        """

        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port

    # Класс - отображение таблицы контактов пользователей
    class UsersContacts:
        """
        Класс, описывавющий контакт пользователя с другим пользователем
        """

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    class UsersHistory:
        """
        Класс, описывающий статистику отправленных и принятых сообщений пользователем
        """

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self):
        self.database_engine = create_engine('sqlite:///database/main.db', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        # Таблица пользователей
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String(50), unique=True),
                            Column('last_login', DateTime),
                            Column('password_hash', Text)
                            )

        # Таблица активных пользователей
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String(50)),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Таблица истории входов
        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id')),
                                   Column('date_time', DateTime),
                                   Column('ip', String(50)),
                                   Column('port', String)
                                   )

        # Таблица контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        # Таблица истории пользователей
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )

        self.metadata.create_all(self.database_engine)

        # Отображения
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

        # Сессия
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Сервер запускается раньше клиентов, при запуске активных пользователей быть не должно.
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port, password_hash):
        """
        Функция регистрации входа пользователя
        """
        # считаем пользователя "хорошим", пока не сравинли пароли
        drop_user = False
        # Есть ли у нас такой пользователь
        result = self.session.query(self.AllUsers).filter_by(name=username)

        # Если есть, добавляем время последнего входа
        if result.count():
            user = result.first()
            # сравниваем пароли
            if user.password_hash == password_hash:
                print(f"пароли {username} совпадают")
                # обновляем последнее посещение
                user.last_login = datetime.datetime.now()
            else:
                # пользователь ввел некорректный пароль, вернем вердикт - кикнуть с чата.
                drop_user = True
                print(f"пароли {username} не совпадают")
                return drop_user
        # Если нет, то создаздаём нового пользователя
        else:
            user = self.AllUsers(username, password_hash)
            self.session.add(user)
            # Коммитим, чтобы получить присвоенный ID
            self.session.commit()
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        # Запись в таблицу активных пользователей о факте входа.
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # и сохранить в историю входов
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # Коммит всех записей
        self.session.commit()

        return drop_user

    def user_logout(self, username):
        """
        Функция выхода клиента из сессии
        """
        # Изем выходящего в общей базе пользователей
        user = self.session.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()

    def process_message(self, sender, recipient):
        """
        Фиксация статистики отправки и получения сообщений.
        """
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Увеличиваем флаги сообщений
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, user, contact):
        """
        Функция - добавление контактов

        """
        # Получаем ID участников операции
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что цель добавления существует
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        """
        Удаление контакта из БД
        """
        # Получаем ID
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что они на самом деле в контакте.
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    def users_list(self):
        """
        Функция, предоставляющая список известных пользователей со временем последнего входа.
        """
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        return query.all()

    def active_users_list(self):
        """
        Возвращает список активных пользователей
        """
        # Собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    def login_history(self, username=None):
        """
        Функция, предоставляющая историю входов
        """
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.name == username)
        # Возвращаем список кортежей
        return query.all()

    def get_contacts(self, username):
        """
        Список контактов пользователя.
        """
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей (БД клиента не реляционная) и возвращаем их.
        return [contact[1] for contact in query.all()]

    def message_history(self):
        """
        Показывает историю сообщений для всех пользователей
        """
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)

        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    test_db.user_login('client_1', '192.168.1.4', 7890)
    print(test_db.users_list())
