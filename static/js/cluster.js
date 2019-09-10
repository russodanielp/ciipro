function changeClusteringName() {
    selector = $("#profile-selection");
    currentProfile = selector.find(":selected").text().trim();
    clusteringFilename = $("#clustering_filename");
    clusteringFilename.val(currentProfile + "_clustering");

};


function refreshProfileClusterPage() {

    // replaces all the profile data on the optimizer page
    // and also replorts the heatmap

    var currentProfile = $("#profile-selection").find(":selected").text().trim();

    var queryUrl = $SCRIPT_ROOT + "get_bioprofile/" + currentProfile;
    var profile_data = JSON.parse(getResponseFromURL(queryUrl));
    console.log(queryUrl);

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

function networkGraph (graph) {

    d3.select("#cluster-graph").select("svg").remove();
    var cardBody = d3.select("#cluster-graph-card-body");

    var body = d3.select("#cluster-graph"),
        width = parseInt(cardBody.style("width")),
        height = parseInt(cardBody.style("width"));

    console.log(width);

    var svg = body.append("svg");

    svg.attr("width", width);
    svg.attr("height", height);

    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(function(d) { return d.id; }))
        .force("charge", d3.forceManyBody().strength(-400))
        .force("center", d3.forceCenter(width / 2, height / 2));



      var link = svg.append("g")
                    .style("stroke", "#aaa")
                    .selectAll("line")
                    .data(graph.links)
                    .enter().append("line");

      var node = svg.append("g")
                .attr("class", "nodes")
      .selectAll("circle")
                .data(graph.nodes)
      .enter().append("circle")
              .attr("r", 6)
              .call(d3.drag()
                  .on("start", dragstarted)
                  .on("drag", dragged)
                  .on("end", dragended));

      var label = svg.append("g")
          .attr("class", "labels")
          .selectAll("text")
          .data(graph.nodes)
          .enter().append("text")
            .attr("class", "label")
            .text(function(d) { return d.name; });

      simulation
          .nodes(graph.nodes)
          .on("tick", ticked);

      simulation.force("link")
          .links(graph.links);

      function ticked() {
        link
            .attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        node
             .attr("r", 20)
             .style("fill", "rgba(0, 128, 256, 0.5)")
             .style("stroke", "#969696")
             .style("stroke-width", "1px")
             .attr("cx", function (d) { return d.x+6; })
             .attr("cy", function(d) { return d.y-6; });

        label
                .attr("x", function(d) { return d.x; })
                .attr("y", function (d) { return d.y; })
                .style("font-size", "20px").style("fill", "rgba(0, 0, 0, 0.4)");
      }


    function dragstarted(d) {
      if (!d3.event.active) simulation.alphaTarget(0.3).restart()
      simulation.fix(d);
    }

    function dragged(d) {
      simulation.fix(d, d3.event.x, d3.event.y);
    }

    function dragended(d) {
      if (!d3.event.active) simulation.alphaTarget(0);
      simulation.unfix(d);
    }
}

function plotGraph() {
    currentClustering = $("#cluster-selection").find(":selected").text().trim();
    console.log(currentClustering)


    var queryUrl = $SCRIPT_ROOT + "get_adj_matrix/" + currentClustering;
    var graph = JSON.parse(getResponseFromURL(queryUrl));

    networkGraph(graph);
}