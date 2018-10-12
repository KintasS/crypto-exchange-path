/*global $, document, Chart, LINECHART, data, options, window, setTimeout*/
$(document).ready(function() {

    'use strict';

    // ------------------------------------------------------- //
    // Equalixe height
    // ------------------------------------------------------ //
    function equalizeHeight(x, y) {
        var textHeight = $(x).height();
        $(y).css('min-height', textHeight);
    }
    equalizeHeight('.featured-posts .text', '.featured-posts .image');

    $(window).resize(function() {
        equalizeHeight('.featured-posts .text', '.featured-posts .image');
    });


    // ---------------------------------------------- //
    // Preventing URL update on navigation link click
    // ---------------------------------------------- //
    $('.link-scroll').bind('click', function(e) {
        var anchor = $(this);
        $('html, body').stop().animate({
            scrollTop: $(anchor.attr('href')).offset().top + 2
        }, 700);
        e.preventDefault();
    });


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