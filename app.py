from flask import Flask, render_template, request, redirect, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from sqlalchemy import func
from flask_security import roles_accepted, auth_required, logout_user
from flask_mailman import Mail
from model import db, seedData, Customer, Account, Transaction, User, user_datastore
from flask_security import Security, hash_password
from forms import NewCustomerForm, AddAccountForm, WithdrawForm, DepositForm, TransferForm, NewUserForm, EditUserForm
import os
from datetime import datetime
 
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:666@localhost:3306/Bank'
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", 'pf9Wkove4IKEAXvy-cQkeDPhv9Cb3Ag-wyJILbq_dFw')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get("SECURITY_PASSWORD_SALT", '146585145368132386173505678016728509634')
app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
app.config["SESSION_COOKIE_SAMESITE"] = "strict"
app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_password'
app.config['MAIL_USE_TLS'] = False
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_FRESHNESS_GRACE_PERIOD'] = 1
mail = Mail(app)
app.security = Security(app, user_datastore)
db.app = app
db.init_app(app)
migrate = Migrate(app,db)
 
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

@app.route("/")
def startpage():
    count_customers = Customer.query.count()
    count_accounts = Account.query.count()
    sum_accounts = Account.query.with_entities(func.sum(Account.Balance).label('total')).first().total

    unique_countries_query = Customer.query.with_entities(Customer.Country).distinct()
    country_list = [row.Country for row in unique_countries_query.all()]
    countries_networth = {}
    print(country_list)
    for x in country_list:
        customers_country = Customer.query.filter_by(Country = x).all()
        country_networth = 0
        for customer in customers_country:
            customer_net_query = Account.query.filter_by(CustomerId = customer.Id).with_entities(func.sum(Account.Balance).label('total')).first().total
            country_networth = country_networth + customer_net_query
        countries_networth[x] = int(country_networth)

    countries_networth = sorted(countries_networth.items(), key=lambda x:x[1], reverse=True)
    countries_by_networth = dict(countries_networth)

    top3 = {k: countries_by_networth[k] for k in list(countries_by_networth)[:3]}
    
    return render_template("startpage.html",
                            count_customers=count_customers,
                            count_accounts=count_accounts,
                            sum_accounts=sum_accounts,
                            top3=top3.items())

@app.route("/country/<country>")
def country_top_10(country):
    customers_country_query = Customer.query.filter_by(Country = country).all()
    customers_country_net = {}
    for customer in customers_country_query:
        customer_net_query = Account.query.filter_by(CustomerId = customer.Id).with_entities(func.sum(Account.Balance).label('total')).first().total
        customers_country_net[f"{customer.GivenName} {customer.Surname}"] = int(customer_net_query)

    all_customer_networth = sorted(customers_country_net.items(), key=lambda x:x[1], reverse=True)
    all_customer_networth_dict = dict(all_customer_networth)

    top10 = {k: all_customer_networth_dict[k] for k in list(all_customer_networth_dict)[:10]}

    return render_template("country.html", 
                           top10=top10.items(),
                           country=country)

@app.route("/customers")
@auth_required()
@roles_accepted("Admin","Cashier")
def customers():
    sortColumn = request.args.get('sortColumn', 'name')
    sortOrder = request.args.get('sortOrder', 'asc')
    q = request.args.get('q', '')
    page = int(request.args.get('page', 1))

    customers = Customer.query

    customers = customers.filter(
        Customer.GivenName.like('%' + q + '%') |
        Customer.City.like('%' + q + '%')
    )

    if sortColumn == "name":
        if sortOrder == "asc":
            customers = customers.order_by(Customer.GivenName.asc())
        else:
            customers = customers.order_by(Customer.GivenName.desc())
    elif sortColumn == "city":
        if sortOrder == "asc":
            customers = customers.order_by(Customer.City.asc())
        else:
            customers = customers.order_by(Customer.City.desc())
    
    paginationObject = customers.paginate(page=page, per_page=20, error_out=False)
    
    return render_template("customers.html",
                            customers=paginationObject.items,
                            pages = paginationObject.pages,
                            sortOrder=sortOrder,
                            sortColumn=sortColumn,
                            page=page,
                            has_next=paginationObject.has_next,
                            has_prev=paginationObject.has_prev,
                            q=q)

@app.route("/customer/<id>")
@auth_required()
@roles_accepted("Admin","Cashier")
def customer(id):
    customer = Customer.query.filter_by(Id = id).first()
    customer_accounts = Account.query.filter_by(CustomerId = id).all()
    return render_template("customer.html",
                            customer=customer,
                            customer_accounts=customer_accounts)

@app.route("/customer/<customer_id>/<account_id>")
@auth_required()
@roles_accepted("Admin","Cashier")
def manageaccount(customer_id, account_id):
    customer = Customer.query.filter_by(Id = customer_id).first()
    active_account = Account.query.filter_by(Id = account_id).first()
    active_account_transactions = Transaction.query.filter_by(AccountId = account_id).all()
    return render_template("manageaccount.html",
                            customer=customer,
                            active_account=active_account,
                            active_account_transactions=active_account_transactions)

@app.route("/customer/<customer_id>/<account_id>/deposit", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def deposit(customer_id, account_id):
    customer = Customer.query.filter_by(Id = customer_id).first()
    active_account = Account.query.filter_by(Id = account_id).first()
    form = DepositForm()
    if form.validate_on_submit():
        active_account.Balance = active_account.Balance + form.depositAmount.data
        transaction = Transaction()
        transaction.Type = "Debit"
        transaction.Operation = "Deposit cash"
        transaction.Date = datetime.now()
        transaction.Amount = form.depositAmount.data
        transaction.NewBalance = active_account.Balance
        transaction.AccountId = account_id
        db.session.add(transaction)
        db.session.commit()
        flash("Deposit successful")
        return redirect("/customer/" + customer_id + "/" + account_id) 
    return render_template("deposit.html",
                            customer=customer,
                            active_account=active_account,
                            form=form)
                            
@app.route("/customer/<customer_id>/<account_id>/withdrawal", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def withdrawal(customer_id, account_id):
    customer = Customer.query.filter_by(Id = customer_id).first()
    active_account = Account.query.filter_by(Id = account_id).first()
    form = WithdrawForm()

    validationOk = True
    if request.method == "POST":
        if form.withdrawalAmount.data > active_account.Balance:
            form.withdrawalAmount.errors = form.withdrawalAmount.errors + ('Amount cannot exceed balance',)
            validationOk = False

    if validationOk == True and form.validate_on_submit():
        active_account.Balance = active_account.Balance - form.withdrawalAmount.data
        transaction = Transaction()
        transaction.Type = "Credit"
        transaction.Operation = "Withdrawal"
        transaction.Date = datetime.now()
        transaction.Amount = form.withdrawalAmount.data
        transaction.NewBalance = active_account.Balance
        transaction.AccountId = account_id
        db.session.add(transaction)
        db.session.commit()
        flash("Withdrawal successful")
        return redirect("/customer/" + customer_id + "/" + account_id)    
    return render_template("withdrawal.html",
                            customer=customer,
                            active_account=active_account,
                            form=form)

@app.route("/customer/<customer_id>/<account_id>/transfer", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def transfer(customer_id, account_id):
    customer = Customer.query.filter_by(Id = customer_id).first()
    active_account = Account.query.filter_by(Id = account_id).first()
    form = TransferForm()
    destination_account = Account.query.filter_by(Id = form.destinationAccountId.data).first()

    validationOk = True
    if request.method == "POST":
        if form.transferAmount.data > active_account.Balance:
            form.transferAmount.errors = form.transferAmount.errors + ('Amount cannot exceed balance',)
            validationOk = False
        if  destination_account == None:
            form.destinationAccountId.errors = form.destinationAccountId.errors + ('Destination account does not exist',)
            validationOk = False

    if validationOk == True and form.validate_on_submit():
        active_account.Balance = active_account.Balance - form.transferAmount.data
        destination_account.Balance = destination_account.Balance + form.transferAmount.data
        transaction = Transaction()
        transaction.Type = form.transactionType.data
        transaction.Operation = f"Transfer to {form.destinationAccountId.data}"
        transaction.Date = datetime.now()
        transaction.Amount = form.transferAmount.data
        transaction.NewBalance = active_account.Balance
        transaction.AccountId = account_id
        db.session.add(transaction)
        transaction_recipient = Transaction()
        transaction_recipient.Type = form.transactionType.data
        transaction_recipient.Operation = f"Received from {account_id}"
        transaction_recipient.Date = datetime.now()
        transaction_recipient.Amount = form.transferAmount.data
        transaction_recipient.NewBalance = destination_account.Balance
        transaction_recipient.AccountId = form.destinationAccountId.data
        db.session.add(transaction_recipient)
        db.session.commit()
        flash("Transfer successful")
        return redirect("/customer/" + customer_id + "/" + account_id)
    return render_template("transfer.html",
                            customer=customer,
                            active_account=active_account,
                            form=form)


@app.route("/newcustomer", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def newcustomer():
    form = NewCustomerForm()
    if form.validate_on_submit():
        customer = Customer()
        customer.GivenName = form.name.data
        customer.Surname = form.surname.data
        customer.Streetaddress = form.address.data
        customer.City = form.city.data
        customer.Zipcode = form.zipcode.data
        customer.Country = form.country.data
        customer.CountryCode = form.countryCode.data
        customer.Birthday = form.birthday.data
        customer.NationalId = form.nationalid.data
        customer.TelephoneCountryCode = form.telephoneCode.data
        customer.Telephone = form.phonenumber.data
        customer.EmailAddress = form.mail.data
        db.session.add(customer)
        db.session.commit()
        account = Account()
        account.AccountType = "Personal"
        account.Created = datetime.now()
        account.Balance = 0
        account.CustomerId = customer.Id
        db.session.add(account)
        db.session.commit()
        flash("Customer added")
        return redirect("/customers")
    return render_template("newcustomer.html", 
                            form=form )

@app.route("/customer/<id>/edit", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def editcustomer(id):
    form = NewCustomerForm()
    customer = Customer.query.filter_by(Id = id).first()
    if form.validate_on_submit():
        customer.GivenName = form.name.data
        customer.Surname = form.surname.data
        customer.Streetaddress = form.address.data
        customer.City = form.city.data
        customer.Zipcode = form.zipcode.data
        customer.Country = form.country.data
        customer.CountryCode = form.countryCode.data
        customer.Birthday = form.birthday.data
        customer.NationalId = form.nationalid.data
        customer.TelephoneCountryCode = form.telephoneCode.data
        customer.Telephone = form.phonenumber.data
        customer.EmailAddress = form.mail.data
        db.session.commit()
        flash("Customer updated")
        return redirect("/customer/" + id)
    form.name.data = customer.GivenName
    form.surname.data = customer.Surname
    form.address.data = customer.Streetaddress
    form.city.data = customer.City
    form.zipcode.data = customer.Zipcode
    form.country.data = customer.Country
    form.countryCode.data = customer.CountryCode
    form.birthday.data = customer.Birthday
    form.nationalid.data = customer.NationalId
    form.telephoneCode.data = str(customer.TelephoneCountryCode)
    form.phonenumber.data = customer.Telephone
    form.mail.data = customer.EmailAddress
    return render_template("editcustomer.html", 
                            form=form,
                            customer=customer )

@app.route("/customer/<id>/addacc", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin","Cashier")
def addaccount(id):
    customer = Customer.query.filter_by(Id = id).first()
    form = AddAccountForm()
    if form.validate_on_submit():
        account = Account()
        account.AccountType = form.AccountType.data
        account.Created = datetime.now()
        account.Balance = 0
        account.CustomerId = id
        db.session.add(account)
        db.session.commit()
        flash("Account opened")
        return redirect("/customer/" + id)
    return render_template("addaccount.html", 
                            form=form,
                            customer=customer)
#### Admin Routes

@app.route("/users")
@auth_required()
@roles_accepted("Admin")
def manage_users():
    return render_template("users.html")

@app.route("/user/<id>", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin")
def edituser(id):
    form = EditUserForm()
    user = user_datastore.find_user(id=id)
    validationOk = True
    if request.method == "POST":
        if app.security.datastore.find_user(email=form.mail.data):
            if form.mail.data == user.email:
                pass
            else:
                form.mail.errors = form.mail.errors + ('E-mail already exists',)
                validationOk = False
    if validationOk == True and form.validate_on_submit():
        user.email = form.mail.data
        if user.roles[0] == "Admin":
            user_datastore.remove_role_from_user(user, "Admin")
        else:
            user_datastore.remove_role_from_user(user, "Cashier")
        user_datastore.add_role_to_user(user, form.role.data)
        app.security.datastore.db.session.commit()
        flash("User updated")
        return redirect("/users")
    form.mail.data = user.email
    form.role.data = user.roles[0]
    return render_template("edituser.html", 
                            form=form )

@app.route("/newuser", methods=['GET', 'POST'])
@auth_required()
@roles_accepted("Admin")
def newuser():
    form = NewUserForm()

    validationOk = True
    if request.method == "POST":
        if app.security.datastore.find_user(email=form.mail.data):
            form.mail.errors = form.mail.errors + ('E-mail already exists',)
            print(form.mail.errors)
            validationOk = False

    if validationOk == True and form.validate_on_submit():
        app.security.datastore.create_user(email=form.mail.data, 
                                           password=hash_password(form.pw.data),
                                           roles=[form.role.data])
        app.security.datastore.db.session.commit()
        flash("User added")
        return redirect("/users")
    return render_template("newuser.html", 
                            form=form )

@app.route('/deactivate_user/<id>')
@auth_required()
@roles_accepted("Admin")
def deactivate_user(id):
    user = user_datastore.find_user(id=id)
    user_datastore.deactivate_user(user)
    app.security.datastore.db.session.commit()
    flash("Deactivation successful")
    return redirect("/users")

@app.route('/activate_user/<id>')
@auth_required()
@roles_accepted("Admin")
def activate_user(id):
    user = user_datastore.find_user(id=id)
    user_datastore.activate_user(user)
    app.security.datastore.db.session.commit()
    flash("Activation successful")
    return redirect("/users")

#### API Routes

@app.route("/api/transactions/<id>")
@auth_required()
@roles_accepted("Admin","Cashier")
def account_transactions_api(id):
    transactions = []
    page = int(request.args.get('page',1))
    transactions_query = Transaction.query.filter_by(AccountId = id).order_by(Transaction.Date.desc()).paginate(page=page,per_page=15)
    for trans in transactions_query.items:
        t = {   "Id":trans.Id,
                "Type":trans.Type, 
                "Operation":trans.Operation, 
                "Date":trans.Date, 
                "Amount":trans.Amount, 
                "NewBalance":trans.NewBalance }
        transactions.append(t)
    return jsonify(transactions)

@app.route("/api/customer/<id>")
@auth_required()
@roles_accepted("Admin","Cashier")
def customer_info_api(id):
    customer = Customer.query.filter_by(Id = id).first()
    c = {   "Name":customer.GivenName,
            "Surname":customer.Surname, 
            "StreetAdress":customer.Streetaddress, 
            "City":customer.City, 
            "Zipcode":customer.Zipcode, 
            "Country":customer.Country,
            "CountryCode":customer.CountryCode,
            "Birthday":customer.Birthday,
            "NationalId":customer.NationalId,
            "TelephoneCountryCode":customer.TelephoneCountryCode,
            "Telephone":customer.Telephone,
            "EmailAddress":customer.EmailAddress,
            "Accounts":str(customer.Accounts) }
    return jsonify(c)

@app.route("/api/users_list")
@auth_required()
@roles_accepted("Admin")
def user_info_api():
    users = []
    page = int(request.args.get('page',1))
    users_query = User.query.paginate(page=page,per_page=15)
    for user in users_query.items:
        role_names = []
        for role in user.roles:
            role_names.append(role.name)
        u = {   "id":user.id,
                "Email":user.email, 
                "Active":user.active,
                "Role":str(role_names[0]) }
        users.append(u)
    return jsonify(users)

if __name__  == "__main__":
    with app.app_context():
        upgrade()
    
        seedData(app, db)
        app.run()