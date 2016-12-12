var link_details = {}
$( document ).ready(function(){
  $(".button-collapse").sideNav();
  $('.modal').modal();
  $( "#tweets" ).on( "click", "li.collection-item", function(e) {
    $('#cleaned_text .modal-content').empty();
    if ($(this).attr('li-uuid') !== undefined) {
      console.log($(this).attr('li-uuid'));
      var content = link_details[$(this).attr('li-uuid')];
      if (content.trim() !== "") {
        $('#cleaned_text .modal-content').html(content);
        $('#cleaned_text').scrollTop(0);
        $('#cleaned_text').modal('open');
       }
    }
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
          )
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
          ));
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
      link_details = {};
      $.each(data, function(index, obj) {
        var shared_from=""
        $.each(obj.shared_from, function(index_names, name) {
          shared_from += name.screen_name+' ';
        });
        link_details[obj.uuid] = obj.cleaned_text;
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<div>').append(
              $('<span>').text(shared_from+': '+obj.quoted_text+' ').append(
                $('<a>').attr('href', obj.url).attr(
                  'target', '_blank').append(
                    // setting text to obj.url makes it dynamic
                    // length and css tries to accommodate text by
                    // resizing collection div which makes element
                    // to go beyond screen width.
                    $('<i class="tiny material-icons">').text('send'))))).attr(
                      'li-uuid', obj.uuid));
      });
    })
    .fail(function() {
      $("#tweets").html("<p>Sorry we don't have records for this Twitter account. Please contact baali@muse-amuse.in for clarifications.<br/></p>");
    });
}
