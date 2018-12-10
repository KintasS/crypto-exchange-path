$(document).ready(function() {


    ///////////////////////////////////////////////////////////////////////////
    /////   FILTERS ASSET CARDS ON INPUT
    ///////////////////////////////////////////////////////////////////////////

    $assetCards = $('section.exchange-fees .asset-col');
    $filterAssetInput = $('#filter-asset-input');
    $filterAssetInput.val('')

    $filterAssetInput.on('input', function() {
        var value = $filterAssetInput.val().toUpperCase();
        // Check all cards to filter depending on input
        $assetCards.each(function() {
            if (value.length > 0) {
                assetID = $(this).attr('data-coin-id').toUpperCase();
                assetName = $(this).attr('data-coin-name').toUpperCase();
                if ((assetID.indexOf(value) >= 0) || (assetName.indexOf(value) >= 0)) {
                    $(this).removeClass("d-none")
                } else {
                    $(this).addClass("d-none")
                }
            } else {
                // If filter is empty, show all cards
                $(this).removeClass("d-none")
            }
        });

    });

    ///////////////////////////////////////////////////////////////////////////
    /////   GOOGLE ANALYTICS EVENTS (Search for 'gtag' in the rest of code!)
    ///////////////////////////////////////////////////////////////////////////


    // REDIRECT EVENTS //

    // 'Referral Popular Exchanges Button' Event
    $(".referral-exchfees-exch").click(function() {
        var exchangeName = $(this).attr("data-exch");
        gtag('event', exchangeName, {
            'event_category': 'Redirect - Exchange',
            'event_label': 'Exchange Fees'
        });
    });


});