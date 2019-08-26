function plotBar(actives, inactives) {
    // bar plot that shows the active:inactive ratio
    // of a dataset

    var margin = {top: 20, right: 20, bottom: 30, left: 40};
    var w = 300 - margin.left - margin.right;
    var h = 300 - margin.top - margin.bottom;


    var svg = d3.select("#dataset-bar").attr("height", 300)
                .attr("width", 600);

    svg.selectAll('g').remove();

    var chart = svg.append('g').attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var yScale = d3.scaleLinear().domain([0, Math.max(actives, inactives)+10]).range([h, 0]);
    var xScale = d3.scaleBand().domain(['Actives', 'Inactives']).range([10, w]);

    var yAxis = chart.append("g")
                    .call(d3.axisLeft(yScale));
    var xAxis = chart.append("g")
                    .call(d3.axisTop(xScale));


    chart.selectAll("act")
      .data([actives])
      .enter().append("rect")
      .attr("width", xScale.bandwidth())
      .attr("height", function (d) {
          return h-yScale(d);
      })
      .attr("x", xScale('Actives'))
      .attr("y", function (d) {
          return yScale(d);
      })
      .style("fill", "red")
      .style("stroke", "black")
      .style("fill-opacity", 0.4).style("stroke-width", 3);


    chart.selectAll("inact")
      .data([inactives])
      .enter().append("rect")
      .attr("width", xScale.bandwidth())
      .attr("height", function (d) {
          return h-yScale(d);
      })
      .attr("x", xScale('Inactives'))
      .attr("y", function (d) {
          return yScale(d)
      })
      .style("fill", "green")
      .style("stroke", "black")
      .style("fill-opacity", 0.4).style("stroke-width", 3);
}

function updateBar() {
    var e = document.getElementById("dataset-selection");
    var currentProfile = e.options[e.selectedIndex].value;

    var queryUrl = $SCRIPT_ROOT + "get_dataset_overview/" + currentProfile;
    var dataset_data = JSON.parse(getResponseFromURL(queryUrl));

    plotBar(dataset_data.actives, dataset_data.inactives);

}