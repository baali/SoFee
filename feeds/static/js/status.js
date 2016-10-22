$( document ).ready(function(){
  $(".button-collapse").sideNav();  
  $( "#tweets" ).on( "mouseenter", "li.collection-item", function(e) {
    console.log(this);
  });
})

function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

function get_task_status(uuid, task_id) {
  $.get("/get_task_status/", {'task_id':task_id})
    .done( function(data) {
      if (data['task_status'] === 'PROGRESS') {
        Materialize.toast(data['info'], 1000);
        Materialize.toast('Processed '+data['count']+' out of '+data['total_count']+' Accounts you follow.', 1000);
        // http://stackoverflow.com/a/951057
        sleep(5000).then(() => {
          get_task_status(uuid, task_id);
        });
      } else if (data['task_status'] === 'SUCCESS') {
        Materialize.toast(data['info'], 1000);
      } else {
        $("#tweets").html("<p>Sorry there was issue while processing your Twitter account. Please contact baali@muse-amuse.in for clarifications.<br/></p>");
      }      
    });
}


function update_feed(url) {
  if (url === null) {
    return
  }
  console.log('Updating feed...');
  $.get(url)
    .done( function(data) {
      $('#tweets').empty();
      next_page = data['next'];
      $.each(data['results'], function(index, obj) {
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<span>').text(obj.tweet_from['screen_name']+' : '+obj.status_text)
          ).attr("li-uuid", obj.uuid)
        );
      });
      var last_li = $('li').last();
      last_li.attr('id', 'last_li');
      var options = [
        {selector: '#last_li', offset: 190, callback: function(el) {
          // Materialize.toast("This is our ScrollFire Demo!", 1500 );
          update_feed(next_page);
        } },
      ]
      Materialize.scrollFire(options);
    })
}

function get_status(uuid) {
  if (uuid === undefined) {
    return
  }
  var return_status = '';
  var next_page = '';
  $.get("/status/"+uuid+"/")
    .done( function(data) {
      $('#tweets').empty();
      next_page = data['next'];
      $.each(data['results'], function(index, obj) {
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<span>').text(obj.tweet_from['screen_name']+' : '+obj.status_text)
          ).attr("li-uuid", obj.uuid));
      });
      var last_li = $('li').last();
      last_li.attr('id', 'last_li');
      var options = [
        {selector: '#last_li', offset: 190, callback: function(el) {
          // Materialize.toast("This is our ScrollFire Demo!", 1500 );
          update_feed(next_page);
        } },
      ]
      Materialize.scrollFire(options);
    })
    .fail(function() {
      $("#tweets").html("<p>Sorry we don't have records for this Twitter account. Please contact baali@muse-amuse.in for clarifications.<br/></p>");
    });
}

function get_links(uuid) {
  if (uuid === undefined) {
    return
  }
  $.get("/links/"+uuid+"/")
    .done( function(data) {
      $('#tweets').empty();
      $.each(data, function(index, obj) {
        var shared_from=""
        $.each(obj.shared_from, function(index_names, name) {
          shared_from += name.screen_name+' ';
        });
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<span>').text(shared_from+': '+obj.quoted_text+' ').append(
              $('<a>').attr('href', obj.url).attr('target', '_blank').append(
                $('<span>').text(obj.url)
              ))));
      });
    })
    .fail(function() {
      $("#tweets").html("<p>Sorry we don't have records for this Twitter account. Please contact baali@muse-amuse.in for clarifications.<br/></p>");
    });
}
