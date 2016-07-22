from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from . import shop
from app import db
from app.shop.forms import (
    AddProductForm,
    ShoppingCartForm
)
from app.shop.models import Customer, Product, Transaction, TransactionLine


@shop.route('/add-to-cart', methods=('GET', 'POST'))
def add_to_cart():
    form = AddProductForm()
    if form.validate_on_submit:
        qty = form.quantity.data
        pn = form.number.data
        try:
            cur_trans = current_user.customer_data.current_transaction
        except AttributeError:
            cur_trans = None
        if not cur_trans:
            try:
                cur_trans = Transaction.from_session_data(session['cart'])
            except KeyError:
                cur_trans = Transaction()
        line = next(
            (l for l in cur_trans.lines if l.product_number == pn),
            None
        )
        if line:
            # Don't create multiple lines of the same product.
            line.quantity += qty
            product = line.product
        else:
            product = Product.query.filter(Product.number == pn).one_or_none()
            line = TransactionLine(product=product, quantity=qty)
            cur_trans.lines.append(line)
        try:
            if cur_trans is not current_user.customer_data.current_transaction:
                current_user.customer_data.current_transaction = cur_trans
        except AttributeError:
            if not current_user.is_anonymous:
                if not current_user.customer_data:
                    current_user.customer_data = Customer()
                current_user.customer_data.current_transaction = cur_trans
        try:
            if current_user.customer_data.current_transaction is cur_trans:
                db.session.commit()
        except AttributeError:
            pass
        session['cart'] = cur_trans.session_data
        flash(
            'Added {0} of "{1}" to shopping cart.'.format(qty, product.label)
        )
        return redirect(request.args.get('origin'))


@shop.route('/cart', methods=['GET', 'POST'])
def cart():
    cur_trans = Transaction.load(current_user)
    form = ShoppingCartForm(obj=cur_trans)
    if form.validate_on_submit():
        if form.save.data:
            for line in form.lines.entries:
                cur_trans.change_line_quantity(
                    line.product_number.data,
                    line.quantity.data
                )
            cur_trans.save()
            flash('Changes saved.')
        elif form.checkout.data:
            flash('Check this out.')
        return redirect(url_for('shop.cart'))
    else:
        print(form.errors)
    return render_template('shop/cart.html', cur_trans=cur_trans, form=form)
