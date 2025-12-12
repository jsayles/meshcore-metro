#!/bin/bash
# MeshCore METRO - WiFi Configuration Script
# Configures WiFi connection to phone hotspot for field operations

set -e  # Exit on any error

echo ""
echo "=================================="
echo "MeshCore METRO - WiFi Setup"
echo "=================================="
echo ""
echo "This script will configure your Pi to connect to your phone's WiFi hotspot."
echo "This is ADDITIVE - it won't remove or modify any existing WiFi connections."
echo ""

# Scan for available WiFi networks
echo "Scanning for available WiFi networks..."
sudo nmcli dev wifi rescan 2>/dev/null || true
sleep 2

# Get list of SSIDs (excluding the header and empty lines)
mapfile -t WIFI_NETWORKS < <(sudo nmcli -t -f SSID dev wifi list | grep -v '^$' | sort -u)

if [ ${#WIFI_NETWORKS[@]} -gt 0 ]; then
    echo ""
    echo "Available WiFi networks:"
    echo "  0) Exit without changes"
    echo "  1) Enter SSID manually"
    for i in "${!WIFI_NETWORKS[@]}"; do
        echo "  $((i+2))) ${WIFI_NETWORKS[$i]}"
    done
    echo ""
    read -p "Select your phone's hotspot (0-$((${#WIFI_NETWORKS[@]}+1))): " WIFI_CHOICE

    if [ "$WIFI_CHOICE" = "0" ]; then
        echo "Exiting without changes"
        exit 0
    elif [ "$WIFI_CHOICE" = "1" ]; then
        read -p "Enter your phone's hotspot SSID: " HOTSPOT_SSID
    elif [ "$WIFI_CHOICE" -ge 2 ] && [ "$WIFI_CHOICE" -le $((${#WIFI_NETWORKS[@]}+1)) ]; then
        HOTSPOT_SSID="${WIFI_NETWORKS[$((WIFI_CHOICE-2))]}"
        echo "Selected: $HOTSPOT_SSID"
    else
        echo "Invalid selection"
        exit 1
    fi
else
    echo "   No WiFi networks found."
    read -p "Enter your phone's hotspot SSID [or press Enter to exit]: " HOTSPOT_SSID
    if [ -z "$HOTSPOT_SSID" ]; then
        echo "Exiting without changes"
        exit 0
    fi
fi

if [ -n "$HOTSPOT_SSID" ]; then
    read -sp "Enter password for '$HOTSPOT_SSID': " HOTSPOT_PASSWORD
    echo ""
    echo ""

    if [ -n "$HOTSPOT_PASSWORD" ]; then
        echo "=> Adding WiFi connection profile..."

        # Check if connection already exists and remove it
        if sudo nmcli connection show "phone-hotspot" &>/dev/null; then
            echo "   Removing existing 'phone-hotspot' connection..."
            sudo nmcli connection delete "phone-hotspot"
        fi

        # Use nmcli to add connection (Raspberry Pi OS Bookworm uses NetworkManager)
        # This is additive - it doesn't remove or modify other connections
        if sudo nmcli connection add \
            con-name "phone-hotspot" \
            ifname wlan0 \
            type wifi \
            ssid "$HOTSPOT_SSID" \
            wifi-sec.key-mgmt wpa-psk \
            wifi-sec.psk "$HOTSPOT_PASSWORD" \
            connection.autoconnect yes \
            connection.autoconnect-priority 10; then
            echo ""
            echo "✓ WiFi connection 'phone-hotspot' configured successfully!"
            echo "✓ Pi will auto-connect to '$HOTSPOT_SSID' when available"
            echo "✓ Your existing WiFi connections are still configured"
            echo ""

            # Try to connect now if the network is available
            read -p "Try to connect to '$HOTSPOT_SSID' now? (y/n): " CONNECT_NOW
            if [ "$CONNECT_NOW" = "y" ] || [ "$CONNECT_NOW" = "Y" ]; then
                echo "Connecting..."
                if sudo nmcli connection up "phone-hotspot"; then
                    echo "✓ Connected successfully!"
                else
                    echo "✗ Connection failed - network may not be in range"
                    echo "  Pi will auto-connect when the network is available"
                fi
            fi
        else
            echo ""
            echo "✗ ERROR: Failed to add WiFi connection"
            echo ""
            echo "You can try manually with:"
            echo "  sudo nmcli device wifi connect \"$HOTSPOT_SSID\" password \"your-password\""
            exit 1
        fi
    else
        echo "No password provided"
        exit 1
    fi
fi

echo ""
echo "=================================="
echo "WiFi Configuration Complete!"
echo "=================================="
echo ""
