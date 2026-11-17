"""Create short-lived LAN test certificates without changing any trust store."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def openssl(*args: str) -> str:
    result = subprocess.run(["openssl", *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Private IPv4 address of the web host")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address.version != 4 or not address.is_private or address.is_loopback:
        parser.error("--host must be the computer's private LAN IPv4 address")

    output = ROOT / ".runtime" / "https"
    output.mkdir(parents=True, exist_ok=True)
    ca_key, ca_cert = output / "root-ca.key", output / "root-ca.crt"
    key, request, certificate = output / "server.key", output / "server.csr", output / "server.crt"

    if not ca_key.exists() and not ca_cert.exists():
        openssl(
            "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "7",
            "-keyout", str(ca_key), "-out", str(ca_cert),
            "-subj", "/CN=G1 Thai Local Test CA",
            "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
        )
    elif not ca_key.exists() or not ca_cert.exists():
        raise RuntimeError("Incomplete local CA files; restore the missing file before continuing")
    openssl("x509", "-in", str(ca_cert), "-checkend", "0", "-noout")

    extensions = output / "server.ext"
    extensions.write_text(
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
        f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{address}\n",
        encoding="utf-8",
    )
    openssl(
        "req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256",
        "-keyout", str(key), "-out", str(request), "-subj", "/CN=G1 Thai Local Web",
    )
    openssl(
        "x509", "-req", "-in", str(request), "-CA", str(ca_cert), "-CAkey", str(ca_key),
        "-CAcreateserial", "-out", str(certificate), "-days", "7", "-sha256",
        "-extfile", str(extensions),
    )
    openssl("verify", "-CAfile", str(ca_cert), "-verify_ip", str(address), str(certificate))
    public_ca = output / "g1-local-ca.cer"
    openssl("x509", "-in", str(ca_cert), "-outform", "DER", "-out", str(public_ca))
    digest = hashlib.sha256(public_ca.read_bytes()).hexdigest().upper()
    fingerprint = ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))
    config = {
        "host": str(address), "httpsPort": 3443, "setupPort": 3444,
        "upstream": "http://127.0.0.1:3000", "caFingerprint": fingerprint,
    }
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Setup: http://{address}:3444")
    print(f"HTTPS: https://{address}:3443")
    print(f"Public CA: {public_ca}")
    print(f"CA SHA-256: {fingerprint}")
    print("No system or browser trust store was modified.")


if __name__ == "__main__":
    main()
