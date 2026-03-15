// Debug script: log exact sequence of ssl_read and lws_write events
// to determine if close 1002 comes from server or client
var ws = Process.findModuleByName('websockets.dll');
var lws_write_addr = ws.findExportByName('lws_write');
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');
var ssl_write = sslmod.findExportByName('SSL_write');

var lws_write_func = new NativeFunction(lws_write_addr, 'int', ['pointer', 'pointer', 'int', 'int']);

var seq = 0;
var lastMsgId = 0;
var sessionReady = false;
var currentWsi = null;
var pendingInject = null;
var injectedCount = 0;
var allocations = [];
var injectOnNextHeartbeat = false;

function encodeMsgId(id) {
    var bytes = [];
    var tmp = id;
    while (tmp >= 128) { bytes.push((tmp & 0x7F) | 0x80); tmp = tmp >>> 7; }
    bytes.push(tmp & 0x7F);
    return bytes;
}

// Hook SSL_write to see raw TLS writes
Interceptor.attach(ssl_write, {
    onEnter: function(args) {
        var len = args[2].toInt32();
        if (len > 0 && len < 100000) {
            var raw = args[1].readByteArray(Math.min(len, 20));
            var arr = new Uint8Array(raw);
            var preview = '';
            for (var i = 0; i < arr.length; i++) preview += ('0'+arr[i].toString(16)).slice(-2)+' ';
            seq++;
            send({t:'SSL_W', s:seq, len:len, p:preview});
        }
    }
});

// Hook SSL_read
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(ret) {
        var n = ret.toInt32();
        if (n <= 0) return;
        try {
            var raw = this.buf.readByteArray(Math.min(n, 30));
            var arr = new Uint8Array(raw);
            var preview = '';
            for (var i = 0; i < arr.length; i++) preview += ('0'+arr[i].toString(16)).slice(-2)+' ';
            seq++;

            // Check for WS close frame (opcode 0x88)
            if (arr[0] === 0x88) {
                var closeCode = -1;
                if (n >= 4) closeCode = (arr[2]<<8)|arr[3];
                send({t:'SSL_R_CLOSE', s:seq, code:closeCode, len:n, p:preview});
            } else if (arr[0] === 0x82 || arr[0] === 0x81) {
                // WS binary/text frame
                var pl = arr[1] & 0x7F;
                send({t:'SSL_R_WS', s:seq, len:n, pl:pl, p:preview});
            } else {
                send({t:'SSL_R', s:seq, len:n, p:preview});
            }
        } catch(e) {}
    }
});

Interceptor.attach(lws_write_addr, {
    onEnter: function(args) {
        this.wsi = args[0];
        this.len = args[2].toInt32();
        this.wp = args[3].toInt32();
        this.doInject = false;
        currentWsi = this.wsi;

        if (this.len > 0 && this.len < 100000) {
            try {
                var raw = args[1].readByteArray(this.len);
                var arr = new Uint8Array(raw);
                var pkgType = arr[0];
                seq++;

                if (pkgType === 3) {
                    sessionReady = true;
                    send({t:'LWS_HB', s:seq});
                    if (injectOnNextHeartbeat && pendingInject) {
                        this.doInject = true;
                    }
                } else if (pkgType === 4 && arr.length >= 5) {
                    var msgFlag = arr[4];
                    var msgType = (msgFlag >> 1) & 0x07;
                    if (msgType === 0) {
                        var id = 0, shift = 0, pos = 5;
                        while (pos < arr.length) {
                            var b = arr[pos]; id |= (b & 0x7F) << shift; pos++;
                            if ((b & 0x80) === 0) break; shift += 7;
                        }
                        lastMsgId = id;
                        if (pos < arr.length) {
                            var rl = arr[pos]; pos++;
                            if (pos + rl <= arr.length) {
                                var route = '';
                                for (var i = 0; i < rl; i++) route += String.fromCharCode(arr[pos+i]);
                                send({t:'LWS_REQ', s:seq, id:id, r:route});
                            }
                        }
                    }
                } else if (pkgType === 1) {
                    sessionReady = false;
                    send({t:'LWS_HS', s:seq});
                } else if (pkgType === 2) {
                    sessionReady = true;
                    send({t:'LWS_ACK', s:seq});
                }

                if (this.wp === 4) {
                    var preview = '';
                    for (var i = 0; i < Math.min(arr.length, 10); i++) preview += ('0'+arr[i].toString(16)).slice(-2)+' ';
                    send({t:'LWS_CLOSE', s:seq, p:preview});
                }
            } catch(e) {}
        }
    },
    onLeave: function(ret) {
        if (this.doInject && pendingInject) {
            var pi = pendingInject;
            pendingInject = null;
            injectOnNextHeartbeat = false;
            injectedCount++;
            seq++;
            send({t:'INJECT_START', s:seq, mid:pi.msgId, len:pi.len});

            var r = lws_write_func(this.wsi, pi.ptr, pi.len, 2);
            seq++;
            send({t:'INJECT_DONE', s:seq, ret:r});
        }
    }
});

rpc.exports = {
    status: function() {
        return { rid: lastMsgId, ready: sessionReady, pending: pendingInject !== null, done: injectedCount };
    },
    arm: function(route, bodyJsonStr, msgId) {
        var msgIdBytes = encodeMsgId(msgId);
        var routeBytes = [];
        for (var i = 0; i < route.length; i++) routeBytes.push(route.charCodeAt(i));
        var bodyBytes = [];
        for (var i = 0; i < bodyJsonStr.length; i++) bodyBytes.push(bodyJsonStr.charCodeAt(i));

        var msgLen = 1 + msgIdBytes.length + 1 + routeBytes.length + bodyBytes.length;
        var msg = new Uint8Array(msgLen);
        var pos = 0;
        msg[pos++] = 0x00;
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
        var buf = Memory.alloc(LWS_PRE + pktLen + 32);
        var writePtr = buf.add(LWS_PRE);
        writePtr.writeByteArray(pkt.buffer);

        var info = {buf: buf, ptr: writePtr, len: pktLen, msgId: msgId};
        allocations.push(info);
        pendingInject = info;
        injectOnNextHeartbeat = true;

        return 'ARMED msgId=' + msgId;
    }
};

send({t:'ready'});
