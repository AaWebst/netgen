#!/bin/bash
echo "Installing VEP1445..."
pip3 install -r requirements.txt --break-system-packages || pip3 install -r requirements.txt
echo "✅ Dependencies installed"
echo ""
echo "To run:"
echo "  sudo python3 web_api.py"
echo ""
echo "Then open: http://$(hostname -I | awk '{print $1}'):5000"
