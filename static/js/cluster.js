function changeClusteringName() {
    selector = $("#profile-selection");
    currentProfile = selector.find(":selected").text().trim();
    clusteringFilename = $("#clustering_filename");
    clusteringFilename.val(currentProfile + "_clustering");

};

function updateMaxNoClusters(maxNumber) {
   $("#n_clusters").attr("max", maxNumber);
};


function refreshProfileClusterPage() {

    // replaces all the profile data on the cluster page

    var currentProfile = $("#profile-selection").find(":selected").text().trim();

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

    updateMaxNoClusters(profile_data.meta.num_aids);
}

function networkGraph (graph) {

    d3.select("#cluster-graph").select("svg").remove();
    var cardBody = d3.select("#cluster-graph-card-body");

    var body = d3.select("#cluster-graph"),
        width = parseInt(cardBody.style("width"))-100,
        height = parseInt(cardBody.style("width"))-100,
        radius = 6;

    // cluster colors
    var fill = d3.scaleOrdinal(d3.schemeCategory20);

    var svg = body.append("svg");

    svg.attr("width", width);
    svg.attr("height", height);

    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(function(d) { return d.id; })
                                     .distance(100)
                                     // .strength(function(d) { return 1-d.weight; })
        )
        .force("charge", d3.forceManyBody())
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
              .attr("r", radius)
              .style("fill", function(d) { return fill(d.class); })
             .style("stroke", "#969696")
             .style("stroke-width", "1px")
              .call(d3.drag()
                  .on("start", dragstarted)
                  .on("drag", dragged)
                  .on("end", dragended)
              );

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
             .attr("cx", function (d) { return d.x = Math.max(radius, Math.min(width - radius, d.x)); })
             .attr("cy",  function(d) { return d.y = Math.max(radius, Math.min(height - radius, d.y)); });

        label
                .attr("x", function(d) { return d.x; })
                .attr("y", function (d) { return d.y; })
                .style("font-size", "20px").style("fill", "rgba(0, 0, 0, 0.4)");
      }


        function dragstarted(d) {
          if (!d3.event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        }

        function dragged(d) {
          d.fx = d3.event.x;
          d.fy = d3.event.y;
        }

        function dragended(d) {
          if (!d3.event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }
}

function updateColors(graph){
    var fill = d3.scaleOrdinal(d3.schemeCategory20);
    nodes = d3.selectAll("circle");

        nodes.data(graph.nodes)
      .enter().append("circle")
              .style("fill", function(d) { return fill(d.class); })
}



function merge(graph, n) {
    // merge clusters at n

    var mergeData = graph.linkage[n];

    var mergeIdxOne = mergeData[0];
    var mergeIdxTwo = mergeData[1];

    if (mergeIdxTwo >= graph.nodes.length) {
        mergeIdxTwo = mergeIdxTwo - graph.nodes.length
    }

    if (mergeIdxOne >= graph.nodes.length) {
        mergeIdxOne = mergeIdxOne - graph.nodes.length
    }

    console.log(mergeIdxTwo, mergeIdxOne)
    nodeOne = graph.nodes[mergeIdxOne];
    nodeTwo = graph.nodes[mergeIdxTwo];

    if (nodeOne.class < nodeTwo.class) {
        for (var i = 0; i < graph.nodes.length; i++) {

            if (graph.nodes[i].class == nodeTwo.class) {
                graph.nodes[i].class = nodeOne.class
            }

        }

    } else {
        for (var i = 0; i < graph.nodes.length; i++) {

            if (graph.nodes[i].class == nodeOne.class) {
                graph.nodes[i].class = nodeTwo.class
            }

        }
    }

}


function plotGraph() {
    currentClustering = $("#cluster-selection").find(":selected").text().trim();


    var queryUrl = $SCRIPT_ROOT + "get_adj_matrix/" + currentClustering;
    var graph = JSON.parse(getResponseFromURL(queryUrl));

    networkGraph(graph);
}