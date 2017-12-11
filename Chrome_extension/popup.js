console.log("heeeey")
document.addEventListener('DOMContentLoaded', function () {
	console.log("loaded")
    document.getElementById("record").onclick = function() {
    	var elem = document.getElementById("record");
        console.log(elem, elem.innerText)
        if (elem.innerText == "Start recording") elem.innerText = "Stop recording";
        else elem.innerText= "Start recording";
        chrome.extension.sendMessage({
            type: "record"
        });
    }
    document.getElementById("send").onclick = function() {
        console.log("message")
        chrome.extension.sendMessage({
            type: "send"
        });
    }
    document.getElementById("visual").onclick = function() {
        console.log("message")
        chrome.extension.sendMessage({
            type: "visual"
        });
    }
    document.getElementById("empty").onclick = function() {
        console.log("message")
        chrome.extension.sendMessage({
            type: "empty"
        });
    }
})