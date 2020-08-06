// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt
function wheel(event) {
    let width = parseInt(document.getElementById("root").style.width.slice(0, -2));
    let pageX = event.pageX;
    let clientX = event.clientX;
    if (event.deltaY > 0 && width > 100) {
        // Zoom out
        document.getElementById("root").style.width = (width / 2).toString() + "vw";
        window.scrollTo(pageX/2 - clientX, 0);
    } else if (event.deltaY < 0) {
        // Zoom in
        document.getElementById("root").style.width = (width * 2).toString() + "vw";
        window.scrollTo(2*pageX - clientX, 0);
    }
}

document.onwheel = wheel;