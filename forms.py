from flask_wtf import FlaskForm
from wtforms import Form, BooleanField, StringField, PasswordField, validators, ValidationError
from wtforms.fields import IntegerField, SelectField, DateField

def validate_positive(form, field):
    if field.data < 0:
        raise ValidationError('Amount must be positive!')

class NewCustomerForm(FlaskForm):
    name = StringField('name', validators=[validators.DataRequired()])
    surname = StringField('surname', validators=[validators.DataRequired()])
    address = StringField('address', validators=[validators.DataRequired()])
    city = StringField('city', validators=[validators.DataRequired()])
    zipcode = StringField('zipcode', validators=[validators.DataRequired()])
    country = StringField('country', validators=[validators.DataRequired()])
    countryCode = SelectField('countryCode',choices=[('US','US'), ('SE','SE'), ('NO','NO'), ('FI','FI')], validators=[validators.DataRequired()])
    birthday = DateField('birthday', validators=[validators.DataRequired()])
    nationalid = StringField('nationalid', validators=[validators.DataRequired()])
    telephoneCode = SelectField('telephoneCode',choices=[(55, 55), (46, 46), (47, 47), (358, 358)], validators=[validators.DataRequired()])
    phonenumber = StringField('phonenumber', validators=[validators.DataRequired()])
    mail = StringField('mail', validators=[validators.DataRequired(), validators.Email()])

class AddAccountForm(FlaskForm):
    AccountType = SelectField('AccountType',choices=[('Personal','Personal'), ('Checking','Checking'), ('Savings','Savings')], validators=[validators.DataRequired()])

class WithdrawForm(FlaskForm):
    withdrawalAmount = IntegerField('withdrawalAmount', validators=[validators.DataRequired(), validate_positive])

class DepositForm(FlaskForm):
    depositAmount = IntegerField('depositAmount', validators=[validators.DataRequired(), validate_positive])

class TransferForm(FlaskForm):
    transferAmount = IntegerField('transferAmount', validators=[validators.DataRequired(), validate_positive])
    destinationAccountId = IntegerField('destinationAccountId', validators=[validators.DataRequired()])
    transactionType = SelectField('transactionType',choices=[('Debit','Debit'),('Credit','Credit')], validators=[validators.DataRequired()])

class NewUserForm(FlaskForm):
    mail = StringField('mail', validators=[validators.DataRequired(), validators.Email()])
    role = SelectField('role',choices=[('Cashier', 'Cashier'), ('Admin', 'Admin')], validators=[validators.DataRequired()])
    pw = PasswordField('pw', validators=[validators.DataRequired(), validators.Length(min = 6, max = 25), validators.EqualTo('pw_confirm')])
    pw_confirm = PasswordField('pw_confirm')

class EditUserForm(FlaskForm):
    mail = StringField('mail', validators=[validators.Email()])
    role = SelectField('role',choices=[('Cashier', 'Cashier'), ('Admin', 'Admin')])