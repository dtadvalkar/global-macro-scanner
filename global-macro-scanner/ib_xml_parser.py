import xml.etree.ElementTree as ET

def parse_ib_xml():
    try:
        tree = ET.parse('ib_parameters.xml')
        root = tree.getroot()
        
        print("🌍 --- LOCATIONS ---")
        # Find all Location tags
        for loc in root.findall('.//Location'):
            display_name = loc.find('displayName')
            location_code = loc.find('locationCode')
            if display_name is not None and location_code is not None:
                d_text = display_name.text
                l_text = location_code.text
                if any(k in d_text for k in ['Canada', 'India', 'Toronto', 'NSE', 'TSE', 'ASEAN']):
                    print(f"[{l_text}] {d_text}")

        print("\n🎣 --- SCAN CODES ---")
        # Find all ScanCode tags in the ScanType list
        # Note: The structure might vary, sometimes it's under <ScanTypeList>
        for scan in root.findall('.//ScanType'):
            scan_code = scan.find('scanCode')
            display_name = scan.find('displayName')
            if scan_code is not None:
                s_text = scan_code.text
                d_text = display_name.text if display_name is not None else "Unknown"
                if any(k in s_text or k in d_text for k in ['LOW', 'PERC', 'GAIN', 'VOL']):
                    print(f"[{s_text}] {d_text}")

    except Exception as e:
        print(f"❌ Parse error: {e}")

if __name__ == "__main__":
    parse_ib_xml()
