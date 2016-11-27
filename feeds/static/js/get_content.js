var readability = require("readability/index");
var jsdom = require("jsdom");
var url = require("url");

var Readability = readability.Readability;
var JSDOMParser = readability.JSDOMParser;
var uri_to_fetch = process.argv[2]

var uri = url.parse(uri_to_fetch);
jsdom.env({
  url: uri_to_fetch,
  scripts: [],
  done: function (err, window) {
    var article = new Readability(uri, window.document).parse();
    console.log(JSON.stringify(article));
  }
});
