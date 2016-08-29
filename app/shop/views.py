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
    ShippingForm,
    ShoppingCartForm
)
from app import db
from app.shop.models import Customer, Order


@shop.route('/add-to-cart/<product_number>', methods=('GET', 'POST'))
def add_to_cart(product_number):
    form = AddProductForm(prefix=product_number)
    if form.validate_on_submit:
        qty = form.quantity.data
        pn = product_number
        current_order = Order.load(current_user)
        if not current_order:
            current_order = Order()
            if not current_user.is_anonymous:
                current_user.current_order = current_order
        line = current_order.add_line(product_number=pn, quantity=qty)
        current_order.save()
        flash(
            'Added {0} of "{1}" to shopping cart.'.format(line.quantity,
                                                          line.label)
        )
        return redirect(request.args.get('origin') or url_for('shop.cart'))


@shop.route('/cart', methods=['GET', 'POST'])
def cart():
    current_order = Order.load(current_user)
    form = ShoppingCartForm(obj=current_order)
    try:
        if current_order.status == Order.PENDING_REVIEW:
            form.checkout.label.text = 'Review Order'
    except AttributeError:
        pass
    if form.validate_on_submit():
        for line in form.lines.entries:
            current_order.change_line_quantity(
                line.product_number.data,
                line.quantity.data
            )
        current_order.save()
        if form.checkout.data:
            return redirect(url_for('shop.shipping'))
        if form.save.data:
            flash('Changes saved.')
        return redirect(url_for('shop.cart'))
    else:
        print(form.errors)
    return render_template(
        'shop/cart.html',
        current_order=current_order,
        form=form
    )


@shop.route('/remove_product/<product_number>')
def remove_product(product_number):
    """Remove the line containing given product from the cart."""
    current_order = Order.load(current_user)
    origin = request.args.get('origin')
    line = current_order.get_line(product_number)
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
    current_order.delete_line(line)
    return redirect(origin or url_for('shop.cart'))


@shop.route('/undo_remove_product/<product_number>/<int:quantity>')
def undo_remove_product(product_number, quantity):
    current_order = Order.load(current_user)
    if not current_order:
        current_order = Order()
        if not current_user.is_anonymous:
            current_user.current_order = current_order
    line = current_order.add_line(
        product_number=product_number,
        quantity=quantity
    )
    current_order.save()

    flash('Returned {} of "{}" to cart.'.format(line.quantity, line.label))
    return redirect(request.args.get('origin') or url_for('shop.cart'))


@shop.route('/shipping', methods=['GET', 'POST'])
def shipping():
    form = ShippingForm()
    form.address.set_selects(filter_noship=True)
    order = Order.load(current_user)
    customer = order.customer
    if not customer:
        customer = Customer.get_from_session()
    if form.validate_on_submit():
        if not customer:
            customer = Customer()
            db.session.add(customer)
        if customer.current_order is not order:
            customer.current_order = order
        customer.shipping_address = form.address.get_or_create_address()
        if not form.comments.data:
            form.comments.data = None
        if form.comments.data != order.shipping_comments:
            order.shipping_comments = form.comments.data
        db.session.commit()
        return redirect(url_for('shop.billing'))
    try:
        form.address.populate_from_address(customer.shipping_address)
    except AttributeError:
        form.address.country.data = 'USA'
    return render_template('shop/shipping.html', form=form, order=order)


@shop.route('/billing', methods=['GET', 'POST'])
def billing():
    return('Nothing yet.')


@shop.route('/checkout', methods=['GET', 'POST'])
def checkout():
    guest = request.args.get('guest') or False
    current_order = Order.load(current_user)
    form = CheckoutForm()
    form.billing_address.set_selects()
    form.shipping_address.set_selects(filter_noship=True)
    customer = current_order.customer
    if not customer:
        customer = Customer.get_from_session()
    if form.validate_on_submit():
        print('Nonce: {}'.format(form.nonce.data))
        if not customer:
            customer = Customer()
        if customer.current_order is not current_order:
            customer.current_order = current_order
        if not current_user.is_anonymous and not current_user.customer_data:
            current_user.customer_data = customer
        if not form.billing_address.equals_address(customer.billing_address):
            customer.billing_address = (
                form.billing_address.get_or_create_address()
            )
        if not form.shipping_address.equals_address(customer.shipping_address):
            if form.billing_address.form == form.shipping_address.form:
                customer.shipping_address = customer.billing_address
            else:
                customer.shipping_address = (
                    form.shipping_address.get_or_create_address()
                )
        if form.shipping_comments.data:
            current_order.shipping_comments = form.shipping_notes.data
        elif current_order.shipping_comments:
            current_order.shipping_comments = None
        current_order.status = Order.PENDING_REVIEW
        db.session.add_all([current_order, customer])
        db.session.commit()
        if current_user.is_anonymous:
            customer.save_id_to_session()
        flash('All fields valid.')
        return redirect(url_for('shop.review_order'))
    # Since as of writing this wtforms has a bug in which `None` is coerced
    # to a string in select fields, I'm using whether or not `form.submit` has
    # been pressed to know if the default countries need to be set or not. -N
    if not form.review_order.data:
        try:
            form.billing_address.populate_from_address(
                customer.billing_address
            )
            form.shipping_address.populate_from_address(
                customer.shipping_address
            )
        except AttributeError:
            form.billing_address.country.data = 'USA'
            form.shipping_address.country.data = 'USA'
        if current_order.shipping_comments:
            form.shipping_comments.data = current_order.shipping_notes
    return render_template('shop/checkout.html',
                           current_order=current_order,
                           guest=guest,
                           form=form)


@shop.route('/review_order')
def review_order():
    if current_user.is_anonymous:
        customer = Customer.get_from_session()
    else:
        customer = current_user.customer_data
    return render_template(
        'shop/review.html',
        current_order=customer.current_order
    )


# TODO: Remove these views when no longer needed!
@shop.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('shop.cart'))


@shop.route('/show_session')
def show_session():
    return str(session)
