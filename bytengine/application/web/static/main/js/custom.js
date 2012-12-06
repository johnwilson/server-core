

// when the DOM is ready..
$(document).ready(function() {
	
	//DEMENTION CLOSE BUTTON
	$(".removable").each(function(){
		$(this).prepend("<a href='#' class='demention-close-icon'>&#215</a>");
	});	
		
	//close button function
	$('.removable .demention-close-icon').click(function() {	
		var theBox = $(this).parent();

		theBox.fadeOut(function() {			
			if(theBox.hasClass('element')){
				$(this).remove();
			}else{
				$(this).hide();
			}		
		});
		
		return false;
	});
    
    //slide out tab
        $('.slide-out-div').tabSlideOut({
            tabHandle: '.handle',                              //class of the element that will be your tab
            pathToTabImage: 'img/switch1.png',          //path to the image for the tab (optionaly can be set using css)
            imageHeight: '100px',                               //height of tab image
            imageWidth: '50px',                               //width of tab image    
           tabLocation: 'left',                               //side of screen where tab lives, top, right, bottom, or left
            speed: 300,                                        //speed of animation
            action: 'click',                                   //options: 'click' or 'hover', action to trigger animation
            topPos: '180px',                                   //80px(original) position from the top
            fixedPosition: true                               //options: true makes it stick(fixed position) on scroll
        });
        
    
    // make code pretty
    window.prettyPrint && prettyPrint();

	
}); //END -- JQUERY document.ready