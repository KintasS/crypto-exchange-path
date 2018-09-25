$(document).ready(function() {


    ///////////////////////////////////////////////////////////////////////////
    /////   TYPEAHEAD CODE
    ///////////////////////////////////////////////////////////////////////////
    function Comparator(a, b) {
        if (a.ranking < b.ranking) return -1;
        if (a.ranking > b.ranking) return 1;
        return 0;
    }

    $.get("/static/data/coins.json", function(data) {

        // Typeahead for origin coin
        var $input_orig_coin = $("#input-orig-coin .typeahead");
        $input_orig_coin.typeahead({
            source: data,
            autoSelect: true,
            changeInputOnMove: false,
            items: 20,
            displayText: function(item) {
                return '<div class="d-flex align-items-center"><img class="mr-1" src="/static/img/coins/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.long_name + ' (' + item.name + ')</div>'
            },
            highlighter: Object,
            afterSelect: function(item) {
                // Change input to the selected coin's longname
                $input_orig_coin.val(item.long_name).change();
                // Change Search Form action (i.e. it's URL)
                var formAction = $("#search-form").attr('action');
                var newAction = formAction.replace(/result\/.*\+/, 'result/' + item.id + '+');
                $("#search-form").attr('action', newAction);
            },
            sorter: function(items) {
                return items.sort(Comparator);
            }
        });

        // Typeahead for destination coin
        var $input_dest_coin = $("#input-dest-coin .typeahead");
        $input_dest_coin.typeahead({
            source: data,
            autoSelect: true,
            changeInputOnMove: false,
            items: 20,
            displayText: function(item) {
                return '<div class="d-flex align-items-center"><img class="mr-1" src="/static/img/coins/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.long_name + ' (' + item.name + ')</div>'
            },
            highlighter: Object,
            afterSelect: function(item) {
                // Change input to the selected coin's longname
                $input_dest_coin.val(item.long_name).change();
                // Change Search Form action (i.e. it's URL)
                var formAction = $("#search-form").attr('action');
                var newAction = formAction.replace(/\+.*/, '+' + item.id);
                $("#search-form").attr('action', newAction);

            },
            sorter: function(items) {
                return items.sort(Comparator);
            }
        });

    }, 'json');


    ///////////////////////////////////////////////////////////////////////////
    /////   EXCHANGE OPTIONS CODE
    ///////////////////////////////////////////////////////////////////////////

    var $checkboxes = $('#exchange-options input');
    var $multiOptions = $('#exchanges option');

    // Actions if 'Select All' button is clicked
    $('#select-all-btn').on('click', function() {
        $checkboxes.each(function() {
            $(this).prop('checked', true);
        });
        $multiOptions.each(function() {
            $(this).prop('selected', true);
        });
    });

    // Actions if 'Select All' button is clicked
    $('#deselect-all-btn').on('click', function() {
        $checkboxes.each(function() {
            $(this).prop('checked', false);
        });
        $multiOptions.each(function() {
            $(this).prop('selected', false);
        });
    });

    // Actions if a checkbox is clicked
    $checkboxes.on('change', function() {
        var exch = $(this).attr('id').replace('exch-', '');
        var $option = $('#exchanges option[value=' + exch + ']');
        if ($(this).is(":checked")) {
            $option.prop('selected', true);
        } else {
            $option.prop('selected', false);
        }
    });

    ///////////////////////////////////////////////////////////////////////////
    /////   SUBMIT BUTTON ACTIONS
    ///////////////////////////////////////////////////////////////////////////

    // Actions when submit button is clicked:
    //   - Hide current results being displayed
    //   - Hide 'Connecting options'
    //   - Show processing modal
    $('#submit-btn').on('click', function() {
        $('#results').fadeOut(200);
        $('#intro').fadeOut(200);
        $('#options-collapse').collapse('hide');
        $('#processing-modal').modal('show')
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   CURRENCY SELECTION
    ///////////////////////////////////////////////////////////////////////////

    // Actions if a currency is selected:
    //   - Replace selected currency
    //   - Hide results
    $('#currency-btn .dropdown-item').on('click', function() {
        currentCurrency = $('#currency-btn button').attr('data-currency');
        selectedCurrency = $(this).attr('data-currency');
        if (currentCurrency != selectedCurrency) {
            // Replace selected currency
            $('#currency-btn button').attr('data-currency', selectedCurrency);
            $('#currency-btn button').html('<b>' + $(this).html() + '</b>');
            // Hide results
            $('#results').fadeOut(200);
            // Change selected option in input form
            var $option = $('#currency option[value=' + selectedCurrency + ']');
            $option.prop('selected', true);
            // Change currency in navbar links & other site navigation links
            // $('.curr-change').each(function() {
            //     oldLink = $(this).attr('href');
            //     newLink = oldLink.replace('currency%3D' + currentCurrency, 'currency%3D' + selectedCurrency)
            //     $(this).attr('href', newLink);
            // });
        }
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   BLOCK LINKS (IN RESULTS)
    ///////////////////////////////////////////////////////////////////////////


    // Show URL on Mouse Hover
    // Open in new window
    $(".referral-summary-link").click(function() {
        window.open($(this).find("a:first").attr("href"));
        return false;
    });
    $(".referral-summary-link").hover(function() {
        $(this).find("a:first").css({
            color: '#4285F4'
        });
        return false;
    }, function() {
        $(this).find("a:first").css({
            color: '#212529'
        });
        return false;
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   AUTO-SEARCH
    ///////////////////////////////////////////////////////////////////////////

    // If auto_search='True', run search automatically
    var cond = $('#results').attr('data-auto-search')
    if (cond == "True") {
        $('#submit-btn').trigger("click");
    }

    ///////////////////////////////////////////////////////////////////////////
    /////   COLLAPSE-ANIMATIONS (CHEVRON ROTATION)
    ///////////////////////////////////////////////////////////////////////////

    // Rotate chevron image when collapse button is clicked
    // Avoid rotation when content is collpsing!
    $(".collapse-animation").click(function() {
        var $collapseElement = $($(this).attr("href"));
        if (!$collapseElement.hasClass("collapsing")) {
            $(this).find("i:first").toggleClass("rotateimg180");
        }
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   GOOGLE ANALYTICS EVENTS
    ///////////////////////////////////////////////////////////////////////////

    // WEB ACTIONS //

    // 'Trending Searches Click' Event
    $(".trending-searches-btn").click(function() {
        var dataClick = $(this).attr("data-click");
        gtag('event', 'Trending searches', {
            'event_category': 'Click',
            'event_label': dataClick
        });
    });

    // 'Send Feedback' Event
    $(".send-feedback-btn").click(function() {
        var feedbackTopic = $("#feedback-topic").val();
        var feedbackSuject = $("#feedback-subject").val();
        var feedbackText = $("#feedback-text").val();
        if ((feedbackTopic != '(Select a topic)') && (feedbackSuject != '') && (feedbackText != '')) {
            gtag('event', 'Send feedback', {
                'event_category': 'Click'
            });
        }
    });

    // REDIRECT EVENTS //

    // 'Referral Popular Exchanges Button' Event
    $(".referral-popular-exch").click(function() {
        var exchangeName = $(this).attr("data-exch");
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Home - Popular exchanges'
        });
    });

    // 'Referral Popular Wallet Button' Event
    $(".referral-popular-wallet").click(function() {
        var walletName = $(this).attr("data-wallet");
        gtag('event', walletName, {
            'event_category': 'Redirect - Wallet',
            'event_label': 'Home - Popular wallets'
        });
    });

    // 'Referral Result Button' Event
    $(".referral-result-btn").click(function() {
        var exchangeName = $(this).attr("data-exch");
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result button'
        });
    });

    // 'Referral Result summary link' Event
    $(".referral-summary-link").click(function() {
        var exchangeName = $(this).attr("data-exch");
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result Summary link'
        });
    });

    // 'Referral Result detail link 1' Event (1 = first detail column)
    $(".referral-detail-link-1").click(function() {
        var exchangeName = $(this).html();
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result Detail link (Column 1)'
        });
    });
    // 'Referral Result detail link 2' Event (2 = first detail column)
    $(".referral-detail-link-2").click(function() {
        var exchangeName = $(this).html();
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result Detail link (Column 2)'
        });
    });
    // 'Referral Result detail link 3' Event (3 = first detail column)
    $(".referral-detail-link-3").click(function() {
        var exchangeName = $(this).html();
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result Detail link (Column 3)'
        });
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   OTHER ACTIONS
    ///////////////////////////////////////////////////////////////////////////

    // Activate tooltips
    $('[data-toggle="tooltip"]').tooltip()

    // If errors in feedback, open modal directly
    var cond = $('#modalFeedbackForm').attr('data-modal-open')
    if (cond == "True") {
        $('#modalFeedbackForm').modal('show');
    }

});