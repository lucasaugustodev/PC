var ws = Process.findModuleByName('websockets.dll');
var lws_write_addr = ws.findExportByName('lws_write');
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');

var lws_write_func = new NativeFunction(lws_write_addr, 'int', ['pointer', 'pointer', 'int', 'int']);

var writeCount = 0;
var lastMsgId = 0;
var sessionReady = false;
var connectSeen = false;
var postConnectCount = 0;
var readyToInject = false;
var currentWsi = null;

// Pending inject: will be sent on next heartbeat AFTER reconnect completes
var pendingInject = null;
var injectedCount = 0;
var allocations = [];

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

Interceptor.attach(lws_write_addr, {
    onEnter: function(args) {
        this.wsi = args[0];
        this.len = args[2].toInt32();
        this.wp = args[3].toInt32();
        this.isInjectableHeartbeat = false;
        writeCount++;
        currentWsi = this.wsi;

        if (this.len > 0 && this.len < 100000) {
            try {
                var raw = args[1].readByteArray(this.len);
                var arr = new Uint8Array(raw);
                if (arr.length < 1) return;

                var pkgType = arr[0];

                if (pkgType === 4 && arr.length >= 5) {
                    var msgFlag = arr[4];
                    var msgType = (msgFlag >> 1) & 0x07;
                    if (msgType === 0) {
                        var id = 0, shift = 0, pos = 5;
                        while (pos < arr.length) {
                            var b = arr[pos];
                            id |= (b & 0x7F) << shift;
                            pos++;
                            if ((b & 0x80) === 0) break;
                            shift += 7;
                        }
                        lastMsgId = id;
                        if (pos < arr.length) {
                            var rl = arr[pos]; pos++;
                            if (pos + rl <= arr.length) {
                                var route = '';
                                for (var i = 0; i < rl; i++) route += String.fromCharCode(arr[pos+i]);
                                var bStart = pos + rl;
                                var bLen = arr.length - bStart;
                                var bs = '';
                                for (var i = bStart; i < Math.min(arr.length, bStart+80); i++) {
                                    var c = arr[i];
                                    bs += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
                                }
                                send({t:'REQ', id:id, r:route, bl:bLen, bs:bs});

                                if (route === 'connector.entryHandler.connect') {
                                    connectSeen = true;
                                    postConnectCount = 0;
                                    readyToInject = false;
                                } else if (connectSeen) {
                                    postConnectCount++;
                                    // After connect + 2 more requests, we're ready
                                    if (postConnectCount >= 2) {
                                        readyToInject = true;
                                        send({t:'READY_INJECT', lastId: lastMsgId});
                                    }
                                }
                            }
                        }
                    }
                } else if (pkgType === 3) {
                    sessionReady = true;
                    // Only inject on heartbeat AFTER reconnect+login sequence
                    if (readyToInject && pendingInject) {
                        this.isInjectableHeartbeat = true;
                    }
                } else if (pkgType === 1) {
                    sessionReady = false;
                    connectSeen = false;
                    readyToInject = false;
                    send({t:'HS'});
                } else if (pkgType === 2) {
                    sessionReady = true;
                    send({t:'ACK'});
                }

                if (this.wp === 4) {
                    send({t:'CLOSE'});
                }
            } catch(e) {
                send({t:'ERR', m: e.message});
            }
        }
    },
    onLeave: function(ret) {
        if (this.isInjectableHeartbeat && pendingInject && ret.toInt32() >= 0) {
            var pi = pendingInject;
            pendingInject = null;
            readyToInject = false;
            injectedCount++;

            var r = lws_write_func(this.wsi, pi.ptr, pi.len, 2);
            send({t:'INJECTED', n:injectedCount, len:pi.len, ret:r, mid: pi.msgId});
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
            wc: writeCount,
            ready: sessionReady,
            rinj: readyToInject,
            pending: pendingInject !== null,
            done: injectedCount,
            conn: connectSeen,
            pcr: postConnectCount
        };
    },
    enqueue: function(route, bodyJsonStr, usemsgid) {
        // If usemsgid <= 0, auto-calculate from lastMsgId
        var msgId = usemsgid > 0 ? usemsgid : (lastMsgId + 1);

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
        var buf = Memory.alloc(LWS_PRE + pktLen + 16);
        var writePtr = buf.add(LWS_PRE);
        writePtr.writeByteArray(pkt.buffer);

        var info = {buf: buf, ptr: writePtr, len: pktLen, msgId: msgId};
        allocations.push(info);
        pendingInject = info;

        return 'PENDING msgId=' + msgId + ' pkt=' + pktLen + ' route=' + route;
    }
};

send({t:'ready'});
