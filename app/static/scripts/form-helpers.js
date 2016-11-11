function make_id(val) {
    if (val[0] != '#') {
        return '#' + val
    } else {
        return val
    }
}

function populate_on_blur(source_id, target_id, options) {
    source_id = make_id(source_id);
    target_id = make_id(target_id);
    options = options || {};
    var prefix = options.prefix || "";
    var postfix = options.postfix || "";
    $(source_id).on('blur', function () {
        if (!$(target_id).val() && $(source_id).val()) {
            $(target_id).val(prefix + $(source_id).val() + postfix);
        }
    });
}
