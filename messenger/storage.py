import datetime

from sqlalchemy import Table, create_engine, MetaData, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, mapper


class ServerStorage:
    class User:

        def __init__(self, login, info):
            self.login = login
            self.info = info
            self.id = None

    class UserHistory:

        def __init__(self, user_id, ip_address, connected_at):
            self.user_id = user_id
            self.ip_address = ip_address
            self.connected_at = connected_at
            self.id = None

    class ContactsList:

        def __init__(self, from_user_id, to_user_id):
            self.from_user_id = from_user_id
            self.to_user_id = to_user_id
            self.id = None

    def __init__(self):
        self.database_engine = create_engine('sqlite:///test.db', echo=False, pool_recycle=7200)
        self.metadata = MetaData()

        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('login', String(50), unique=True),
                            Column('info', String(50))
                            )

        user_history_table = Table('User_history', self.metadata,
                                   Column('id', Integer, primary_key=True),

                                   Column('user_id', ForeignKey('Users.id')),
       

                                   Column('ip_address', String(50)),
                                   Column('port', Integer),
                                   Column('connected_at', DateTime)
                                   )

        contacts_list_table = Table('Contacts_list', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('from_user_id', ForeignKey('Users.id')),
                                    Column('to_user_id', ForeignKey('Users.id')),
                                    )

        self.metadata.create_all(self.database_engine)

        mapper(self.User, users_table)
        mapper(self.UserHistory, user_history_table)
        mapper(self.ContactsList, contacts_list_table)

        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

    def user_login(self, login, ip_address):
        result = self.session.query(self.User).filter_by(login=login)
        if not result.count():
            user = self.User(login, None)
            self.session.add(user)
            self.session.commit()

        entered_user = self.UserHistory(user.id, ip_address, datetime.datetime.now())
        self.session.add(entered_user)

        self.session.commit()

    def get_contacts(self, username):
        username = self.session.query(self.User).filter_by(login=username).first()
        query = self.session.query(self.ContactsList).filter_by(from_user_id=username.id)
        return query.all()

    def add_contact(self, who_adds, who_to_add):
        who_adds = self.session.query(self.User).filter_by(login=who_adds).first()
        who_to_add = self.session.query(self.User).filter_by(login=who_to_add).first()
        if who_to_add:
            new_contact = self.ContactsList(who_adds.id, who_to_add.id)
            self.session.add(new_contact)

    def del_contact(self, who_removes, will_be_removed):
        who_removes = self.session.query(self.User).filter_by(login=who_removes).first()
        will_be_removed = self.session.query(self.User).filter_by(login=will_be_removed).first()
        if will_be_removed:
            try:
                self.session.query(self.ContactsList).filter_by(self.ContactsList.from_user_id == who_removes.id,
                                                                self.ContactsList.to_user_id == will_be_removed.id).delete()
                self.session.commit()
            except Exception:
                pass




if __name__ == '__main__':
    test_db = ServerStorage()

    test_db.user_login('client_1', '192.168.1.4')

