#!/usr/bin/env python3
"""Moved native bundle operates with no checkout reference or Python/gcc PATH."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    print(('ok  ' if ok else 'FAIL'),label,flush=True)
with tempfile.TemporaryDirectory(prefix='hs bundle space ') as temp:
    d=Path(temp);bindir=d/'utilities';bindir.mkdir()
    for name in ['uname','dirname','sha256sum','mktemp','rm','mkdir','cp','chmod','mv','cmp']:
        (bindir/name).symlink_to(shutil.which(name))
    env=dict(os.environ,PATH=str(bindir));env.pop('HSPATH',None);env.pop('HSROOT',None)
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/install-native.sh')],env=env,capture_output=True,text=True,timeout=10)
    check(r.returncode==2 and 'usage:' in r.stderr,'installer requires explicit destination')
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/install-native.sh'),str(d/'absent'/'install')],env=env,capture_output=True,text=True,timeout=10)
    check(r.returncode!=0 and not (d/'absent').exists(),'missing parent does not create or change directories')
    # A second-driver build failure must not publish a partial installation.
    broken=d/'broken checkout'
    broken.mkdir()
    for name in ('scripts','bootstrap','selfhost','runtime','std'):
        shutil.copytree(ROOT/name,broken/name)
    (broken/'selfhost/be/irinterp_run.holy').write_text('def broken(:\n')
    failed_install=d/'failed install'
    r=subprocess.run(['/bin/sh',str(broken/'scripts/install-native.sh'),str(failed_install)],env=env,capture_output=True,text=True,timeout=240)
    check(r.returncode!=0 and not failed_install.exists() and not list(d.glob('.holyshit-bundle.*')),'interpreter build failure cleans staging without publishing')
    original=d/'original';moved=d/'moved bundle'
    started=time.monotonic()
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/install-native.sh'),str(original)],env=env,capture_output=True,text=True,timeout=240)
    print('METRIC candidate_install_wall_seconds',round(time.monotonic()-started,3),flush=True)
    check(r.returncode==0,'build '+r.stderr[-150:])
    if r.returncode:sys.exit(1)
    original.rename(moved)
    launcher=moved/'bin/hs';compiler=moved/'bootstrap/hs-hosted-x86_64'
    r=subprocess.run(['/bin/sh',str(launcher),'fmt','input.holy'],env=env,capture_output=True,text=True,timeout=10)
    check(r.returncode==2 and 'unknown command' in r.stderr,'unsupported development command is explicit, no fallback')
    source=d/'main file.holy';module=d/'support.holy';module.write_text('value = 19\n')
    source.write_text('import support\nprint support.value\nprint json_str([1, "ok"])\nprint argv()\nextern:\n  I64 printf(Str format, ..., I64 n)\nprintf("value=%lld\\n", 27)\n')
    expected='19\n[1, "ok"]\n[hello world, $5]\nvalue=27\n'
    # Keep PATH isolated and all sources outside both bundle and checkout.
    r=subprocess.run(['/bin/sh',str(launcher),'run',source.name,'hello world','$5'],cwd=d,env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout==expected,'relocated eager JSON/import/argv/variadic '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    exe=d/'program'
    r=subprocess.run(['/bin/sh',str(launcher),'build',source.name,str(exe)],cwd=d,env=env,capture_output=True,text=True,timeout=60)
    if r.returncode==0:r=subprocess.run([str(exe),'hello world','$5'],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout==expected,'relocated AOT '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    local=dict(env,HSROOT=str(moved),HSPATH=str(moved/'selfhost')+':'+str(moved/'selfhost/be'))
    stage=d/'stage2'
    if '--skip-selfcompile' not in sys.argv:
        r=subprocess.run([str(compiler),str(moved/'selfhost/be/compile.holy'),str(stage)],env=local,capture_output=True,text=True,timeout=180)
        check(r.returncode==0 and stage.read_bytes()==compiler.read_bytes(),'relocated compiler self-compilation')
    # Explicit interpreter: moved bundle, no Python/gcc, no launch-time build.
    interp=moved/'bin/hs-interp'
    print('METRIC installed_interpreter_bytes',interp.stat().st_size,flush=True)
    interp_before=interp.read_bytes()
    interp_mtime=interp.stat().st_mtime_ns
    env['HS_BUNDLE_INTERP']='installed'
    r=subprocess.run(['/bin/sh',str(launcher),'interpret'],env=env,capture_output=True,text=True,timeout=10)
    check(r.returncode==2 and 'usage:' in r.stderr,'interpret requires source')
    source.write_text('import support\nprint support.value\nprint argv()\nprint env("HS_BUNDLE_INTERP")\ntry:\n  raise "caught"\nexcept:\n  print json_str([1, "ok"])\n')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',source.name,'hello world','$5'],cwd=d,env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and not r.stderr and r.stdout=='19\n[hello world, $5]\ninstalled\n[1, "ok"]\n','relocated explicit interpreter args/import/env/JSON/try '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    check(interp.stat().st_mtime_ns==interp_mtime and interp.read_bytes()==interp_before,'interpret does not rebuild installed driver')
    source.write_text('print "before"\nprint 1 / 0\n')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==1 and r.stdout=='before\n' and 'division by zero' in r.stderr,'interpret runtime failure preserves output and status')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(d/'absent.holy')],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==1 and not r.stdout and 'error:' in r.stderr,'interpret missing source failure')
    source.write_text('def broken(:\n')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==1 and not r.stdout and 'error:' in r.stderr,'interpret parse failure')
    for label,text in [('unsafe','unsafe:\n  Ptr p = alloc(8)\n'),('ffi','extern:\n  I64 puts(Str s)\nputs("must not run")\n')]:
        source.write_text('print "TARGET RAN"\n'+text)
        r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
        check(r.returncode==3 and not r.stdout and 'irinterp: unsupported' in r.stderr,'interpret '+label+' refused before effects')
    module.write_text('print "MODULE RAN"\nunsafe:\n  Ptr p = alloc(8)\n')
    source.write_text('print "TARGET RAN"\nimport support\n')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==3 and not r.stdout and 'irinterp: unsupported' in r.stderr,'interpret import graph refused before effects')
    module.write_text('value = 19\n')
    interp.write_bytes(interp_before+b'changed')
    source.write_text('print "TARGET RAN"\n')
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and not r.stdout,'corrupt interpreter refused before target execution')
    # Corrupting this optional execution route must not change run/build.
    source.write_text('print 23\n')
    r=subprocess.run(['/bin/sh',str(launcher),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout=='23\n','run independent of interpreter checksum')
    r=subprocess.run(['/bin/sh',str(launcher),'build',str(source),str(exe)],env=env,capture_output=True,text=True,timeout=60)
    if r.returncode==0:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout=='23\n','build independent of interpreter checksum')
    interp.write_bytes(interp_before)
    sums=moved/'INTERP_SHA256SUMS'
    saved_sums=sums.read_bytes()
    sums.unlink()
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==1 and not r.stdout and 'install a new complete bundle' in r.stderr,'missing interpreter manifest reports incomplete bundle')
    sums.write_bytes(saved_sums)
    interp.unlink()
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==1 and not r.stdout and 'install a new complete bundle' in r.stderr,'missing interpreter binary reports incomplete bundle')
    interp.write_bytes(interp_before)
    interp.chmod(0o755)
    r=subprocess.run(['/bin/sh',str(launcher),'interpret',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout=='23\n','restored interpreter works')
    source.write_text('print 1 / 0\n')
    r=subprocess.run(['/bin/sh',str(launcher),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and 'division by zero' in r.stderr,'runtime error status')
    source.write_text('if\n');exe.write_bytes(b'preserve')
    r=subprocess.run(['/bin/sh',str(launcher),'build',str(source),str(exe)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and exe.read_bytes()==b'preserve','invalid source preserves output')
    source.write_text('print "TARGET RAN"\n')
    eager=moved/'bin/hs-eager';data=eager.read_bytes();eager.write_bytes(data+b'changed')
    r=subprocess.run(['/bin/sh',str(launcher),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and 'TARGET RAN' not in r.stdout,'corrupt eager binary refused before execution')
    eager.write_bytes(data)
    before=(moved/'EAGER_SHA256SUMS').read_bytes()
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/install-native.sh'),str(moved)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and (moved/'EAGER_SHA256SUMS').read_bytes()==before,'existing directory refused')
print(f'{passed}/{passed+failed} relocated native bundle gates (PATH without Python/gcc)')
sys.exit(bool(failed))
