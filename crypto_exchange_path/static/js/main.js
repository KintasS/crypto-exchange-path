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
                $input_orig_coin.val(item.long_name).change();
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
                $input_dest_coin.val(item.long_name).change();
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
        console.log("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        console.log("currentCurrency")
        console.log("selectedCurrency")
        if (currentCurrency != selectedCurrency) {
            // Replace selected currency
            $('#currency-btn button').attr('data-currency', selectedCurrency);
            $('#currency-btn button').html('<b>' + $(this).html() + '</b>');
            // Hide results
            $('#results').fadeOut(200);
            // Change selected option in input form
            var $option = $('#currency option[value=' + selectedCurrency + ']');
            console.log("llego111")
            $option.prop('selected', true);
        }
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