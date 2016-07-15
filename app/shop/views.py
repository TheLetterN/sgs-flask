import random  #TMP
from flask import flash, redirect, render_template, request, session
from flask_login import current_user
from . import shop
from app import db
from app.shop.forms import AddProductForm
from app.shop.models import Customer, Product, Transaction, TransactionLine


@shop.route('/')
def index():
    """Main shop page."""
    choices = ['frogs', 'toads', 'salamanders']
    try:
        session['amphibian']
    except KeyError:
        session['amphibian'] = None
    if not session['amphibian']:
        session['amphibian'] = random.choice(choices)
    return('Your amphibian: {}'.format(session['amphibian']))


@shop.route('/add-to-cart', methods=('GET', 'POST'))
def add_to_cart():
    form = AddProductForm()
    if form.validate_on_submit:
        qty = form.quantity.data
        pn = form.number.data
        product = Product.query.filter(Product.number==pn).one_or_none()
        print(product)#TMP
        try:
            session['cart']
        except KeyError:
            session['cart'] = []
        product_dict = next(
            (d for d in session['cart'] if d['product number'] == pn),
            None
        )
        if product_dict:
            product_dict['quantity'] += qty
        else:
            product_dict = {'product number': pn, 'quantity': qty}
            session['cart'].append(product_dict)
        if not current_user.is_anonymous:
            if not current_user.customer_data:
                current_user.customer_data = Customer()
            customer = current_user.customer_data
            if not customer.current_transaction:
                customer.current_transaction = Transaction()
            line = next(
                (l for l in customer.current_transaction.lines if
                 l.product is product),
                None
            )
            if line:
                line.quantity += qty
            else:
                line = TransactionLine(product=product, quantity=qty)
                customer.current_transaction.lines.append(line)
            db.session.commit()
        flash('{0} of {1}'.format(qty, product.label))
        return redirect(request.args.get('origin'))


@shop.route('/cart')
def cart():
    if session['cart']:
        return str(session['cart'])
    else:
        return('No transaction')
