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