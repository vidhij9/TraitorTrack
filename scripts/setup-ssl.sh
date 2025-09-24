#!/bin/bash

# SSL Certificate Setup Script for TraceTrack
# Creates self-signed certificates for development/testing

set -e

SSL_DIR="./docker/nginx/ssl"
DOMAIN="localhost"

echo "🔐 Setting up SSL certificates for TraceTrack..."

# Create SSL directory
mkdir -p "$SSL_DIR"

# Check if certificates already exist
if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "✅ SSL certificates already exist"
    echo "To regenerate, remove files in $SSL_DIR and run this script again"
    exit 0
fi

# Generate private key
echo "🔑 Generating private key..."
openssl genrsa -out "$SSL_DIR/key.pem" 2048

# Generate certificate
echo "📜 Generating self-signed certificate..."
openssl req -new -x509 -key "$SSL_DIR/key.pem" -out "$SSL_DIR/cert.pem" -days 365 -subj "/C=US/ST=State/L=City/O=TraceTrack/CN=$DOMAIN"

# Set proper permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo "✅ SSL certificates created successfully!"
echo "📁 Location: $SSL_DIR"
echo "⚠️  These are self-signed certificates for development only"
echo "🚀 For production, replace with certificates from a trusted CA"

# Show certificate info
echo ""
echo "📋 Certificate Information:"
openssl x509 -in "$SSL_DIR/cert.pem" -text -noout | grep -E "(Subject:|Not Before|Not After)"