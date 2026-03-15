// Find lws_callback_on_writable and discover the protocol callback function
var ws = Process.findModuleByName('websockets.dll');

// List all exports from websockets.dll
var exports = ws.enumerateExports();
var lwsExports = [];
for (var i = 0; i < exports.length; i++) {
    lwsExports.push(exports[i].name);
}
send({t:'exports', count: lwsExports.length, list: lwsExports.join('\n')});

// Look for key functions
var cow = ws.findExportByName('lws_callback_on_writable');
send({t:'cow', found: cow !== null, addr: cow ? cow.toString() : 'null'});

var lws_write_addr = ws.findExportByName('lws_write');

// Hook lws_write and capture the return address to find the callback
Interceptor.attach(lws_write_addr, {
    onEnter: function(args) {
        // Get return address - this tells us WHO called lws_write
        var retAddr = this.returnAddress;
        var mod = Process.findModuleByAddress(retAddr);
        send({t:'caller', ret: retAddr.toString(), mod: mod ? mod.name : 'unknown',
              offset: mod ? '0x' + retAddr.sub(mod.base).toString(16) : '?'});
    }
});

send({t:'ready'});
