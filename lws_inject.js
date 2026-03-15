var ws = Process.findModuleByName('websockets.dll');
var lws_write_addr = ws.findExportByName('lws_write');
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');

var lws_write_func = new NativeFunction(lws_write_addr, 'int', ['pointer', 'pointer', 'int', 'int']);

var capturedWsi = null;
var writeCount = 0;
var lastReqId = 0;

Interceptor.attach(lws_write_addr, {
    onEnter: function(args) {
        this.wsi = args[0];
        this.buf = args[1];
        this.len = args[2].toInt32();
        this.wp = args[3].toInt32();
        writeCount++;

        if (!capturedWsi) {
            capturedWsi = this.wsi;
            send({t:'WSI_CAPTURED', addr: this.wsi.toString()});
        }

        if (this.len > 0 && this.len < 100000) {
            try {
                var raw = this.buf.readByteArray(this.len);
                var arr = new Uint8Array(raw);
                var preview = '';
                for (var i = 0; i < Math.min(arr.length, 30); i++) {
                    preview += ('0' + arr[i].toString(16)).slice(-2) + ' ';
                }
                send({t:'LWS_WRITE', n:writeCount, len:this.len, wp:this.wp, preview:preview});

                if (arr.length >= 4) {
                    var ptype = arr[0];
                    if (ptype === 0) {
                        var reqId = (arr[1]<<16)|(arr[2]<<8)|arr[3];
                        lastReqId = reqId;
                        if (arr.length > 4) {
                            var routeLen = arr[4];
                            if (5 + routeLen <= arr.length) {
                                var route = '';
                                for (var i = 0; i < routeLen; i++) route += String.fromCharCode(arr[5+i]);
                                send({t:'CLIENT_REQ', reqId:reqId, route:route, bodyLen:arr.length - 5 - routeLen});
                            }
                        }
                    }
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
            if (payload.length < 4) return;

            var ptype = payload[0];
            if (ptype === 2 || ptype === 4) {
                send({t:'SRV_MSG', ptype:ptype, len:payload.length}, new Uint8Array(payload).buffer);
            }
        } catch(e) {}
    }
});

rpc.exports = {
    get_state: function() {
        return {
            last_req_id: lastReqId,
            has_wsi: capturedWsi !== null,
            writes: writeCount
        };
    },
    inject_pomelo: function(route, bodyHexStr, reqId) {
        if (!capturedWsi) return 'NO_WSI';

        var rb = [];
        for (var i = 0; i < route.length; i++) rb.push(route.charCodeAt(i));

        var bb = [];
        if (bodyHexStr && bodyHexStr.length > 0) {
            var parts = bodyHexStr.split(' ');
            for (var i = 0; i < parts.length; i++) {
                if (parts[i].length === 2) bb.push(parseInt(parts[i], 16));
            }
        }

        var pktLen = 4 + 1 + rb.length + bb.length;
        var pkt = new Uint8Array(pktLen);
        pkt[0] = 0;
        pkt[1] = (reqId >> 16) & 0xFF;
        pkt[2] = (reqId >> 8) & 0xFF;
        pkt[3] = reqId & 0xFF;
        pkt[4] = rb.length;
        for (var i = 0; i < rb.length; i++) pkt[5+i] = rb[i];
        for (var i = 0; i < bb.length; i++) pkt[5+rb.length+i] = bb[i];

        var LWS_PRE = 16;
        var totalLen = LWS_PRE + pktLen;
        var buf = Memory.alloc(totalLen);
        var payloadPtr = buf.add(LWS_PRE);
        payloadPtr.writeByteArray(pkt.buffer);

        var r = lws_write_func(capturedWsi, payloadPtr, pktLen, 2);
        lastReqId = reqId;
        return 'OK sent=' + r + ' pktLen=' + pktLen;
    }
};

send({t:'ready'});
