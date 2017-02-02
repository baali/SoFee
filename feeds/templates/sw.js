{% load static %}
'use strict';
var CACHE = 'sofee_offline';
   
self.addEventListener('install', function(event) {
  console.log('Installed', event);
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll([
        './',
        "{% static "css/ghpages-materialize.css" %}",
        "{% static "js/firebase.js" %}",
        "{% static "js/jquery-2.1.1.min.js" %}",
        "{% static "js/materialize.js" %}",
        "{% static "js/status.js" %}",
        "/index/{{ uuid }}/",
        "/urls/{{ uuid }}/",
      ]);
    })
  );
});


self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request).then(function(response) {
        caches.open(CACHE).then(function(cache) {
          return cache.put(event.request, response);
        });
      });
    })
  );
});


self.addEventListener('activate', function(event) {
  console.log('Activated', event);
  event.waitUntil(self.clients.claim());
});


self.addEventListener('push', function(event) {
  console.log('Push message received', event);
  var options = {
    body: "Body",
  }
  self.registration.showNotification("Title");
});

self.addEventListener('message', function(event) {
  console.log('We got message');
  // Fetch Links for this UUID and cache the result
  if (event.data.action === 'get_links') {
    caches.open(CACHE).then(function (cache) {
      cache.match("/urls/"+event.data.uuid+"/").then(function (response) {
        console.log('Returning from Cache');
        if (response) {
          response.json().then(function(data) {
            console.log('Returning cached response');
            self.clients.matchAll().then(function(clients) {
              clients.forEach(function(client) {
                client.postMessage(data);
              })
            })
            // event.ports[0].postMessage(data);
          }).catch(function(err) {
            console.log('Fetch Error :-S', err);
          });
        }
        else {
          console.log('Fetching new content');
          fetch("/urls/"+event.data.uuid+"/").then(function(response) {
            var cache_response = response.clone();
            caches.open(CACHE).then(function (cache) {
              cache.put("/urls/"+event.data.uuid+"/", cache_response);
            });
            response.json().then(function(data) {
              self.clients.matchAll().then(function(clients) {
                clients.forEach(function(client) {
                  client.postMessage(data);
                })
              })
            }).catch(function(err) {
              console.log('Fetch Error :-S', err);
            });
          });
        }
      });
    });
  }
});
