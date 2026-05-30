#!/usr/bin/env python3
"""
🔐 Master Key Generator for CTO Dashboard
Generates cryptographically secure master keys for credential encryption

Usage:
    python generate_master_key.py [--length 64] [--format hex|base64]
"""

import os
import sys
import secrets
import base64
import argparse
from pathlib import Path


class MasterKeyGenerator:
    """
    Secure master key generation utility
    """
    
    @staticmethod
    def generate_hex_key(length: int = 64) -> str:
        """Generate hexadecimal key"""
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_base64_key(length: int = 48) -> str:
        """Generate base64 key (URL-safe)"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_from_passphrase(passphrase: str) -> str:
        """Generate key from a memorable passphrase (NOT recommended for production)"""
        import hashlib
        return hashlib.sha256(passphrase.encode()).hexdigest()
    
    @staticmethod
    def validate_key_strength(key: str) -> dict:
        """Validate key strength"""
        return {
            "length": len(key),
            "min_recommended": 64,
            "is_strong": len(key) >= 64,
            "entropy_bits": len(key) * 4 if all(c in '0123456789abcdefABCDEF' for c in key) else len(key) * 6
        }
    
    @staticmethod
    def generate_deployment_keys() -> dict:
        """Generate complete set of keys for deployment"""
        return {
            "credential_master_key": MasterKeyGenerator.generate_hex_key(64),
            "jwt_secret": MasterKeyGenerator.generate_hex_key(32),
            "session_secret": MasterKeyGenerator.generate_hex_key(32),
            "backup_encryption_key": MasterKeyGenerator.generate_hex_key(64)
        }


def main():
    parser = argparse.ArgumentParser(description="Generate secure master keys for CTO Dashboard")
    parser.add_argument("--length", type=int, default=64, help="Key length (default: 64)")
    parser.add_argument("--format", choices=['hex', 'base64'], default='hex', help="Key format (default: hex)")
    parser.add_argument("--full-deployment", action="store_true", help="Generate full deployment key set")
    parser.add_argument("--passphrase", type=str, help="Generate from passphrase (NOT recommended for production)")
    parser.add_argument("--validate", type=str, help="Validate existing key strength")
    parser.add_argument("--railway", action="store_true", help="Generate Railway environment commands")
    
    args = parser.parse_args()
    
    print("🔐 CTO Dashboard Master Key Generator")
    print("====================================")
    
    if args.validate:
        print(f"\n🔍 Validating key: {args.validate[:8]}...")
        validation = MasterKeyGenerator.validate_key_strength(args.validate)
        print(f"Length: {validation['length']} characters")
        print(f"Entropy: ~{validation['entropy_bits']} bits")
        print(f"Strength: {'✅ Strong' if validation['is_strong'] else '⚠️ Weak (recommend 64+ chars)'}")
        return
    
    if args.full_deployment:
        print("\n🚀 Generating complete deployment key set...")
        keys = MasterKeyGenerator.generate_deployment_keys()
        
        print("\n📋 Environment Variables:")
        print("=" * 50)
        for key_name, key_value in keys.items():
            env_name = key_name.upper()
            print(f"export {env_name}=\"{key_value}\"")
        
        if args.railway:
            print("\n🚄 Railway CLI Commands:")
            print("=" * 50)
            for key_name, key_value in keys.items():
                env_name = key_name.upper()
                print(f"railway variables set {env_name}=\"{key_value}\"")
        
        print("\n💾 Save to .env file:")
        print("=" * 50)
        env_content = "\n".join([f"{k.upper()}=\"{v}\"" for k, v in keys.items()])
        print(env_content)
        
        # Optionally save to .env file
        save_to_file = input("\n💾 Save to .env file? [y/N]: ").lower() == 'y'
        if save_to_file:
            env_file = Path(".env")
            
            # Read existing .env if it exists
            existing_content = ""
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_content = f.read()
            
            # Append new keys
            with open(env_file, 'w') as f:
                f.write(existing_content)
                f.write("\n# Generated master keys\n")
                f.write(env_content)
                f.write("\n")
            
            print(f"✅ Keys saved to {env_file}")
            print("⚠️  WARNING: Keep .env file secure and never commit to git!")
        
        return
    
    if args.passphrase:
        print(f"\n⚠️  WARNING: Generating key from passphrase is less secure!")
        print("🔒 For production, use randomly generated keys instead.")
        key = MasterKeyGenerator.generate_from_passphrase(args.passphrase)
    else:
        print(f"\n🎲 Generating {args.format} key (length: {args.length})...")
        if args.format == 'hex':
            key = MasterKeyGenerator.generate_hex_key(args.length)
        else:
            key = MasterKeyGenerator.generate_base64_key(args.length)
    
    print(f"\n🔑 Generated Key:")
    print("=" * 50)
    print(key)
    
    # Validate strength
    validation = MasterKeyGenerator.validate_key_strength(key)
    print(f"\n📊 Key Strength:")
    print(f"Length: {validation['length']} characters")
    print(f"Entropy: ~{validation['entropy_bits']} bits")
    print(f"Status: {'✅ Strong' if validation['is_strong'] else '⚠️ Consider longer key'}")
    
    print(f"\n🚀 Usage:")
    print("=" * 50)
    print("# For local development:")
    print(f"export CREDENTIAL_MASTER_KEY=\"{key}\"")
    print()
    print("# For Railway deployment:")
    print(f"railway variables set CREDENTIAL_MASTER_KEY=\"{key}\"")
    print()
    print("# For Docker/production:")
    print(f"docker run -e CREDENTIAL_MASTER_KEY=\"{key}\" your-app")
    
    print(f"\n⚠️  SECURITY WARNINGS:")
    print("• Store this key securely (password manager, secure vault)")
    print("• Never commit this key to version control")
    print("• Use different keys for different environments")
    print("• Back up this key - losing it means losing all credentials")
    print("• Rotate keys periodically in production")


if __name__ == "__main__":
    main()