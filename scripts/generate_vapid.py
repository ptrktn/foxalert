#!/usr/bin/env python3
"""Generate VAPID (P-256) keypair and print base64url keys.

Usage:
  python3 scripts/generate_vapid.py [--out file.json]

Outputs environment export lines and optionally writes a JSON file with keys.
"""
import argparse
import json
import base64

from cryptography.hazmat.primitives.asymmetric import ec


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode('utf-8')


def generate_vapid_keys():
    # Generate private key (SECP256R1 / P-256)
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_numbers = private_key.private_numbers()
    private_value = private_numbers.private_value
    private_bytes = private_value.to_bytes(32, 'big')

    pub = private_key.public_key()
    pub_numbers = pub.public_numbers()
    x = pub_numbers.x.to_bytes(32, 'big')
    y = pub_numbers.y.to_bytes(32, 'big')
    # Uncompressed public key format 0x04 || X || Y
    public_bytes = b"\x04" + x + y

    return b64url(public_bytes), b64url(private_bytes)


def main():
    parser = argparse.ArgumentParser(description='Generate VAPID VAPID keys (P-256)')
    parser.add_argument('--out', '-o', help='Write keys to JSON file')
    args = parser.parse_args()

    public_key, private_key = generate_vapid_keys()

    print('Public Key (base64url):')
    print(public_key)
    print('\nPrivate Key (base64url):')
    print(private_key)

    print('\nShell export commands:')
    print(f'export VAPID_PUBLIC_KEY="{public_key}"')
    print(f'export VAPID_PRIVATE_KEY="{private_key}"')

    if args.out:
        doc = { 'publicKey': public_key, 'privateKey': private_key }
        with open(args.out, 'w') as f:
            json.dump(doc, f, indent=2)
        print(f'\nWrote keys to {args.out}')


if __name__ == '__main__':
    main()
