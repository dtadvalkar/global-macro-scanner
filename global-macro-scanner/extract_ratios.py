import re
import os
import json

def extract_tags(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    ratios = re.findall(r'Ratio FieldName="(.*?)" Type="(\w)">(.*?)</Ratio>', content)
    return ratios

all_ratios = {}
for f in ['ibkr_raw_RELIANCE_NS.xml', 'ibkr_raw_TCS_NS.xml', 'ibkr_raw_20MICRONS_NS.xml']:
    tags = extract_tags(f)
    for tag, ttype, val in tags:
        if tag not in all_ratios:
            all_ratios[tag] = val

print(json.dumps(all_ratios, indent=2))
