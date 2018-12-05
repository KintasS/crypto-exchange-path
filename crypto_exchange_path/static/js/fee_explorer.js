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




});