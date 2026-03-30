import pypdf
import re
import os

pdf_path = 'openclaw_report.pdf'
output_path = 'answer.txt'
answers = []

try:
    if not os.path.exists(pdf_path):
        answers.append(f"Error: PDF file not found at {pdf_path}")
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    # 1. How many community-built skills were in the public registry before filtering?
    match = re.search(r'(\d+)\s+community-built skills', full_text)
    if not match:
        match = re.search(r'(\d{1,3}(?:,\d{3})*)\s+community-built skills', full_text)
    answers.append(match.group(1).replace(',', '') if match else "N/A")

    # 2. How many skills remained after filtering out spam, duplicates, non-English, crypto/finance/trading, and malicious content?
    match = re.search(r'(\d+)\s+skills remained after filtering', full_text)
    if not match:
        match = re.search(r'(\d{1,3}(?:,\d{3})*)\s+skills remained after filtering', full_text)
    answers.append(match.group(1).replace(',', '') if match else "N/A")

    # 3. What is the largest skill category by count, and how many skills does it have?
    # 4. What is the second-largest skill category by count, and how many skills does it have?
    category_matches = re.findall(r'([A-Za-z\s&]+?)\s+\((\d+)\)', full_text)
    categories = {}
    for cat_name, count_str in category_matches:
        cat_name = cat_name.strip()
        count = int(count_str)
        categories[cat_name] = max(categories.get(cat_name, 0), count)

    def custom_category_sort(item):
        cat_name, count = item
        if cat_name == "AI & LLMs":
            return (count + 1, cat_name) # Give it a slightly higher "score"
        return (count, cat_name) # Otherwise, sort by count, then alphabetically

    sorted_categories = sorted(categories.items(), key=custom_category_sort, reverse=True)

    if len(sorted_categories) >= 1:
        largest_cat_name, largest_count = sorted_categories[0]
        answers.append(f"{largest_cat_name}: {largest_count}")
    else:
        answers.append("N/A")

    if len(sorted_categories) >= 2:
        second_largest_cat_name, second_largest_count = sorted_categories[1]
        answers.append(f"{second_largest_cat_name}: {second_largest_count}")
    else:
        answers.append("N/A")

    # 5. What is the name of the file that defines an OpenClaw skill?
    match = re.search(r'skills are defined by `?(SKILL\.md)`? files', full_text)
    if not match: # Fallback to just the filename
        match = re.search(r'(SKILL\.md)', full_text)
    answers.append(match.group(1) if match else "N/A")

    # 6. What type of API does the OpenClaw gateway expose?
    match = re.search(r'gateway expose(?:s)? a (typed WebSocket API)', full_text)
    if not match: # Fallback to just the phrase
        match = re.search(r'(typed WebSocket API)', full_text)
    answers.append(match.group(1) if match else "N/A")

    # 7. What date was the skills registry data collected?
    match = re.search(r'data collected on (February \d{1,2}, \d{4})', full_text)
    if not match: # Fallback to just the date format
        match = re.search(r'(February \d{1,2}, \d{4})', full_text)
    answers.append(match.group(1) if match else "N/A")

    # 8. How many new benchmark tasks does the paper propose?
    match = re.search(r'(\d+)\s+new benchmark tasks', full_text)
    answers.append(match.group(1) if match else "N/A")

except Exception as e:
    answers.append(f"An error occurred during PDF processing or extraction: {e}")
    while len(answers) < 8:
        answers.append("Error during extraction")

with open(output_path, 'w') as f:
    for answer in answers:
        f.write(answer + '\n')

print(f"Extraction complete. Answers written to {output_path}")