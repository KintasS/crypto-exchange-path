$(document).ready(function() {


    ///////////////////////////////////////////////////////////////////////////
    /////   TYPEAHEAD CODE
    ///////////////////////////////////////////////////////////////////////////
    function Comparator(a, b) {
        if (a.ranking < b.ranking) return -1;
        if (a.ranking > b.ranking) return 1;
        return 0;
    }

    var inputOrigCoinChanged = true;
    var inputDestCoinChanged = true;
    $.get("/static/data/coins.json", function(coinData) {

        // Typeahead for origin coin
        var $input_orig_coin = $("#input-orig-coin .typeahead");
        $input_orig_coin.typeahead({
            source: coinData,
            autoSelect: false,
            changeInputOnMove: false,
            showHintOnFocus: true,
            selectOnBlur: false,
            items: 50,
            item: '<li class="dropdown-item"><a class="dropdown-item" href="#" role="option"></a></li>',
            displayText: function(item) {
                return '<div class="d-flex align-items-center"><img class="mr-2" src="/static/img/coins/16/' + item.img + '" alt="" width="16" height="16"> ' +
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
            source: coinData,
            autoSelect: false,
            changeInputOnMove: false,
            showHintOnFocus: true,
            selectOnBlur: false,
            items: 50,
            item: '<li class="dropdown-item"><a class="dropdown-item" href="#" role="option"></a></li>',
            displayText: function(item) {
                return '<div class="d-flex align-items-center"><img class="mr-2" src="/static/img/coins/16/' + item.img + '" alt="" width="16" height="16"> ' +
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

    // Typeahead for origin location
    var inputOrigExchanges = []
    var $input_orig_loc = $("#input-orig-loc .typeahead");
    $input_orig_loc.typeahead({
        source: function(query, process) {
            // Open file with Exchange attributes
            $.get("/static/data/exchanges.json", function(exchangeData) {
                // Open file with exchanges for each coin
                $.get("/static/data/exchanges_by_coin.json", function(exchsByCoin) {
                    inputCoin = $('#orig_coin').val()
                    // If there is input coin, get exchanges for that coin
                    if ((inputOrigCoinChanged == true) && (inputCoin.length > 0)) {
                        if (inputCoin in exchsByCoin) {
                            inputOrigExchanges = exchsByCoin[inputCoin];
                        }
                        inputOrigCoinChanged = false;
                    }
                    // Generate JSON object with options to display in Typeahead
                    var returnValue = []
                    // If there was no coin properly field, display all exchanges
                    if (inputOrigExchanges.length == 0) {
                        for (const [key, value] of Object.entries(exchangeData)) {
                            returnValue.push(value);
                        }
                        return process(returnValue);
                        // If there was a coin, display only exchanges for that coin
                    } else {
                        for (var i = 0; i < inputOrigExchanges.length; i++) {
                            if (inputOrigExchanges[i] in exchangeData) {
                                returnValue.push(exchangeData[inputOrigExchanges[i]]);
                            }
                        }
                        return process(returnValue);
                    }
                }, 'json');
            }, 'json');
        },
        autoSelect: false,
        changeInputOnMove: false,
        showHintOnFocus: true,
        selectOnBlur: false,
        items: 100,
        item: '<li class="dropdown-item"><a class="dropdown-item" href="#" role="option"></a></li>',
        displayText: function(item) {
            if ((item.name == 'Bank') || (item.name == 'Wallet')) {
                return '<div class="font-weight-bold d-flex align-items-center"><img class="mr-2" src="/static/img/exchanges/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.name + '<span class="badge badge-warning ml-2">Default</span></div>'
            } else {
                return '<div class="d-flex align-items-center"><img class="mr-2" src="/static/img/exchanges/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.name + '</div>'
            }
        },
        highlighter: Object,
        afterSelect: function(item) {
            // Change input to the selected coin's longname
            $input_orig_loc.val(item.name).change();
        },
        sorter: function(items) {
            return items.sort(Comparator);
        }
    });

    // Typeahead for destination location
    var inputDestExchanges = []
    var $input_dest_loc = $("#input-dest-loc .typeahead");
    $input_dest_loc.typeahead({
        source: function(query, process) {
            // Open file with Exchange attributes
            $.get("/static/data/exchanges.json", function(exchangeData) {
                // Open file with exchanges for each coin
                $.get("/static/data/exchanges_by_coin.json", function(exchsByCoin) {
                    inputCoin = $('#dest_coin').val()
                    // If there is input coin, get exchanges for that coin
                    if ((inputDestCoinChanged == true) && (inputCoin.length > 0)) {
                        if (inputCoin in exchsByCoin) {
                            inputDestExchanges = exchsByCoin[inputCoin];
                        }
                        inputDestCoinChanged = false;
                    }
                    // Generate JSON object with options to display in Typeahead
                    var returnValue = []
                    // If there was no coin properly field, display all exchanges
                    if (inputDestExchanges.length == 0) {
                        for (const [key, value] of Object.entries(exchangeData)) {
                            returnValue.push(value);
                        }
                        return process(returnValue);
                        // If there was a coin, display only exchanges for that coin
                    } else {
                        for (var i = 0; i < inputDestExchanges.length; i++) {
                            if (inputDestExchanges[i] in exchangeData) {
                                returnValue.push(exchangeData[inputDestExchanges[i]]);
                            }
                        }
                        return process(returnValue);
                    }
                }, 'json');
            }, 'json');
        },
        autoSelect: false,
        changeInputOnMove: false,
        showHintOnFocus: true,
        selectOnBlur: false,
        items: 100,
        item: '<li class="dropdown-item"><a class="dropdown-item" href="#" role="option"></a></li>',
        displayText: function(item) {
            if ((item.name == 'Bank') || (item.name == 'Wallet')) {
                return '<div class="font-weight-bold d-flex align-items-center"><img class="mr-2" src="/static/img/exchanges/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.name + '<span class="badge badge-warning ml-2">Default</span></div>'
            } else {
                return '<div class="d-flex align-items-center"><img class="mr-2" src="/static/img/exchanges/16/' + item.img + '" alt="" width="16" height="16"> ' +
                    item.name + '</div>'
            }
        },
        highlighter: Object,
        afterSelect: function(item) {
            // Change input to the selected coin's longname
            $input_dest_loc.val(item.name).change();
        },
        sorter: function(items) {
            return items.sort(Comparator);
        }
    });



    ///////////////////////////////////////////////////////////////////////////
    /////   ADD SPACE TO AMOUNT INPUT
    ///////////////////////////////////////////////////////////////////////////

    // Adds an space to the input amount so that italics don't get cut off.
    $('#orig_amt').on('change', function() {
        var value = $('#orig_amt').val();
        if (value.length > 0) {
            value = value.replace(' ', '');
            $('#orig_amt').val(value + " ");
        }
    });



    ///////////////////////////////////////////////////////////////////////////
    /////   SEARCH INPUT ACTIONS
    ///////////////////////////////////////////////////////////////////////////

    // Checks whether there is input in the forms to make it bold
    function CheckSearchInput($input) {
        var changeFont = false;
        var value = $input.val();
        if (value.length > 0) {
            $input.css({
                'color': 'white'
            });
        }
    }

    // Actions if Form inputs change
    $('.track-filled').on('change', function() {
        CheckSearchInput($(this));
        // Check if coin changed to search for exchanges in Typeahead
        var id = $(this).attr('id');
        if (id == 'orig_coin') {
            inputOrigCoinChanged = true;
            inputOrigExchanges = [];
        } else if (id == 'dest_coin') {
            inputDestCoinChanged = true;
            inputDestExchanges = [];
        }
    });

    // Check when page loads (in case form was prefilled!)
    // CheckSearchInput($('#orig_amt'));
    // CheckSearchInput($('#orig_coin'));
    // CheckSearchInput($('#orig_loc'));
    // CheckSearchInput($('#dest_coin'));
    // CheckSearchInput($('#dest_loc'));




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
    //   - Show processing modal (if form was filled!)
    //   - Replace ',' by '.' in origin amount
    //   - If Origin location and Destination location are emtpy, fill them
    $('#submit-btn').on('click', function() {
        // Hide current results being displayed
        $('#results').fadeOut(200);
        $('#intro').fadeOut(200);
        // Hide 'Connecting options'
        $('#options-collapse').collapse('hide');
        // Show processing modal (if form was filled!)
        if ($('#dest_coin').val().length > 0 &&
            $('#orig_amt').val().length > 0 &&
            $('#orig_coin').val().length > 0) {
            $('#processing-modal').modal('show')
        }
        // Replace ',' by '.' in origin amount
        var $origAmt = $('#orig_amt')
        $origAmt.val($origAmt.val().replace(',', '.'))
        // If Origin location is empty, fill it
        var $origLoc = $('#orig_loc')
        var value = $origLoc.val();
        if (value.length == 0) {
            $origLoc.val('(Default)');
        }
        // If Destination location is empty, fill it
        var $destLoc = $('#dest_loc')
        var value = $destLoc.val();
        if (value.length == 0) {
            $destLoc.val('(Default)');
        }
    });





    ///////////////////////////////////////////////////////////////////////////
    /////   CURRENCY SELECTION
    ///////////////////////////////////////////////////////////////////////////

    // Actions if a currency is selected:
    //   - Replace selected currency
    //   - Hide results
    //   - If inputs are filled, send form automatically
    $('#currency-btn .dropdown-item').on('click', function() {
        currentCurrency = $('#currency-btn button').attr('data-currency');
        selectedCurrency = $(this).attr('data-currency');
        if (currentCurrency != selectedCurrency) {
            // Replace selected currency
            $('#currency-btn button').attr('data-currency', selectedCurrency);
            $('#currency-btn button').html('<b>' + $(this).html() + '</b>');
            // Change selected option in input form
            var $option = $('#currency option[value=' + selectedCurrency + ']');
            $option.prop('selected', true);
            // Hide results
            $('#results').fadeOut(200);
            // If inputs are filled, send form automatically
            if ($('#dest_coin').val().length > 0 &&
                $('#orig_amt').val().length > 0 &&
                $('#orig_coin').val().length > 0) {
                $('#submit-btn').trigger("click");
            }
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
    /////   OPEN COLLAPSES AUTOMATICALLY
    ///////////////////////////////////////////////////////////////////////////

    // Open 'Advanced Search' collapse in case of error in location inputs
    var errors = $("section#search-canvas .location-error")
    if (errors.length > 0) {
        $('#options-collapse').collapse('show');
    }

    // Open the first collapse item to show details
    $("#results .collapse").first().collapse('show')
    $("#results .collapse-animation").first().find("i:first").toggleClass("rotateimg180");



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
    /////   BACK TO TOP BUTTON
    ///////////////////////////////////////////////////////////////////////////

    console.log("entro 5")

    // When the user scrolls down 400px from the top of the document, show the button
    window.onscroll = function() {
        scrollFunction()
    };

    var scrollToAppear = 400;

    function scrollFunction() {
        if (document.body.scrollTop > scrollToAppear || document.documentElement.scrollTop > scrollToAppear) {
            document.getElementById("myBtn").style.display = "block";
        } else {
            document.getElementById("myBtn").style.display = "none";
        }
    }

    // When the user clicks on the button, scroll to the top of the document
    $("#myBtn").click(function() {
        document.body.scrollTop = 0; // For Safari
        document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
    });


    ///////////////////////////////////////////////////////////////////////////
    /////   GOOGLE ANALYTICS EVENTS
    ///////////////////////////////////////////////////////////////////////////


    // EXCHANGE SEARCHES //

    $('#submit-btn').on('click', function() {
        var formAction = $("#search-form").attr('action');
        var searchCoins = formAction.replace('/exchanges/result/', '');
        gtag('event', 'Exchange Engine Search', {
            'event_category': 'Click',
            'event_label': 'Exchange Engine Search: ' + String(searchCoins)
        });
    });

    // WEB ACTIONS //

    // 'Trending Searches Click' Event
    $(".trending-searches-btn").click(function() {
        var dataClick = $(this).attr("data-click");
        gtag('event', 'Trending search', {
            'event_category': 'Click',
            'event_label': 'Trending search: ' + String(dataClick)
        });
    });

    // 'Send Feedback' Event
    $(".send-feedback-btn").click(function() {
        var feedbackTopic = $("#feedback-topic").val();
        var feedbackSuject = $("#feedback-subject").val();
        var feedbackText = $("#feedback-text").val();
        if ((feedbackTopic != '(Select a topic)') && (feedbackSuject != '') && (feedbackText != '')) {
            gtag('event', 'Send feedback', {
                'event_category': 'Click',
                'event_label': 'Send feedback: ' + String(feedbackTopic)
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

    // 'Referral Result promo link' Event
    $("#results .promo-link").click(function() {
        var exchangeName = $(this).attr("data-exch");
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Result Promo link'
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