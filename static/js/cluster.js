function refreshProfileClusterPage() {

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



}