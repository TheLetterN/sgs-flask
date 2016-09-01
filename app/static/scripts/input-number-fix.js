$("input[type=number]").each( function () {
    $(this).on('blur', function () {
        var val = parseInt($(this).val());
        var min = parseInt($(this).prop('min'));
        if (!isNaN(min) && (!val || val < min)) {
            $(this).val(min);
        }
    });
});
