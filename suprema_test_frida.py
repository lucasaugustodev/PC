"""Simple test - just attach and enumerate a few exports"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    pid = 67336
    print(f"Attaching to {pid}...")
    sess = frida.attach(pid)
    print("Attached!")

    js = r'''
    send({t: "hello"});
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    if (libcocos) {
        send({t: "cocos", base: libcocos.base.toString(), size: libcocos.size});
    } else {
        send({t: "no_cocos"});
    }
    '''

    sc = sess.create_script(js)
    def on_msg(msg, data):
        print(f"MSG: {json.dumps(msg)}")

    sc.on('message', on_msg)
    sc.load()
    time.sleep(2)
    sc.unload()
    sess.detach()
    print("Done")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
