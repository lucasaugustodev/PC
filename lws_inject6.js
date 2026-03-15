var ws = Process.findModuleByName('websockets.dll');
var lws_write_addr = ws.findExportByName('lws_write');
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');

var lws_write_func = new NativeFunction(lws_write_addr, 'int', ['pointer', 'pointer', 'int', 'int']);

var writeCount = 0;
var lastMsgId = 0;
var sessionReady = false;

var injectQueue = [];
var injectedCount = 0;
// Keep references to allocated memory so GC doesn't free them
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
        this.isHeartbeat = false;
        writeCount++;

        if (this.len > 0 && this.len < 100000) {
            try {
                var raw = args[1].readByteArray(this.len);
                var arr = new Uint8Array(raw);

                if (arr.length >= 1) {
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
                                    for (var i = bStart; i < Math.min(arr.length, bStart+100); i++) {
                                        var c = arr[i];
                                        bs += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
                                    }
                                    send({t:'REQ', id:id, r:route, bl:bLen, bs:bs});
                                }
                            }
                        }
                    } else if (pkgType === 3) {
                        this.isHeartbeat = true;
                        sessionReady = true;
                    } else if (pkgType === 1) {
                        sessionReady = false;
                        send({t:'HS'});
                    } else if (pkgType === 2) {
                        sessionReady = true;
                        send({t:'ACK'});
                    }
                }

                if (this.wp === 4) {
                    send({t:'CLOSE'});
                }
            } catch(e) {}
        }
    },
    onLeave: function(ret) {
        // After heartbeat write completes successfully, inject queued packets
        // We're on the lws event loop thread, so lws_write is safe to call
        if (this.isHeartbeat && ret.toInt32() >= 0 && injectQueue.length > 0) {
            var pktInfo = injectQueue.shift();
            injectedCount++;

            // pktInfo has: {buf, ptr, len}
            var r = lws_write_func(this.wsi, pktInfo.ptr, pktInfo.len, 2);
            send({t:'INJECTED', n:injectedCount, len:pktInfo.len, ret:r});
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
            queue: injectQueue.length,
            done: injectedCount
        };
    },
    enqueue: function(route, bodyJsonStr, msgId) {
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

        // Allocate buffer with LWS_PRE padding and write packet
        var LWS_PRE = 16;
        var buf = Memory.alloc(LWS_PRE + pktLen + 16);
        var writePtr = buf.add(LWS_PRE);
        writePtr.writeByteArray(pkt.buffer);

        // Keep reference to prevent GC
        var info = {buf: buf, ptr: writePtr, len: pktLen};
        allocations.push(info);
        injectQueue.push(info);

        lastMsgId = msgId;
        return 'QUEUED #' + injectQueue.length + ' pkt=' + pktLen + ' msgId=' + msgId;
    }
};

send({t:'ready'});
