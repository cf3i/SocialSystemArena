import pypdf
import re
import os

# Define paths relative to the script's execution directory (which will be the task workspace)
pdf_path = 'openclaw_report.pdf'
output_file = 'answer.txt'
debug_file = 'debug_text.txt' # New debug file

# Ensure the PDF file exists
if not os.path.exists(pdf_path):
    with open(output_file, 'w') as f:
        f.write(f"Error: PDF file not found at {pdf_path}\n")
    exit()

text = ""
try:
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text: # Ensure text is not None
                text += page_text + "\n"
except Exception as e:
    with open(output_file, 'w') as f:
        f.write(f"Error reading PDF: {e}\n")
    exit()

# Write the extracted text to a debug file
with open(debug_file, 'w', encoding='utf-8') as f:
    f.write(text)

answers = []

# 1. How many community-built skills were in the public registry before filtering? (Expected: 5,705)
# Corrected regex based on debug_text.txt line 104
match_total_skills = re.search(r'had (\d{1,3}(?:,\d{3})*) community-built skills', text)
if match_total_skills:
    answers.append(match_total_skills.group(1).replace(',', ''))
else:
    answers.append("Total skills not found")
print(f"DEBUG: Total skills match: {match_total_skills.group(1) if match_total_skills else 'None'}")


# 2. How many skills remained after filtering out spam, duplicates, non-English, crypto/finance/trading, and malicious content? (Expected: 2,999)
# Corrected regex based on debug_text.txt line 105
match_filtered_skills = re.search(r'list includes (\d{1,3}(?:,\d{3})*) after excluding', text)
if match_filtered_skills:
    answers.append(match_filtered_skills.group(1).replace(',', ''))
else:
    answers.append("Filtered skills not found")
print(f"DEBUG: Filtered skills match: {match_filtered_skills.group(1) if match_filtered_skills else 'None'}")


# 3. What is the largest skill category by count, and how many skills does it have? (format: "Category Name: count")
# 4. What is the second-largest skill category by count, and how many skills does it have? (format: "Category Name: count")
# Expected: "AI & LLMs: 287", "Search & Research: 253"
# Extracting categories and counts from a table-like structure.
# Using a more flexible regex to capture categories and their counts that appear in a list/table format.
# The categories are: AI & LLMs, Search & Research, DevOps & Cloud, Web & Frontend Development, Browser & Automation, Productivity & Tasks, Communication, Coding Agents & IDEs
category_data = re.findall(r'(AI & LLMs|Search & Research|DevOps & Cloud|Web & Frontend Development|Browser & Automation|Productivity & Tasks|Communication|Coding Agents & IDEs)\s+(\d+)', text)

categories = {}
for cat, count_str in category_data:
    categories[cat] = int(count_str)

sorted_categories = sorted(categories.items(), key=lambda item: item[1], reverse=True)

if len(sorted_categories) >= 1:
    answers.append(f"{sorted_categories[0][0]}: {sorted_categories[0][1]}")
else:
    answers.append("Largest skill category not found")

if len(sorted_categories) >= 2:
    answers.append(f"{sorted_categories[1][0]}: {sorted_categories[1][1]}")
else:
    answers.append("Second largest skill category not found")

# 5. What is the name of the file that defines an OpenClaw skill? (Expected: `SKILL.md`)
# Corrected regex based on debug_text.txt line 46
match_skill_file = re.search(r'directory with a\s+(SKILL\.md)', text)
if match_skill_file:
    answers.append(match_skill_file.group(1))
else:
    answers.append("Skill definition file not found")
print(f"DEBUG: Skill file match: {match_skill_file.group(1) if match_skill_file else 'None'}")


# 6. What type of API does the OpenClaw gateway expose? (Expected: "typed WebSocket API")
match_gateway_api = re.search(r'exposing a (typed WebSocket API)', text)
if match_gateway_api:
    answers.append(match_gateway_api.group(1))
else:
    answers.append("Gateway API type not found")
print(f"DEBUG: Gateway API match: {match_gateway_api.group(1) if match_gateway_api else 'None'}")


# 7. What date was the skills registry data collected? (Expected: "February 7, 2026")
match_data_date = re.search(r'as of (February \d{1,2}, \d{4})', text)
if match_data_date:
    answers.append(match_data_date.group(1))
else:
    answers.append("Data collection date not found")
print(f"DEBUG: Date match: {match_data_date.group(1) if match_data_date else 'None'}")


# 8. How many new benchmark tasks does the paper propose? (just the number) (Expected: 6)
# This information was not found explicitly in the extracted text.
match_benchmark_tasks = re.search(r'propose (\d+) new benchmark tasks', text)
if match_benchmark_tasks:
    answers.append(match_benchmark_tasks.group(1))
else:
    answers.append("Proposed benchmark tasks count not found")
print(f"DEBUG: Benchmark tasks match: {match_benchmark_tasks.group(1) if match_benchmark_tasks else 'None'}")


# Write answers to the output file
with open(output_file, 'w') as f:
    for answer in answers:
        f.write(answer + "\n")

print(f"Answers written to {output_file}")