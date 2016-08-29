function setVisibleStateField(country) {
    var dsp = "block";  // Default display mode for visible.
    var usa = document.getElementById('usa-state');
    var can = document.getElementById('can-state');
    var aus = document.getElementById('aus-state');
    var unlisted = document.getElementById('unlisted-state');

    if (country.value == 'USA') {
        usa.style.display = dsp;
        can.style.display = "none";
        aus.style.display = "none";
        unlisted.style.display = "none";
    } else if (country.value == 'CAN') {
        usa.style.display = "none";
        can.style.display = dsp;
        aus.style.display = "none";
        unlisted.style.display = "none";
    } else if (country.value == 'AUS') {
        usa.style.display = "none";
        can.style.display = "none";
        aus.style.display = dsp;
        unlisted.style.display = "none";
    } else {
        usa.style.display = "none";
        can.style.display = "none";
        aus.style.display = "none";
        unlisted.style.display = dsp ;
    }
};
