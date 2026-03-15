// Inject via SSL_write with proper WebSocket frame + Pomelo Package + Message
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_write_addr = sslmod.findExportByName('SSL_write');
var ssl_read_addr = sslmod.findExportByName('SSL_read');

var ssl_write_func = new NativeFunction(ssl_write_addr, 'int', ['pointer', 'pointer', 'int']);

var gameSSL = null;
var lastMsgId = 0;
var sessionReady = false;
var injectedCount = 0;

function encodeMsgId(id) {
    var bytes = [];
    var tmp = id;
    while (tmp >= 128) { bytes.push((tmp & 0x7F) | 0x80); tmp = tmp >>> 7; }
    bytes.push(tmp & 0x7F);
    return bytes;
}

// Hook SSL_read to capture SSL pointer and incoming messages
Interceptor.attach(ssl_read_addr, {
    onEnter: function(args) {
        this.ssl = args[0];
        this.buf = args[1];
    },
    onLeave: function(ret) {
        var n = ret.toInt32();
        if (n <= 0) return;

        // Capture SSL pointer from successful reads
        if (!gameSSL) {
            gameSSL = this.ssl;
            send({t:'SSL_GOT', addr: this.ssl.toString()});
        }

        try {
            var raw = this.buf.readByteArray(n);
            if (!raw) return;
            var arr = new Uint8Array(raw);

            // WS binary frame from server (unmasked)
            if ((arr[0] === 0x82 || arr[0] === 0x81) && arr.length >= 6) {
                var pl = arr[1] & 0x7F;
                var hl = 2;
                if (pl === 126) { pl = (arr[2]<<8)|arr[3]; hl = 4; }
                else if (pl === 127) { hl = 10; }
                if (hl + pl > arr.length) return;
                var payload = arr.slice(hl, hl+pl);
                if (payload.length < 1) return;

                var pkgType = payload[0];
                if (pkgType === 3) {
                    // Server heartbeat response - session is alive
                    sessionReady = true;
                }
                if (pkgType === 4 && payload.length >= 5) {
                    var msgBody = payload.slice(4);
                    send({t:'SRV', len:msgBody.length}, new Uint8Array(msgBody).buffer);
                } else if (pkgType === 5) {
                    send({t:'KICK'});
                }
            }
        } catch(e) {}
    }
});

// Hook lws_write to capture client requests (for msgId tracking)
var ws = Process.findModuleByName('websockets.dll');
var lws_write = ws.findExportByName('lws_write');
Interceptor.attach(lws_write, {
    onEnter: function(args) {
        var len = args[2].toInt32();
        if (len > 0 && len < 100000) {
            try {
                var raw = args[1].readByteArray(len);
                var arr = new Uint8Array(raw);
                if (arr.length >= 1) {
                    var pkgType = arr[0];
                    if (pkgType === 4 && arr.length >= 5) {
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
                                    send({t:'REQ', id:id, r:route});
                                }
                            }
                        }
                    } else if (pkgType === 3) {
                        sessionReady = true;
                    } else if (pkgType === 1) {
                        sessionReady = false;
                        send({t:'HS'});
                    } else if (pkgType === 2) {
                        sessionReady = true;
                        send({t:'ACK'});
                    }
                }
            } catch(e) {}
        }
    }
});

rpc.exports = {
    status: function() {
        return { rid: lastMsgId, ssl: gameSSL !== null, ready: sessionReady, done: injectedCount };
    },
    inject: function(route, bodyJsonStr, msgId) {
        if (!gameSSL) return 'NO_SSL';

        // Build Pomelo Message
        var msgIdBytes = encodeMsgId(msgId);
        var routeBytes = [];
        for (var i = 0; i < route.length; i++) routeBytes.push(route.charCodeAt(i));
        var bodyBytes = [];
        for (var i = 0; i < bodyJsonStr.length; i++) bodyBytes.push(bodyJsonStr.charCodeAt(i));

        var msgLen = 1 + msgIdBytes.length + 1 + routeBytes.length + bodyBytes.length;
        var msg = new Uint8Array(msgLen);
        var pos = 0;
        msg[pos++] = 0x00; // flag: request, string route
        for (var i = 0; i < msgIdBytes.length; i++) msg[pos++] = msgIdBytes[i];
        msg[pos++] = routeBytes.length;
        for (var i = 0; i < routeBytes.length; i++) msg[pos++] = routeBytes[i];
        for (var i = 0; i < bodyBytes.length; i++) msg[pos++] = bodyBytes[i];

        // Build Pomelo Package (type=4 DATA)
        var pktLen = 4 + msgLen;
        var pkt = new Uint8Array(pktLen);
        pkt[0] = 4;
        pkt[1] = (msgLen >> 16) & 0xFF;
        pkt[2] = (msgLen >> 8) & 0xFF;
        pkt[3] = msgLen & 0xFF;
        for (var i = 0; i < msgLen; i++) pkt[4+i] = msg[i];

        // Build WebSocket binary frame (masked, as client must mask)
        var wsPayloadLen = pktLen;
        var wsHeaderLen;
        if (wsPayloadLen <= 125) {
            wsHeaderLen = 2 + 4; // opcode(1) + len(1) + mask(4)
        } else if (wsPayloadLen <= 65535) {
            wsHeaderLen = 2 + 2 + 4; // opcode(1) + 126(1) + len(2) + mask(4)
        } else {
            wsHeaderLen = 2 + 8 + 4; // opcode(1) + 127(1) + len(8) + mask(4)
        }

        var wsFrame = new Uint8Array(wsHeaderLen + wsPayloadLen);
        var fpos = 0;
        wsFrame[fpos++] = 0x82; // FIN + binary opcode

        if (wsPayloadLen <= 125) {
            wsFrame[fpos++] = 0x80 | wsPayloadLen; // mask bit + len
        } else if (wsPayloadLen <= 65535) {
            wsFrame[fpos++] = 0x80 | 126;
            wsFrame[fpos++] = (wsPayloadLen >> 8) & 0xFF;
            wsFrame[fpos++] = wsPayloadLen & 0xFF;
        }

        // Mask key (random-ish)
        var maskKey = [0x37, 0xfa, 0x21, 0x3d];
        wsFrame[fpos++] = maskKey[0];
        wsFrame[fpos++] = maskKey[1];
        wsFrame[fpos++] = maskKey[2];
        wsFrame[fpos++] = maskKey[3];

        // Masked payload
        for (var i = 0; i < wsPayloadLen; i++) {
            wsFrame[fpos++] = pkt[i] ^ maskKey[i % 4];
        }

        // Send via SSL_write
        var buf = Memory.alloc(wsFrame.length + 16);
        buf.writeByteArray(wsFrame.buffer);
        var r = ssl_write_func(gameSSL, buf, wsFrame.length);
        injectedCount++;

        return 'OK ssl_write=' + r + ' ws_frame=' + wsFrame.length + ' pomelo_pkt=' + pktLen + ' msgId=' + msgId;
    }
};

send({t:'ready'});
