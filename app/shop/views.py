# -*- coding: utf-8 -*-
# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from . import shop
from app.shop.forms import (
    AddProductForm,
    CheckoutForm,
    ShoppingCartForm
)
from app.shop.models import Transaction


@shop.route('/add-to-cart/<product_number>', methods=('GET', 'POST'))
def add_to_cart(product_number):
    form = AddProductForm(prefix=product_number)
    if form.validate_on_submit:
        qty = form.quantity.data
        pn = product_number
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
    origin = request.args.get('origin')
    line = cur_trans.get_line(product_number)
    flash(
        'Removed {} of "{}" from cart. [<a href="{}">UNDO</a>]'.format(
            line.quantity,
            line.label,
            url_for(
                'shop.undo_remove_product',
                product_number=line.product_number,
                quantity=line.quantity,
                origin=origin
            )
        )
    )
    cur_trans.delete_line(line)
    return redirect(origin or url_for('shop.cart'))


@shop.route('/undo_remove_product/<product_number>/<int:quantity>')
def undo_remove_product(product_number, quantity):
    cur_trans = Transaction.load(current_user)
    if not cur_trans:
        cur_trans = Transaction()
        if not current_user.is_anonymous:
            current_user.current_transaction = cur_trans
    line = cur_trans.add_line(product_number=product_number, quantity=quantity)
    cur_trans.save()

    flash('Returned {} of "{}" to cart.'.format(line.quantity, line.label))
    return redirect(request.args.get('origin') or url_for('shop.cart'))


@shop.route('/checkout')
def checkout():
    form = CheckoutForm()
    form.billing_address.set_selects()
    form.shipping_address.set_selects(filter_noship=True)
    if form.validate_on_submit():
        pass #TODO
    form.billing_address.country.data = 'USA'
    form.shipping_address.country.data = 'USA'
    return render_template('shop/checkout.html', form=form)


# TODO: Remove these views when no longer needed!
@shop.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('shop.cart'))


@shop.route('/show_session')
def show_session():
    return str(session['cart'])
