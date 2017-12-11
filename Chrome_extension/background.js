console.log('Extension background restarted...');
queue = []
id = Math.floor((Math.random()*10000000000)).toString();
recording = true

chrome.webRequest.onCompleted.addListener(function(req){
    if (recording){
        queue.push(encodeURIComponent(req.url))
        if (queue.length > 170){
            updateStorage()
            queue = []
        }
    	console.log("Image arrived");
    }
},{	urls: [ "<all_urls>" ], types: ["image"]})



function updateStorage() {
    // chrome.storage.local.get('urls', function(data) {
    // 	data.urls = [].concat(data.urls || [], queue);
    //     queue = [];
    //     chrome.storage.local.set(data);
    // });
    $.ajax({
      type: "POST",
      url: "http://10.230.12.17:8000/urls",
      crossDomain:true, 
      dataType: "json",
      data: {"queue": queue, "id": id}
     }).done(function ( data ) {
          alert("ajax callback response:"+JSON.stringify(data));
       })
}

// Message
chrome.extension.onMessage.addListener(function(request, sender, sendResponse) {
    console.log('message')
    switch(request.type) {
        case "record":
            recording = !recording;
            console.log('record:', recording)
            break;
        case "visual":
            chrome.tabs.create({ url: 'http://10.230.12.17:8000/stats?id='+id });
            break;
        case "send":
            console.log(queue);
            updateStorage();
            break;
        case "empty":
            chrome.storage.local.clear(function(){
                console.log("cleared");
            })
            queue = []
            break;
    }
    return true;
});

