const http = new XMLHttpRequest();
const dbBaseUrl = "http://127.0.0.1:5000/get_database_overview/";
const statsBaseUrl = "http://127.0.0.1:5000/get_ff_stats/";
console.log(dbBaseUrl)
function getResponseFromURL(queryUrl) {
  http.open('GET', queryUrl, false);
  http.send(null);
  if (http.status === 200) {
    return http.responseText;
  } else {
    return null;
  }
}