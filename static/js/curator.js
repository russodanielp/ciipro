function addCurationStep() {

    var curationSteps = document.getElementById("curation-steps");
    var selectedStep = curationSteps.options[curationSteps.selectedIndex].value;

    var appliedSteps = document.getElementById('applied-steps');


    var appliedStep = document.createElement("li");
    appliedStep.classList.add("applied-steps");
    appliedStep.classList.add("list-group-item");

    var newStep = document.createElement("span");
    newStep.classname = "curationstep";
    newStep.setAttribute("data-value", selectedStep)
    newStepText = document.createTextNode(selectedStep);
    newStep.appendChild(newStepText);

    appliedStep.appendChild(newStep);

    appliedSteps.append(appliedStep);


}

function clearSteps() {

    // removes the curation steps

    var curationSteps = document.getElementById("applied-steps");
    while (curationSteps.firstChild) {
        curationSteps.removeChild(curationSteps.firstChild);
    }


}

function aggSteps() {

    var curationSteps = document.getElementsByClassName("applied-steps");

    steps = [];


    for (var i = 0; i < curationSteps.length; i++) {

        // for each filter the first child node is the stats
        // and the second is the threshold
        // values for both are stored in the "data-value" attribute

        var stepVal = curationSteps[i].children[0].getAttribute("data-value");


        var step = {
            step : stepVal,

        };

        steps.push(step);
    }

    return steps;
}

function populateTable(tableID, tableJSON){

    var tableData = tableJSON.tableData;
    var tableHeader = tableJSON.tableHeader;

    var columns = [];

    for (var i = 0; i < tableHeader.length; i++) {
        columns.push({title: tableHeader[i]})
    }

    if (! $.fn.DataTable.isDataTable(tableID)) {
        $(tableID).DataTable({
            data: tableData,
            columns: columns
            // deferLoading: tableData.length,
        });
    } else {
    //   $(tableID).DataTable().clear().draw();
    //
    //
    //   $(tableID).DataTable().rows.add(tableData).draw( false ); // Add new data
      // $('#yourtable').DataTable().columns.adjust().draw(); // Redraw the DataTable
        console.log('true')
        $(tableID).DataTable().clear().destroy();
        $(tableID).empty();
        $(tableID).DataTable({
            data: tableData,
            columns: columns
            // deferLoading: tableData.length,
        });
    }
}

function getTableData(tableID) {
    // get the curation data from the
    var table = $(tableID).DataTable();

    var tableData = table.rows().data();

    var tableHeader = table.columns().header().toArray().map(x => x.innerText);

    return {
        tableHeader: tableHeader,
        tableData: tableData
    }
}