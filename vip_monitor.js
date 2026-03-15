var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read = sslmod.findExportByName('SSL_read');
var ssl_write = sslmod.findExportByName('SSL_write');
var gameSSL = null;

function toHex(b) { return ('0'+b.toString(16)).slice(-2); }
function bytesToHex(arr, start, end) {
    var h = '';
    for (var i = start; i < end; i++) h += toHex(arr[i]) + ' ';
    return h;
}
function bytesToStr(arr, start, end) {
    var s = '';
    for (var i = start; i < end; i++) {
        var c = arr[i];
        if (c >= 32 && c < 127) s += String.fromCharCode(c);
        else s += '.';
    }
    return s;
}

function parseWS(arr) {
    if (arr.length < 2) return null;
    var masked = (arr[1] & 0x80) !== 0;
    var pl = arr[1] & 0x7F;
    var hl = 2;
    if (pl === 126) { pl = (arr[2]<<8)|arr[3]; hl = 4; }
    else if (pl === 127) { hl = 10; pl = 0; for(var i=2;i<10;i++) pl = pl*256+arr[i]; }
    if (masked) hl += 4;
    if (hl + pl > arr.length) return null;
    
    var payload;
    if (masked) {
        var mk = [arr[hl-4], arr[hl-3], arr[hl-2], arr[hl-1]];
        payload = new Uint8Array(pl);
        for (var i = 0; i < pl; i++) payload[i] = arr[hl+i] ^ mk[i%4];
    } else {
        payload = arr.slice(hl, hl+pl);
    }
    return payload;
}

Interceptor.attach(ssl_write, {
    onEnter: function(args) {
        this.ssl = args[0];
        this.buf = args[1];
        this.len = args[2].toInt32();
    },
    onLeave: function(ret) {
        if (this.len <= 0) return;
        var raw = this.buf.readByteArray(this.len);
        if (!raw) return;
        var arr = new Uint8Array(raw);
        if (arr[0] !== 0x82 && arr[0] !== 0x81) return;
        gameSSL = this.ssl;
        
        var payload = parseWS(arr);
        if (!payload || payload.length < 5) return;
        
        var ptype = payload[0];
        if (ptype !== 0) return; // Only REQUEST
        
        var reqId = (payload[1]<<16)|(payload[2]<<8)|payload[3];
        var routeLen = payload[4];
        if (5 + routeLen > payload.length) return;
        
        var route = '';
        for (var i = 0; i < routeLen; i++) route += String.fromCharCode(payload[5+i]);
        
        var bodyStart = 5 + routeLen;
        var bodyHex = bytesToHex(payload, bodyStart, Math.min(payload.length, bodyStart+100));
        var bodyAscii = bytesToStr(payload, bodyStart, Math.min(payload.length, bodyStart+200));
        
        send({t:'REQ', route:route, reqId:reqId, bodyHex:bodyHex, bodyAscii:bodyAscii, bodyLen:payload.length-bodyStart});
    }
});

Interceptor.attach(ssl_read, {
    onEnter: function(args) {
        this.ssl = args[0];
        this.buf = args[1];
    },
    onLeave: function(ret) {
        var n = ret.toInt32();
        if (n <= 0) return;
        var raw = this.buf.readByteArray(n);
        if (!raw) return;
        var arr = new Uint8Array(raw);
        if ((arr[0] !== 0x82 && arr[0] !== 0x81) || arr.length < 6) return;
        
        var payload = parseWS(arr);
        if (!payload || payload.length < 4) return;
        
        var ptype = payload[0];
        var body;
        
        if (ptype === 2) { // RESPONSE
            var reqId = (payload[1]<<16)|(payload[2]<<8)|payload[3];
            body = bytesToStr(payload, 4, Math.min(payload.length, 304));
            var hex = bytesToHex(payload, 4, Math.min(payload.length, 54));
            send({t:'RESP', reqId:reqId, body:body, hex:hex, len:payload.length-4});
        }
        
        if (ptype === 4) { // PUSH
            body = bytesToStr(payload, 4, Math.min(payload.length, 304));
            if (body.length > 10) {
                send({t:'PUSH', body:body, len:payload.length-4});
            }
        }
    }
});

send({t:'ready'});
