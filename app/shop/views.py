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
        cur_trans = Transaction.load(current_user)
        if not cur_trans:
            cur_trans = Transaction()
            if not current_user.is_anonymous:
                current_user.current_transaction = cur_trans
        line = cur_trans.add_line(product_number=pn, quantity=qty)
        cur_trans.save()
        flash(
            'Added {0} of "{1}" to shopping cart.'.format(line.quantity,
                                                          line.label)
        )
        return redirect(request.args.get('origin') or url_for('shop.cart'))


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


@shop.route('/remove_product/<product_number>')
def remove_product(product_number):
    """Remove the line containing given product from the cart."""
    cur_trans = Transaction.load(current_user)
    line = cur_trans.get_line(product_number)
    flash ('Removed "{}" from cart.'.format(line.label))
    cur_trans.delete_line(line)
    return redirect(request.args.get('origin') or url_for('shop.cart'))


@shop.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('shop.cart'))
