function loop_delay(uuid) {
  setTimeout(get_status, 2000, uuid)
}

function get_status(uuid) {
  if (uuid === undefined) {
    return
  }
  console.log(uuid);
  var return_status = '';
  $.get("/get_status/", {"uuid":uuid})
    .done( function(data) {
      if (data.task_status === 'PENDING') {
        $("div.link").text("");
        $("span.stats").html("<p>Waiting for task to start...<br /></p>");
        console.log(data);
        get_status(uuid);
      }
      else if (data.task_status === 'PROGRESS') {
        $("div.link").text("");
        $("span.stats").html("Finished " + data.count + "/" + data.total_count +" friends.");
        $("span.list").html(data.info);
        get_status(uuid);
      }
      else if (data.task_status === 'SUCCESS') {
        $("div.link").text("");
        $("span.stats").html("<p>Done processing your OPML file, We have DMed you details or you can Download the file from <a href=\""+data.info+"\">here</a>.<br/></p>");
      }
    })
    .fail(function() {
      $("span.stats").html("<p>Sorry for the trouble, We were not able to process your request, please contact baali@muse-amuse.in for clarifications.<br/></p>");
      console.log( "Task failed" );
    });
}

