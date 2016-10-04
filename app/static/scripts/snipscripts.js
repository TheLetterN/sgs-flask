function snipify() {
    function ctms() {
      return (new Date()).getTime();
    };
    var st = ctms();
    var $cultivars = $('div.Cultivar');
    $cultivars.each( function () {
        var name = $(this).find('.Cultivar_em').text().toUpperCase().trim() + ', ' + $(this).find('.Cultivar_h3').clone().children().remove().end().text().toUpperCase().trim();
        var dandp = $(this).find('.Cultivar_table_size_price').text().split('-');
        var items = {
            'id': $(this).find('input[name=PartNo]').prop('value'),
            'name': name,
            'description': dandp[0].trim(),
            'price': dandp[1].trim().replace('$', ''),
            'url': $(this).find('input[name=Referer]').prop('value')
        }
        var $form = $(this).find('form');
        $form.find('input[type=hidden]').remove();
        var $qtyinput = $form.find('input[name=Qty]');
        var qtyid = 'quantity-' + items['id'];
        $qtyinput.prop('type', 'number');
        $qtyinput.prop('name', qtyid);
        $qtyinput.prop('id', qtyid);
        $qtyinput.prop('min', '1');
        $form.replaceWith($form.contents());

        var $button = $(this).find('button');
        $button.addClass('snipcart-add-item');
        $button.prop('type', 'button');
        $button.data('item-id', items['id']);
        $button.data('item-name', items['name']);
        $button.data('item-description', items['description']);
        $button.data('item-price', items['price']);
        $button.data('item-url', items['url']);
    });
    var $cartlink = $('.Page_header-view-cart-link');
    $cartlink.prop('href', '#');
    $cartlink.addClass('snipcart-checkout');
    var tt = ctms() - st;
    console.log('Snipified page in ' + tt.toString() + ' milliseconds.');
};

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
        if (cart['total'] > 40) {
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
    Snipcart.api.configure('show_continue_shopping', true);
    Snipcart.api.configure('split_firstname_and_lastname', true);
    Snipcart.subscribe('item.added', fixQuantitySnip);
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

};
