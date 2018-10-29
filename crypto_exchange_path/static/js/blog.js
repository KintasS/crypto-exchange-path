/*global $, document, Chart, LINECHART, data, options, window, setTimeout*/
$(document).ready(function() {

    'use strict';

    // ---------------------------------------------- //
    // Copy Link Tooltip
    // ---------------------------------------------- //

    // Activate tooltips
    // $('[data-toggle="tooltip"]').tooltip()

    // Copy link to clipboard when link is clicked
    $('.copy-link-tooltip').on('click', function() {
        var copyText = $(this).attr('data-clipboard-text');
        // Create temporal input to paste and then remove it
        var $temp = $("<input>");
        $("body").append($temp);
        $temp.val(copyText).select();
        document.execCommand("copy");
        $temp.remove();
        // $(this).tooltip('toggle')
    });


});