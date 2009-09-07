jq(document).ready(function() {
 // hides the slickbox as soon as the DOM is ready (a little sooner that page load)
  jq('.explain-info').hide();
  jq('#explain-showmore').click(function() {
    jq('#explain-' + jq(this).attr("explain")).slideToggle(400);
    return false;
  });
});