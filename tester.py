import unittest
from flask import Flask, render_template, request, url_for, redirect
from app import app
from model import db, Customer, User, Role, Account
from flask_security import Security,SQLAlchemyUserDatastore, hash_password
from sqlalchemy import create_engine
from datetime import datetime

def set_current_user(app, ds, email):
    """Set up so that when request is received,
    the token will cause 'user' to be made the current_user
    """

    def token_cb(request):
        if request.headers.get("Authentication-Token") == "token":
            return ds.find_user(email=email)
        return app.security.login_manager.anonymous_user()

    app.security.login_manager.request_loader(token_cb)


init = False

class TestCases(unittest.TestCase):
    # def __init__(self, *args, **kwargs):
    #     super(FormsTestCases, self).__init__(*args, **kwargs)
    def tearDown(self):
        self.ctx.pop()
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        #self.client = app.test_client()
        app.config["SERVER_NAME"] = "lilbanken.se"
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['WTF_CSRF_METHODS'] = []  # This is the magic
        app.config['TESTING'] = True
        app.config['LOGIN_DISABLED'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['SECURITY_FRESHNESS_GRACE_PERIOD'] = 123454
        global init
        if not init:
            db.init_app(app)
            db.create_all()
            init = True
            user_datastore = SQLAlchemyUserDatastore(db, User, Role)
            app.security = Security(app, user_datastore,register_blueprint=False)
            app.security.init_app(app, user_datastore,register_blueprint=False)
            app.security.datastore.db.create_all()

    def test_a_withdrawing_amount_exceeding_balance(self):
        app.security.datastore.create_role(name="Admin")
        app.security.datastore.create_user(email="unittest@me.com", password=hash_password("password"), roles=["Admin"])
        app.security.datastore.commit()

        set_current_user(app, app.security.datastore, "unittest@me.com")
        customer = Customer()
        customer.GivenName = "TestFirstName"
        customer.Surname = "TestSurname"
        customer.Streetaddress = "TestValley"
        customer.City = "TestCity"
        customer.Zipcode = "111-11"
        customer.Country = "TestCountry"
        customer.CountryCode = "55"
        customer.Birthday = datetime.now().date()
        customer.NationalId = "111111111111"
        customer.TelephoneCountryCode = 55
        customer.Telephone = "0701111111"
        customer.EmailAddress = "testcustomer@me.com"
        db.session.add(customer)

        account = Account()
        account.AccountType = "Personal"
        account.Created = datetime.now()
        account.Balance = 100
        account.CustomerId = 1
        db.session.add(account)
        db.session.commit()

        test_client = app.test_client()
        with test_client:
            url = "/customer/1/1/withdrawal"
            response = test_client.post(url, data={ "withdrawalAmount":"300"},  headers={app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"]: "token"} )
            s = response.data.decode("utf-8") 
            ok = 'Amount cannot exceed balance' in s
            self.assertTrue(ok)


    def test_withdrawing_negative_amount(self):
        test_client = app.test_client()
        with test_client:
            url = "/customer/1/1/withdrawal"
            response = test_client.post(url, data={ "withdrawalAmount":"-5"},  headers={app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"]: "token"} )
            s = response.data.decode("utf-8") 
            ok = 'Amount must be positive!' in s
            self.assertTrue(ok)


    def test_depositing_negative_amount(self):
        test_client = app.test_client()
        with test_client:
            url = "/customer/1/1/deposit"
            response = test_client.post(url, data={ "depositAmount":"-50"},  headers={app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"]: "token"} )
            s = response.data.decode("utf-8") 
            ok = 'Amount must be positive!' in s
            self.assertTrue(ok)


    def test_transfer_amount_exceeding_balance(self):
        account = Account()
        account.AccountType = "Personal"
        account.Created = datetime.now()
        account.Balance = 200
        account.CustomerId = 1
        db.session.add(account)
        db.session.commit()

        test_client = app.test_client()
        with test_client:
            url = "/customer/1/1/transfer"
            response = test_client.post(url, data={ "transferAmount":"400", "destinationAccountId":"1", "transactionType":"Debit"},  headers={app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"]: "token"} )
            s = response.data.decode("utf-8") 
            ok = 'Amount cannot exceed balance' in s
            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()