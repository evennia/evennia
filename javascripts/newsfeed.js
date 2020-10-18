// Get data from github

function httpGetAsync(theUrl, callback)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() { 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback(xmlHttp.responseText);
    }
    xmlHttp.open("GET", theUrl, true); // true for asynchronous 
    xmlHttp.send(null);
}

function on_github_response(response) {
  console.log("read latest events from github!");
  var eventList = JSON.parse(response);

  // console.log(eventList);

  // Which events to exclude
  var excludes = ["WatchEvent", "GollumEvent", "IssueCommentEvent",
                  "ForkEvent", "PullRequestReviewCommentEvent"];

  // loop over events, filtering out excluded ones
  const resultList = eventList 
    .filter(item => !(excludes.includes(item.type)))
    .map(envt => {
      var output = "";
      if (envt.type === "IssueCommentEvent") {
          output = (
            " <a href=\"" + envt.payload.comment.html_url + "\">" 
            + envt.actor.display_login + " commented on issue #"
            + envt.payload.issue.number + "</a>"
          );
      } else if(envt.type === "IssuesEvent") {
          output = (
            "<a href=\"" + envt.payload.issue.html_url + "\">" 
            + "Issue " 
            + envt.payload.action + ": "
            + envt.payload.issue.title.slice(0, 20) + ".." + "</a>"
          );
      } else if(envt.type == "PushEvent") {
          output = (
            "<a href=\"" + "https://github.com/evennia/evennia/commit/" + envt.payload.commits[0].sha + "\">"
            + "Commit by " + envt.payload.commits[0].author.name + ": " 
            + envt.payload.commits[0].message.slice(0, 20) + ".." + "</a>"
          );
      } else if(envt.type == "PullRequestEvent") {
          output = (
            "<a href=\"" + "https://github.com/evennia/evennia/pull/" + envt.payload.number + "\">"
            + "PR #" + envt.payload.number + " " + envt.payload.action
            + " by " + envt.actor.display_login
            + "</a>"
          )  
      }
      return "<li class=\"news-event\">" + output + "</li>";
  });

  var strList = "";
  if (resultList.length) {
    strList = "<ul>" + resultList.slice(0,5).join('') + "</ul>";
  }
      
  // Add news to div
  var newsDiv = document.getElementById("latest-events");
  newsDiv.innerHTML = "";  // clear the Fetching feed message
  newsDiv.insertAdjacentHTML('afterend', strList);
}

// Get public events
function fetchGithubData() {
  httpGetAsync("https://api.github.com/orgs/evennia/events?per_page=40", on_github_response);
};
