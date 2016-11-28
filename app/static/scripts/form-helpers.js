function make_id(val) {
    if (val[0] != '#') {
        return '#' + val
    } else {
        return val
    }
}

function populate_on_blur(source_id, target_id, cb) {
    if (!cb) {
        cb = function (data) { return data; };
    }
    source_id = make_id(source_id);
    target_id = make_id(target_id);
    $(source_id).on('blur', function () {
        if (!$(target_id).val() && $(source_id).val()) {
            $(target_id).val(cb($(source_id).val()));
        }
    });
}

function slugify(text) {
    return text.toString().toLowerCase().trim()
        .replace(/\s+/g, '-')
        .replace(/&/g, '-and-')
        .replace(/[^\w\-]+/g, '')
        .replace(/\-\-+/g, '-');
}
