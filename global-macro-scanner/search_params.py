import sys

def search_xml(file_path, terms):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                for term in terms:
                    if term.lower() in line.lower():
                        print(f"L{i+1}: {line.strip()}")
                        break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_xml('ib_parameters.xml', ['scanCode', 'LOW'])
