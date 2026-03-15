var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
var ssl_write_addr = sslmod.findExportByName("SSL_write");
var gameSSL = null;
var ssl_write_func = new NativeFunction(ssl_write_addr, "int", ["pointer", "pointer", "int"]);

var lastReqId = 0;
var clientRoutes = {};
var writeCount = 0;

// Single hook for SSL_write - capture everything
Interceptor.attach(ssl_write_addr, {
    onEnter: function(args) {
        this.ssl = args[0];
        this.buf = args[1];
        this.len = args[2].toInt32();

        // Read buffer NOW in onEnter (before it might be modified)
        if (this.len > 0 && this.len < 100000) {
            try {
                this.raw = this.buf.readByteArray(this.len);
            } catch(e) {
                this.raw = null;
            }
        }

        writeCount++;

        // Log ALL writes for first 50
        if (writeCount <= 50) {
            var preview = '';
            if (this.raw) {
                var arr = new Uint8Array(this.raw);
                for (var i = 0; i < Math.min(arr.length, 20); i++) {
                    preview += ('0' + arr[i].toString(16)).slice(-2) + ' ';
                }
            }
            send({t:'WRITE_RAW', n:writeCount, len:this.len, preview:preview});
        }
    },
    onLeave: function(ret) {
        if (!this.raw) return;
        var arr = new Uint8Array(this.raw);

        // Check for WS binary frame
        if (arr[0] === 0x82 || arr[0] === 0x81) {
            gameSSL = this.ssl;

            // Parse WS
            var masked = (arr[1] & 0x80) !== 0;
            var pl = arr[1] & 0x7F;
            var hl = 2;
            if (pl === 126) { pl = (arr[2]<<8)|arr[3]; hl = 4; }
            if (masked) hl += 4;
            if (hl + pl > arr.length) return;

            var payload;
            if (masked) {
                var mk = [arr[hl-4], arr[hl-3], arr[hl-2], arr[hl-1]];
                payload = new Uint8Array(pl);
                for (var i = 0; i < pl; i++) payload[i] = arr[hl+i] ^ mk[i%4];
            } else {
                payload = arr.slice(hl, hl+pl);
            }

            if (payload.length < 4) return;
            var ptype = payload[0];

            // Log pomelo type
            send({t:'WRITE_POMELO', ptype:ptype, payloadLen:payload.length});

            if (ptype === 0) { // REQUEST
                var reqId = (payload[1]<<16)|(payload[2]<<8)|payload[3];
                var routeLen = payload[4];
                if (5 + routeLen <= payload.length) {
                    var route = '';
                    for (var i = 0; i < routeLen; i++) route += String.fromCharCode(payload[5+i]);

                    lastReqId = reqId;
                    clientRoutes[reqId] = route;

                    var bodyStart = 5 + routeLen;
                    var bodyBytes = payload.slice(bodyStart);
                    var bodyHex = '';
                    var bodyStr = '';
                    for (var i = 0; i < Math.min(bodyBytes.length, 100); i++) {
                        bodyHex += ('0' + bodyBytes[i].toString(16)).slice(-2) + ' ';
                        var c = bodyBytes[i];
                        bodyStr += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
                    }

                    send({t:'CLIENT_REQ', reqId:reqId, route:route, bodyLen:bodyBytes.length, bodyStr:bodyStr, bodyHex:bodyHex});
                }
            }
            if (ptype === 3) { // HEARTBEAT
                send({t:'HEARTBEAT_SEND'});
            }
        }
    }
});

// Monitor incoming
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
            if (hl + pl > arr.length) return;
            var payload = arr.slice(hl, hl+pl);
            if (payload.length < 4) return;

            var ptype = payload[0];
            if (ptype === 2 || ptype === 4) {
                send({t:'SRV_MSG', ptype:ptype, len:payload.length}, new Uint8Array(payload).buffer);
            }
        } catch(e) {}
    }
});

rpc.exports = {
    getState: function() {
        return {lastReqId: lastReqId, hasSSL: gameSSL !== null, routes: clientRoutes, writes: writeCount};
    },
    injectRaw: function(route, bodyHexStr, reqId) {
        if (!gameSSL) return 'NO_SSL';
        var rb = []; for (var i = 0; i < route.length; i++) rb.push(route.charCodeAt(i));
        var bb = [];
        if (bodyHexStr && bodyHexStr.length > 0) {
            var parts = bodyHexStr.split(' ');
            for (var i = 0; i < parts.length; i++) {
                if (parts[i].length === 2) bb.push(parseInt(parts[i], 16));
            }
        }
        var pl = 1 + rb.length + bb.length;
        var p = new Uint8Array(4 + pl);
        p[0] = 0;
        p[1] = (reqId >> 16) & 0xFF;
        p[2] = (reqId >> 8) & 0xFF;
        p[3] = reqId & 0xFF;
        p[4] = rb.length;
        for (var i = 0; i < rb.length; i++) p[5+i] = rb[i];
        for (var i = 0; i < bb.length; i++) p[5+rb.length+i] = bb[i];
        var wl = p.length;
        var wh = (wl <= 125) ? 6 : 8;
        var ws = new Uint8Array(wh + wl);
        ws[0] = 0x82;
        if (wl <= 125) { ws[1] = 0x80 | wl; }
        else { ws[1] = 0x80 | 126; ws[2] = (wl>>8)&0xFF; ws[3] = wl&0xFF; }
        var mo = wh - 4;
        ws[mo] = 0x37; ws[mo+1] = 0xfa; ws[mo+2] = 0x21; ws[mo+3] = 0x3d;
        for (var i = 0; i < wl; i++) ws[wh+i] = p[i] ^ ws[mo + (i%4)];
        var buf = Memory.alloc(ws.length);
        buf.writeByteArray(ws.buffer);
        var r = ssl_write_func(gameSSL, buf, ws.length);
        lastReqId = reqId;
        return 'OK sent=' + r + ' bytes';
    }
};

send({t:'ready'});
