// Functions to support the optimizter page


function addStatsToBody(data, statsTableBody) {




    for (var i = 0; data.length; i++){
        var newRow   = statsTableBody.insertRow();

        var newAID  = newRow.insertCell(0);
        var newText  = document.createTextNode(data[i].aid);
        newAID.appendChild(newText);

        var newSens  = newRow.insertCell(1);
        var newText  = document.createTextNode(data[i].Sensitivity);
        newSens.appendChild(newText);

        var newSpec  = newRow.insertCell(2);
        var newText  = document.createTextNode(data[i].Specificity);
        newSpec.appendChild(newText);

        var newCCR  = newRow.insertCell(3);
        var newText  = document.createTextNode(data[i].CCR);
        newCCR.appendChild(newText);

    }

}


function refreshProfile() {

    // replaces all the profile data on the optimizer page
    // and also replorts the heatmap

    var e = document.getElementById("profile-selection");
    var currentProfile = e.options[e.selectedIndex].value;

    var queryUrl = $SCRIPT_ROOT + "get_bioprofile/" + currentProfile;
    var profile_data = JSON.parse(getResponseFromURL(queryUrl));


    var tsElement = document.getElementById('this_ts');
    tsElement.innerHTML = profile_data.meta.training_set;

    var tsElement = document.getElementById('cmps');
    tsElement.innerHTML = profile_data.meta.num_cmps;

    var tsElement = document.getElementById('aids');
    tsElement.innerHTML = profile_data.meta.num_aids;

    var tsElement = document.getElementById('tot_acts');
    tsElement.innerHTML = profile_data.meta.num_total_actives;

    var tsElement = document.getElementById('tot_inacts');
    tsElement.innerHTML = profile_data.meta.num_total_inactives;


    // plotHeatMap comes from
    plotHeatMap(profile_data);
}


function addFilter() {

    var statsFilter = document.getElementById("stats-filter");
    var selectedStat = statsFilter.options[statsFilter.selectedIndex].value;

    var statsThreshold = document.getElementById("stats-threshold");
    var selectedThreshold = statsThreshold.options[statsThreshold.selectedIndex].value;


    var appliedFilters = document.getElementById('applied-filters');


    var appliedFilter = document.createElement("li");
    appliedFilter.classList.add("applied-filter");
    appliedFilter.classList.add("list-group-item");

    var newStat = document.createElement("span");
    newStat.classname = "stat";
    newStat.setAttribute("data-value", selectedStat)
    newStatText = document.createTextNode(selectedStat + " @ ");
    newStat.appendChild(newStatText);

    appliedFilter.appendChild(newStat);

    var threshold = document.createElement("span");
    threshold.classname = "thresh";
    threshold.setAttribute("data-value", selectedThreshold);

    threshText = document.createTextNode(selectedThreshold);
    threshold.appendChild(threshText);

    appliedFilter.appendChild(threshold);

    appliedFilters.append(appliedFilter);


}

function deleteProfile() {
    var e = document.getElementById("profile-selection");
    var currentProfile = e.options[e.selectedIndex].value;


    data = {
        profile_name: currentProfile
    }

    postData('/delete_profile', data);

    location.reload();
}

function clearFilters() {

    // removes the applied filters

    var statsFilters = document.getElementById("applied-filters");
    while (statsFilters.firstChild) {
        statsFilters.removeChild(statsFilters.firstChild);
    }


}

function aggFilters() {

    var statsFilters = document.getElementsByClassName("applied-filter");

    filters = [];


    for (var i = 0; i < statsFilters.length; i++) {

        // for each filter the first child node is the stats
        // and the second is the threshold
        // values for both are stored in the "data-value" attribute

        var statVal = statsFilters[i].children[0].getAttribute("data-value");
        var threshVal = statsFilters[i].children[1].getAttribute("data-value");

        var filter = {
            stat : statVal,
            thresh : threshVal
        };

        filters.push(filter);
    }

    return filters;
}




function postData(url, data) {
    // function that uses fetch model to send the current filters to the flask function


    fetch(url, {

            method: 'POST',

            headers: {
                'Content-type': 'application/json'
            },

            body: JSON.stringify(data)
        }
        )
}