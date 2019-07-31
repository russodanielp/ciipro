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

function addFilter() {

    var statsFilter = document.getElementById("stats-filter");
    var selectedStat = statsFilter.options[statsFilter.selectedIndex].value;

    var statsThreshold = document.getElementById("stats-threshold");
    var selectedThreshold = statsThreshold.options[statsThreshold.selectedIndex].value;

    console.log(selectedStat, selectedThreshold);
    var appliedFilters = document.getElementById('applied-filters');
    console.log(appliedFilters);

    var appliedFilter = document.createElement("div");
    appliedFilter.classname = 'applied-filter';

    var newStat = document.createElement("div");
    newStat.classname = "stat";
    newStat.setAttribute("data-value", selectedStat)
    newStatText = document.createTextNode(selectedStat + " @");
    newStat.appendChild(newStatText);

    appliedFilter.appendChild(newStat);

    var threshold = document.createElement("div");
    threshold.classname = "thresh";
    threshold.setAttribute("data-value", selectedThreshold);

    threshText = document.createTextNode(selectedThreshold);
    threshold.appendChild(threshText);

    appliedFilter.appendChild(threshold);

    appliedFilters.append(appliedFilter);







}