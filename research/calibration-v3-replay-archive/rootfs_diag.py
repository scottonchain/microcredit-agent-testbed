#!/usr/bin/env python3
"""Diagnostics run INSIDE the image rootfs by run_acceptance_in_image_rootfs.sh, with the archived interpreter (which carries
only the stdlib modules the replay imports: no socket, so the network check reads /proc/net). Shows: which files the
interpreter maps after importing what the replay imports and after one NSS lookup (the glibc in use is the image's, not the
host's; the host-only NSS module libnss_sss is absent), the interfaces and routes of the network namespace (must be
loopback only, no route), and the two bound glibc files hashed from inside."""
import os, sys, json, random, hashlib, re, collections, pwd
try:
    pwd.getpwuid(os.getuid())  # the kind of lookup that mapped libnss_sss.so.2 on the operator host
    print("getpwuid: ok")
except KeyError as e:
    print("getpwuid: KeyError", e)
mapped = sorted({l.split()[-1] for l in open("/proc/self/maps") if len(l.split()) >= 6 and l.split()[-1].startswith("/")})
print("python:", sys.version.split()[0], "| executable:", sys.executable)
print("mapped files (%d):" % len(mapped))
for p in mapped:
    print("  ", p)
for p in ("/usr/lib64/libc.so.6", "/usr/lib64/ld-linux-x86-64.so.2"):
    print("sha256", p, hashlib.sha256(open(p, "rb").read()).hexdigest())
print("os-release:", [l.strip() for l in open("/etc/os-release") if l.startswith("PRETTY_NAME")])
print("nsswitch passwd:", [l.strip() for l in open("/etc/nsswitch.conf") if l.startswith("passwd")])
print("libnss_sss.so.2 present in rootfs:", os.path.exists("/usr/lib64/libnss_sss.so.2"))
print("libnss_files.so.2 present in rootfs:", os.path.exists("/usr/lib64/libnss_files.so.2"))
ifaces = [l.split(":")[0].strip() for l in open("/proc/net/dev").read().splitlines()[2:] if ":" in l]
routes = open("/proc/net/route").read().splitlines()[1:]
print("network namespace interfaces:", ifaces, "| routes:", len(routes))
print("network: isolated" if ifaces in (["lo"], []) and not routes else "network: NOT isolated")
