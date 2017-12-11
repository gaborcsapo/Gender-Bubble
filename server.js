var express = require('express');
var path =  require('path');
var bp = require('body-parser');
var fs = require('fs');
var http = require('http');
var request = require('request');
var url = require("url");
var app = express();
var port = 8000;
var count = 0;
process.umask(0)

app.use(express.static(path.join(__dirname, 'public')));

app.use(bp.urlencoded({
  extended: true,
  limit: '50mb'
}));
app.use(bp.json());

var server = app.listen(port, '0.0.0.0', function(){
  console.log('server started on port'+port);
});

var onResponse = function(res, resolve, reject, req){
    var imagedata = ''
    
    res.on('error', function(msg){
        resolve('response error: ', msg)
    })
    
    res.setEncoding('binary')
    res.on('data', function(chunk){
        imagedata += chunk
    })   
    
    res.on('end', function(){ 
        if (imagedata.length >= 1000){
            filename = './img/'+req.body.id+"/raw/"+options.host+ '-' + count.toString()+'.jpg'
            arriving.push(options.host+ '-' + count.toString()+'.jpg')
            fs.writeFile(filename, imagedata, 'binary', function(err){
                if (err) throw err
                console.log('Saved: img/'+req.body.id+"/raw/"+count.toString()+'.jpg | ', options.host)
                count++
            })
        } else {
            console.log('Too small (', imagedata.length, '): ', options.host, options.path)
        }
        resolve('done');
    }) 
}

var new_request = function(req, i){
    return new Promise((resolve, reject) => {
        options = {host: url.parse(decodeURIComponent(req.body.queue[i])).hostname, 
                   port: 80, 
                   path: url.parse(decodeURIComponent(req.body.queue[i])).pathname}
        request = http.get(options, res => onResponse(res, resolve, reject, req))
        request.on('error', function(msg){
            resolve('HTTP error:', msg)
        });
        setTimeout(function() {
            resolve('HTTP request discarded after ' + 3000 + ' ms');
        }, 3000);
    })
}

app.post("/urls", function(req, res, err){
    if (! req.body.queue)
        return 0
    if (!fs.existsSync('./img/'+req.body.id)){
        console.log("ceating dir")
        fs.mkdirSync('./img/'+req.body.id, 0777);
        fs.mkdirSync('./img/'+req.body.id+'/raw/', 0777);
        fs.mkdirSync('./img/'+req.body.id+'/processed/', 0777);
    }
    arriving = []
    promises = []
    for (var i = 0; i < req.body.queue.length; i++){
        promises.push(new_request(req, i))
    }
    Promise.all(promises).then(function() {
        console.log('Preprocessing...')
        var spawn = require('child_process').spawnSync,
            py = spawn('/home/gc1569/anaconda3/bin/python3',['preproc.py',req.body.id],{'input':JSON.stringify(arriving)});
        console.log('output: ', py.stdout.toString('utf8')) 
        console.log('stderr: ', py.stderr.toString('utf8')) 
        console.log('Done preprocessing') 
    })
})

app.get('/stats', function (req, res) {
    res.sendfile('./public/index.html')   
})

app.get('/sum/:user', function (req, res) {

    res.sendfile('./public/img/'+username+'-sum.json')
})