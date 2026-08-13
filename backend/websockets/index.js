/*
concepts in websockets
1.client
2.server
3.request
4.response
5.connection
6.message
7.events
8.close
*/



const http = require("http")
const wsServer = require("websocket").server
let connection = null

const httpServer = http.createServer((req, res) => {
    console.log("we have received the reqest")
})

const ws = new wsServer({
    "httpServer": httpServer
})

ws.on("request", req=>{
    connection = req.accept(null, req.origin)
    global.connection = connection // debug-only: lets the debug console reach it
    console.log("opened!!!")
    connection.on("close", ()=>console.log("closeddd!!"))
    connection.on("message", message => console.log(`received message: ${message.utf8Data}`))

    sendevery5seconds()
})

httpServer.listen(8000, () => console.log("my server is listening on port 8000"))


function sendevery5seconds(){

    connection.send(`Message ${Math.random()}`);

    setTimeout(sendevery5seconds, 5000);


}