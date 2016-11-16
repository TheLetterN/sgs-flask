function fixQuantitySnip(item) {
    // Subtract 1 because snipcart adds 1 item when the button is clicked.
    var oldQuantity = item['quantity'] - 1;
    var fieldQuantity = parseInt($('#quantity-' + item['id']).val());
    if (!fieldQuantity || fieldQuantity <= 0) {  // input type "number" returns null if non-numeric value is in field.
        fieldQuantity = 1;
    }
    var quantity = fieldQuantity + oldQuantity;
    Snipcart.api.items.update(item['id'], { 'quantity': quantity });
    console.log("Successfully added " + fieldQuantity + " of item " + item['id'] + " to cart.");
};

function setSnipcartShippingMethods(address) {
    if (address.country == "US") {
        var cart = Snipcart.api.cart.get();
        if (cart['total'] > 100) {
            Snipcart.execute('config', 'allowed_shipping_methods', ['free-priority-shipping']);
        } else if (cart['total'] > 40) {
            Snipcart.execute('config', 'allowed_shipping_methods', ['free-shipping', 'usps-priority']);
        } else {
            Snipcart.execute('config', 'allowed_shipping_methods', ['usps-first-class', 'usps-priority']);
        }
    } else {
        Snipcart.execute('config', 'allowed_shipping_methods', ['usps-first-class-international']);
    }
};

// This is the function to edit if we want to change snipcart parameters during
// initialization.
function setupSnip () {
    Snipcart.subscribe('cart.ready', function () {
        Snipcart.api.configure('show_continue_shopping', true);
        Snipcart.api.configure('split_firstname_and_lastname', true);
        Snipcart.api.configure('show_cart_automatically', false);
        Snipcart.api.configure('credit_cards', [
            {'type': 'visa', 'display': 'Visa'},
            {'type': 'mastercard', 'display': 'Mastercard'},
            {'type': 'discover', 'display': 'Discover'}
        ]);
    });
    Snipcart.subscribe('item.added', fixQuantitySnip);
    Snipcart.subscribe('page.change', function (page) {
        if (page == 'shipping-method') {
            var cart = Snipcart.api.cart.get();
            setSnipcartShippingMethods(cart.shippingAddress);
        }
    });
    // Change 'NEXT STEP' button on first page of cart
    Snipcart.subscribe('cart.opened', function () {
        $('.snip-btn--right').text('SECURE CHECKOUT >');
    });
    Snipcart.execute('bind', 'billingaddress.changed', function (address) {
        if (address.shippingSameAsBilling) {
            setSnipcartShippingMethods(address);
        }
    });
    Snipcart.execute('bind', 'shippingaddress.changed', function (address) {
        setSnipcartShippingMethods(address);
    });
    Snipcart.execute('bind', 'cart.ready', function (cart) {
        if (cart.order) {
            setSnipcartShippingMethods(cart.order.shippingAddress);
        }
    });
    $(document).ready( function () {
        $('.snipcart-add-item').each( function () {
            $(this).on('click', function () {
                var name = $(this).attr('data-item-name');
                var sku = $(this).attr('data-item-id');
                var qty = $('#quantity-' + sku).val();
                if (parseInt(qty) > 1) {
                    var pkt = 'packets';
                } else {
                    var pkt = 'packet';
                }
                noty({
                    closeWith: ['button'],
                    timeout: 4000,
                    theme: 'sgs',
                    layout: 'top',
                    type: 'alert',
                    text: 'Added ' + qty + ' ' + pkt + ' of ' + name + ' to your shopping cart.\t[&nbsp;<span class="open-cart" onclick="Snipcart.api.modal.show();">View&nbsp;Cart</span>&nbsp;]'
                });
            });
        });
    });
};
