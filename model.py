from flask_sqlalchemy import SQLAlchemy
import barnum
import random
from datetime import datetime  
from datetime import timedelta
from flask_security import hash_password, SQLAlchemyUserDatastore
from flask_security.models import fsqla_v3 as fsqla

db = SQLAlchemy()

fsqla.FsModels.set_db_info(db)

class Role(db.Model, fsqla.FsRoleMixin):
    pass

class User(db.Model, fsqla.FsUserMixin):
    pass


user_datastore = SQLAlchemyUserDatastore(db, User, Role)

class Customer(db.Model):
    __tablename__= "Customers"
    Id = db.Column(db.Integer, primary_key=True)
    GivenName = db.Column(db.String(50), unique=False, nullable=False)
    Surname = db.Column(db.String(50), unique=False, nullable=False)
    Streetaddress = db.Column(db.String(50), unique=False, nullable=False)
    City = db.Column(db.String(50), unique=False, nullable=False)
    Zipcode = db.Column(db.String(10), unique=False, nullable=False)
    Country = db.Column(db.String(30), unique=False, nullable=False)
    CountryCode = db.Column(db.String(2), unique=False, nullable=False)
    Birthday = db.Column(db.DateTime, unique=False, nullable=False)
    NationalId = db.Column(db.String(20), unique=False, nullable=False)
    TelephoneCountryCode = db.Column(db.Integer, unique=False, nullable=False)
    Telephone = db.Column(db.String(20), unique=False, nullable=False)
    EmailAddress = db.Column(db.String(50), unique=False, nullable=False)

    Accounts = db.relationship('Account', backref='Customer',
     lazy=True)

class Account(db.Model):
    __tablename__= "Accounts"
    Id = db.Column(db.Integer, primary_key=True)
    AccountType = db.Column(db.String(10), unique=False, nullable=False)
    Created = db.Column(db.DateTime, unique=False, nullable=False)
    Balance = db.Column(db.Integer, unique=False, nullable=False)
    Transactions = db.relationship('Transaction', backref='Account',
     lazy=True)
    CustomerId = db.Column(db.Integer, db.ForeignKey('Customers.Id'), nullable=False)


class Transaction(db.Model):
    __tablename__= "Transactions"
    Id = db.Column(db.Integer, primary_key=True)
    Type = db.Column(db.String(20), unique=False, nullable=False)
    Operation = db.Column(db.String(50), unique=False, nullable=False)
    Date = db.Column(db.DateTime, unique=False, nullable=False)
    Amount = db.Column(db.Integer, unique=False, nullable=False)
    NewBalance = db.Column(db.Integer, unique=False, nullable=False)
    AccountId = db.Column(db.Integer, db.ForeignKey('Accounts.Id'), nullable=False)



def seedData(app, db):
    antal =  Customer.query.count()
    while antal < 500:
        customer = Customer()
        
        customer.GivenName, customer.Surname = barnum.create_name()

        customer.Streetaddress = barnum.create_street()
        customer.Zipcode, customer.City, _  = barnum.create_city_state_zip()
        customer.Country = random.choice(["USA", "Sweden", "Norway", "Finland"])
        if customer.Country == "USA":
            customer.CountryCode = "US"
        if customer.Country == "Sweden":
            customer.CountryCode = "SE"
        if customer.Country == "Norway":
            customer.CountryCode = "NO"
        if customer.Country == "Finland":
            customer.CountryCode = "FI"
        customer.Birthday = barnum.create_birthday()
        n = barnum.create_cc_number()
        customer.NationalId = customer.Birthday.strftime("%Y%m%d-") + n[1][0][0:4]
        if customer.Country == "USA":
            customer.TelephoneCountryCode = 55
        if customer.Country == "Sweden":
            customer.TelephoneCountryCode = 46
        if customer.Country == "Norway":
            customer.TelephoneCountryCode = 47
        if customer.Country == "Finland":
            customer.TelephoneCountryCode = 358
        customer.Telephone = barnum.create_phone()
        customer.EmailAddress = barnum.create_email().lower()

        for x in range(random.randint(1,4)):
            account = Account()

            c = random.randint(0,100)
            if c < 33:
                account.AccountType = "Personal"    
            elif c < 66:
                account.AccountType = "Checking"    
            else:
                account.AccountType = "Savings"    


            start = datetime.now() + timedelta(days=-random.randint(1000,10000))
            account.Created = start
            account.Balance = 0
            
            for n in range(random.randint(0,30)):
                belopp = random.randint(0,30)*100
                tran = Transaction()
                start = start+ timedelta(days=-random.randint(10,100))
                if start > datetime.now():
                    break
                tran.Date = start
                account.Transactions.append(tran)
                tran.Amount = belopp
                if account.Balance - belopp < 0:
                    tran.Type = "Debit"
                else:
                    if random.randint(0,100) > 70:
                        tran.Type = "Debit"
                    else:
                        tran.Type = "Credit"

                r = random.randint(0,100)
                if tran.Type == "Debit":
                    account.Balance = account.Balance + belopp
                    if r < 20:
                        tran.Operation = "Deposit cash"
                    elif r < 66:
                        tran.Operation = "Salary"
                    else:
                        tran.Operation = "Transfer"
                else:
                    account.Balance = account.Balance - belopp
                    if r < 40:
                        tran.Operation = "ATM withdrawal"
                    if r < 75:
                        tran.Operation = "Payment"
                    elif r < 85:
                        tran.Operation = "Bank withdrawal"
                    else:
                        tran.Operation = "Transfer"

                tran.NewBalance = account.Balance


            customer.Accounts.append(account)

        db.session.add(customer)
        db.session.commit()
        
        antal = antal + 1

    app.security.datastore.db.create_all()
    if not app.security.datastore.find_role("Admin"):
        app.security.datastore.create_role(name="Admin")
    if not app.security.datastore.find_role("Cashier"):
        app.security.datastore.create_role(name="Cashier")
    if not app.security.datastore.find_user(email="admin@systementor.se"):
        app.security.datastore.create_user(email="admin@systementor.se", password=hash_password("password"),roles=["Admin"])
    if not app.security.datastore.find_user(email="worker1@systementor.se"):
        app.security.datastore.create_user(email="worker1@systementor.se", password=hash_password("password"),roles=["Cashier"])
    if not app.security.datastore.find_user(email="worker2@systementor.se"):
        app.security.datastore.create_user(email="worker2@systementor.se", password=hash_password("password"),roles=["Cashier"])
    if not app.security.datastore.find_user(email="stefan.holmberg@systementor.se"):
        app.security.datastore.create_user(email="stefan.holmberg@systementor.se", password=hash_password("Hejsan123#"),roles=["Admin"])
    if not app.security.datastore.find_user(email="stefan.holmberg@nackademin.se"):
        app.security.datastore.create_user(email="stefan.holmberg@nackademin.se", password=hash_password("Hejsan123#"),roles=["Cashier"])
    app.security.datastore.db.session.commit()

