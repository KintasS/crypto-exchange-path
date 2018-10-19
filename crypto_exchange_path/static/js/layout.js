$(document).ready(function() {

    ///////////////////////////////////////////////////////////////////////////
    /////   ACTIVATE NAV-LINK
    ///////////////////////////////////////////////////////////////////////////

    // Get active selection and Add 'active' class to the active nov-link
    var activeSection = $('#navlink-selector').attr('data-active');
    $('#' + activeSection).addClass('active');


});