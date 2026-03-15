var ws = Process.findModuleByName('websockets.dll');
var lws_write_addr = ws.findExportByName('lws_write');
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');

var lws_write_func = new NativeFunction(lws_write_addr, 'int', ['pointer', 'pointer', 'int', 'int']);

var currentWsi = null;
var writeCount = 0;
var lastMsgId = 0;
var sessionReady = false;
var connectDone = false;
var postConnectReqs = 0;

function encodeMsgId(id) {
    var bytes = [];
    var tmp = id;
    while (tmp >= 128) {
        bytes.push((tmp & 0x7F) | 0x80);
        tmp = tmp >>> 7;
    }
    bytes.push(tmp & 0x7F);
    return bytes;
}

function decodeMsgId(arr, startPos) {
    var id = 0;
    var shift = 0;
    var pos = startPos;
    while (pos < arr.length) {
        var b = arr[pos];
        id |= (b & 0x7F) << shift;
        pos++;
        if ((b & 0x80) === 0) break;
        shift += 7;
    }
    return {id: id, nextPos: pos};
}

Interceptor.attach(lws_write_addr, {
    onEnter: function(args) {
        var wsi = args[0];
        var buf = args[1];
        var len = args[2].toInt32();
        var wp = args[3].toInt32();
        writeCount++;
        currentWsi = wsi;

        if (len > 0 && len < 100000) {
            try {
                var raw = buf.readByteArray(len);
                var arr = new Uint8Array(raw);

                if (arr.length >= 1) {
                    var pkgType = arr[0];

                    if (pkgType === 4 && arr.length >= 5) {
                        var msgFlag = arr[4];
                        var msgType = (msgFlag >> 1) & 0x07;

                        if (msgType === 0) {
                            var decoded = decodeMsgId(arr, 5);
                            var msgId = decoded.id;
                            var pos = decoded.nextPos;
                            lastMsgId = msgId;

                            if (pos < arr.length) {
                                var routeLen = arr[pos]; pos++;
                                if (pos + routeLen <= arr.length) {
                                    var route = '';
                                    for (var i = 0; i < routeLen; i++) route += String.fromCharCode(arr[pos+i]);
                                    var bStart = pos + routeLen;
                                    var bLen = arr.length - bStart;
                                    var bodyStr = '';
                                    for (var i = bStart; i < Math.min(arr.length, bStart+100); i++) {
                                        var c = arr[i];
                                        bodyStr += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
                                    }
                                    send({t:'REQ', id:msgId, r:route, bl:bLen, bs:bodyStr});

                                    if (route === 'connector.entryHandler.connect') {
                                        connectDone = true;
                                        postConnectReqs = 0;
                                    } else if (connectDone) {
                                        postConnectReqs++;
                                    }
                                }
                            }
                        }
                    } else if (pkgType === 1) {
                        sessionReady = false;
                        connectDone = false;
                        postConnectReqs = 0;
                        send({t:'HS'});
                    } else if (pkgType === 2) {
                        sessionReady = true;
                        send({t:'ACK'});
                    } else if (pkgType === 3) {
                        sessionReady = true;
                    }
                }

                if (wp === 4) {
                    send({t:'CLOSE'});
                }
            } catch(e) {}
        }
    }
});

Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(ret) {
        var n = ret.toInt32();
        if (n <= 6) return;
        try {
            var raw = this.buf.readByteArray(n);
            if (!raw) return;
            var arr = new Uint8Array(raw);
            if (arr[0] !== 0x82 && arr[0] !== 0x81) return;

            var pl = arr[1] & 0x7F;
            var hl = 2;
            if (pl === 126) { pl = (arr[2]<<8)|arr[3]; hl = 4; }
            else if (pl === 127) { hl = 10; }
            if (hl + pl > arr.length) return;
            var payload = arr.slice(hl, hl+pl);
            if (payload.length < 1) return;

            var pkgType = payload[0];
            if (pkgType === 4 && payload.length >= 5) {
                var msgBody = payload.slice(4);
                send({t:'SRV', len:msgBody.length}, new Uint8Array(msgBody).buffer);
            } else if (pkgType === 5) {
                send({t:'KICK'});
            }
        } catch(e) {}
    }
});

rpc.exports = {
    status: function() {
        return {
            rid: lastMsgId,
            wsi: currentWsi !== null,
            wc: writeCount,
            ready: sessionReady,
            conn: connectDone,
            pcr: postConnectReqs
        };
    },
    inject: function(route, bodyJsonStr, msgId) {
        if (!currentWsi) return 'NO_WSI';
        if (!sessionReady) return 'NOT_READY';

        var msgIdBytes = encodeMsgId(msgId);

        var routeBytes = [];
        for (var i = 0; i < route.length; i++) routeBytes.push(route.charCodeAt(i));

        // Body is JSON string
        var bodyBytes = [];
        for (var i = 0; i < bodyJsonStr.length; i++) bodyBytes.push(bodyJsonStr.charCodeAt(i));

        var msgLen = 1 + msgIdBytes.length + 1 + routeBytes.length + bodyBytes.length;
        var msg = new Uint8Array(msgLen);
        var pos = 0;
        msg[pos++] = 0x00; // flag: type=request, route=string
        for (var i = 0; i < msgIdBytes.length; i++) msg[pos++] = msgIdBytes[i];
        msg[pos++] = routeBytes.length;
        for (var i = 0; i < routeBytes.length; i++) msg[pos++] = routeBytes[i];
        for (var i = 0; i < bodyBytes.length; i++) msg[pos++] = bodyBytes[i];

        var pktLen = 4 + msgLen;
        var pkt = new Uint8Array(pktLen);
        pkt[0] = 4;
        pkt[1] = (msgLen >> 16) & 0xFF;
        pkt[2] = (msgLen >> 8) & 0xFF;
        pkt[3] = msgLen & 0xFF;
        for (var i = 0; i < msgLen; i++) pkt[4+i] = msg[i];

        var LWS_PRE = 16;
        var buf = Memory.alloc(LWS_PRE + pktLen);
        var payloadPtr = buf.add(LWS_PRE);
        payloadPtr.writeByteArray(pkt.buffer);

        var r = lws_write_func(currentWsi, payloadPtr, pktLen, 2);
        lastMsgId = msgId;
        return 'OK sent=' + r + ' pkt=' + pktLen;
    }
};

send({t:'ready'});
