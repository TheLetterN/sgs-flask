<!--begin google search-->
  (function() {
    var cx = '006413036390056318082:jiyohl9_9ey';
    var gcse = document.createElement('script');
    gcse.type = 'text/javascript';
    gcse.async = true;
    gcse.src = (document.location.protocol == 'https:' ? 'https:' : 'http:') +
        '//cse.google.com/cse.js?cx=' + cx;
    var s = document.getElementsByTagName('script')[0];
    s.parentNode.insertBefore(gcse, s);
  })();
<!--end google search-->

<!--begin back to top-->
$(document).ready(function() {
  $("#back-top").hide();
  $(function() {
    $(window).scroll(function() {
      3250 < $(this).scrollTop() ? $("#back-top").fadeIn() : $("#back-top").fadeOut();
    });
    $("#back-top a").click(function() {
      $("body,html").animate({scrollTop:0}, 1E3);
      return !1;
    });
  });
});
<!--end back to top-->

<!--begin google analytics-->
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-19076223-1', 'auto');
  ga('send', 'pageview');
<!--end google analytics-->

<!--begin facebook link and share-->
(function(d, s, id) {
var js, fjs = d.getElementsByTagName(s)[0];
  if (d.getElementById(id)) return;
  js = d.createElement(s); js.id = id;
  js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.3";
  fjs.parentNode.insertBefore(js, fjs);
  }(document, 'script', 'facebook-jssdk'));
<!--end facebook link and share-->

function popitup(url) {
	newwindow=window.open(url,'name','height=550,width=400');
	if (window.focus) {newwindow.focus()}
	return false;
}