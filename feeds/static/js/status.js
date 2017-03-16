var link_details = {}
var next_page = '';

// Based on SO Conversation http://stackoverflow.com/questions/10072216/jquery-infinite-scroll-with-div-not-scrollbar-of-body
// scrollFire option to update the last li element didn't work for dynamic elements
// var options = [{selector: '.collection-item.last-li', offset: 50, callback: function(el) {
//   update_feed(next_page);
// }},]
// Materialize.scrollFire(options);

$(window).scroll(function() {
  if($(window).scrollTop() + $(window).height() == $(document).height()) {
    update_feed(next_page);
  }
});
 
const messaging = firebase.messaging();
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
        $('#cleaned_text').modal('open');
        $('#cleaned_text').scrollTop(0);
       }
    }
  });
  messaging.requestPermission()
    .then(function() {
      console.log('Notification permission granted.');
    })
    .catch(function(err) {
      console.log('Unable to get permission to notify.', err);
    });
  messaging.getToken()
    .then(function(currentToken) {
      if (currentToken && uuid !== undefined) {
        console.log(currentToken);
        fetch("/push_token/", {
          headers: {
            'Content-Type': 'application/json'
          },
          method: "POST",
          body: JSON.stringify({uuid: uuid,
                                token: currentToken}),
        }).then(function(response) {
          console.log(response.json());
        });
        // Communicate it to server.
      } else {
        console.log('No Instance ID token available. Request permission to generate one.');
      }
    }).catch(function(err) {
      console.log('An error occurred while retrieving token. ', err);
    });
})

function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

function get_task_status(uuid, task_id) {
  $.get("/get_task_status/", {'task_id':task_id})
    .done( function(data) {
      if (data['task_status'] === 'PROGRESS' || data['task_status'] === 'RECEIVED' || data['task_status'] === 'PENDING') {
        Materialize.toast(data['info'], 1000);
        Materialize.toast('Processed '+data['count']+' out of '+data['total_count']+' Accounts you follow.', 1000);
        // http://stackoverflow.com/a/951057
        sleep(5000).then(() => {
          get_task_status(uuid, task_id);
        });
      } else if (data['task_status'] === 'SUCCESS') {
        Materialize.toast(data['info'], 1000);
      } else {
        $("#tweets").html("<p>Sorry there was issue while processing your Twitter account. Please contact baali[at]muse-amuse.in for clarifications.<br/></p>");
      }      
    });
}

function update_feed(url) {
  if (url === null) {
    return
  }
  console.log('Updating feed...');
  fetch(next_page).then(function(response) {
    response.json().then(function(data) {
      next_page = data.next;
      data.results.forEach(function(obj, index, array) {
        var shared_from = "";
        if (obj.shared_from !== undefined) {
          var quoted_text = '';
          quoted_text = obj.quoted_text;
          if ('title' in obj.url_json && obj.url_json.title.length > 0) {
            quoted_text += '<br/><strong>Title</strong>: '+obj.url_json.title;
          }
          $.each(obj.shared_from, function(index_names, name) {
            if ('profile_image_url' in name.account_json) {
              shared_from =
                $('<div class="chip">').append(
                  $('<a>').attr('href', name.account_json.url).append(
                    $('<img class="circle responsive-img">').attr('src', name.account_json.profile_image_url)).attr(
                      'target', '_blank').append(name.account_json.screen_name));
            }
            else {
              shared_from += name.screen_name+' ';
            }
          });
          link_details[obj.uuid] = obj.cleaned_text;
          $('#tweets').append(
            $('<li class="collection-item">').append(
              $('<div>').append(shared_from).append(
                $('<span>').append(quoted_text+' ').append(
                  $('<a>').attr('href', obj.url).attr(
                    'target', '_blank').append(
                      $('<i class="tiny material-icons">').text('send'))))).attr(
                        'li-uuid', obj.uuid));
        }
        else {
          if ('profile_image_url' in obj.tweet_from.account_json) {
            shared_from =
              $('<div class="chip">').append(
                $('<a>').attr('href', obj.tweet_from.account_json.url).append(
                  $('<img class="circle responsive-img">').attr('src', obj.tweet_from.account_json.profile_image_url)).attr(
                    'target', '_blank').append(obj.tweet_from.account_json.screen_name));
          }
          else {
            shared_from += obj.tweet_from.screen_name+' ';
          }
          $('#tweets').append(
            $('<li class="collection-item">').append(
              $('<div>').append(shared_from).append(
                $('<span>').text(obj.status_text)
              )
            )
          );
        }
      });
    });
  });
}

function get_status(uuid) {
  if (uuid === undefined) {
    return
  }
  $('.button-collapse').sideNav('hide');
  var return_status = '';
  // var next_page = '';
  // $.get("/status/"+uuid+"/")
  //   .done( function(data) {
  fetch("/status/"+uuid+"/").then(function(response) {
    response.json().then(function(data) {
      next_page = data.next;
      $('#tweets').empty();
      data.results.forEach(function(obj, index, array) {
        if ('profile_image_url' in obj.tweet_from.account_json) {
          shared_from =
            $('<div class="chip">').append(
              $('<a>').attr('href', obj.tweet_from.account_json.url).append(
                $('<img class="circle responsive-img">').attr('src', obj.tweet_from.account_json.profile_image_url)).attr(
                  'target', '_blank').append(obj.tweet_from.account_json.screen_name));
        }
        else {
          shared_from += obj.tweet_from.screen_name+' ';
        }
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<div>').append(shared_from).append(
              $('<span>').text(obj.status_text)
            )
          )
        );
      });
    });
  });
}

function get_links(uuid) {
  if (uuid === undefined) {
    return
  }
  $('.button-collapse').sideNav('hide');
  $('#tweets').empty();
  if (navigator.serviceWorker.controller) {
    navigator.serviceWorker.onmessage = function(event) {
      console.log('Service worker returned a message!');
      link_details = {};
      next_page = event.data.next;
      $.each(event.data.results, function(index, obj) {
        var shared_from = "";
        $.each(obj.shared_from, function(index_names, name) {
          if ('profile_image_url' in name.account_json) {
            shared_from =
              $('<div class="chip">').append(
                $('<a>').attr('href', name.account_json.url).append(
                  $('<img class="circle responsive-img">').attr('src', name.account_json.profile_image_url)).attr(
                    'target', '_blank').append(name.account_json.screen_name));
          }
          else {
            shared_from += name.screen_name+' ';
          }
        });
        link_details[obj.uuid] = obj.cleaned_text;
        var quoted_text = '';
        quoted_text = obj.quoted_text;
        if ('title' in obj.url_json && obj.url_json.title.length > 0) {
          quoted_text += '<br/><strong>Title</strong>: '+obj.url_json.title;
        }
        $('#tweets').append(
          $('<li class="collection-item">').append(
            $('<div>').append(shared_from).append(
              $('<span>').append(quoted_text+' ').append(
                $('<a>').attr('href', obj.url).attr(
                  'target', '_blank').append(
                    // setting text to obj.url makes it dynamic
                    // length and css tries to accommodate text by
                    // resizing collection div which makes element
                    // to go beyond screen width.
                    $('<i class="tiny material-icons">').text('send'))))).attr(
                      'li-uuid', obj.uuid));
      });
    }
    // Create a Message Channel
    var msg_chan = new MessageChannel();
    navigator.serviceWorker.controller.postMessage({'uuid': uuid,
                                                    'action': 'get_links'});
  }
  else {
    console.log('Making our own JS Request!');
    $.get("/urls/"+uuid+"/")
      .done( function(data) {
        next_page = data.next;
        link_details = {};
        $.each(data.results, function(index, obj) {
          var shared_from = "";
          $.each(obj.shared_from, function(index_names, name) {
            if ('profile_image_url' in name.account_json) {
              shared_from =
                $('<div class="chip">').append(
                  $('<a>').attr('href', name.account_json.url).append(
                    $('<img class="circle responsive-img">').attr('src', name.account_json.profile_image_url)).attr(
                      'target', '_blank').append(name.account_json.screen_name));
            }
            else {
              shared_from += name.screen_name+' ';
            }
          });
          link_details[obj.uuid] = obj.cleaned_text;
          var quoted_text = '';
          quoted_text = obj.quoted_text;
          if ('title' in obj.url_json && obj.url_json.title.length > 0) {
            quoted_text += '<br/><strong>Title</strong>: '+obj.url_json.title;
          }
          $('#tweets').append(
            $('<li class="collection-item">').append(
              $('<div>').append(shared_from).append(
                $('<span>').append(quoted_text+' ').append(
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
}
