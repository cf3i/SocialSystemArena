import os
import re
from datetime import datetime

def parse_email(email_content):
    """Parses email content to extract relevant information."""
    data = {
        "subject": "",
        "from": "",
        "date": "",
        "body": ""
    }
    
    # Extract headers
    headers_end_index = email_content.find("\n\n")
    if headers_end_index == -1:
        headers_end_index = len(email_content) # No double newline, assume whole content is headers/body
    
    headers_raw = email_content[:headers_end_index]
    body_raw = email_content[headers_end_index:].strip()

    for line in headers_raw.split('\n'):
        if line.lower().startswith("subject:"):
            data["subject"] = line[len("subject:"):].strip()
        elif line.lower().startswith("from:"):
            data["from"] = line[len("from:"):].strip()
        elif line.lower().startswith("date:"):
            data["date"] = line[len("date:"):].strip()
    
    data["body"] = body_raw
    return data

def extract_project_alpha_info(email_data):
    """Extracts Project Alpha specific information from email body and subject."""
    info = {
        "technical_stack": [],
        "budget": None,
        "customer_impact": [],
        "business_impact": [],
        "key_facts": [],
        "project_name": "Project Alpha" # Default
    }

    subject = email_data["subject"].lower()
    body = email_data["body"].lower()

    # Project Name (if explicitly mentioned beyond "Project Alpha")
    project_name_match = re.search(r"project alpha:?\s*([^\n]+)", subject)
    if project_name_match:
        info["project_name"] = "Project Alpha: " + project_name_match.group(1).strip()
    
    # Technical Stack
    tech_stack_keywords = ["tech stack", "technology stack", "technologies", "frameworks", "libraries"]
    for keyword in tech_stack_keywords:
        if keyword in body:
            # Attempt to find a list or specific mentions
            match = re.search(rf"{keyword}.*?:\s*(.*?)(?=\n\n|\n[a-z]|\Z)", body, re.DOTALL)
            if match:
                stack_details = match.group(1).strip()
                # Split by common list delimiters
                stack_items = re.split(r'[,\n;]', stack_details)
                info["technical_stack"].extend([item.strip() for item in stack_items if item.strip()])
    
    # Budget
    budget_match = re.search(r"budget:?\s*(\$?\s*[\d,]+\.?\d*\s*(million|k|usd)?)", body)
    if budget_match:
        extracted_budget = budget_match.group(1).strip()
        if extracted_budget and extracted_budget != ',': # Ensure it's not empty and not just a comma
            info["budget"] = extracted_budget
        else:
            info["budget"] = None # Reset to None if invalid
    
    # Customer/Business Impact
    impact_keywords = {
        "customer_impact": ["customer impact", "client benefit", "user experience", "customer satisfaction"],
        "business_impact": ["business impact", "revenue", "cost saving", "market share", "strategic importance"]
    }

    for impact_type, keywords in impact_keywords.items():
        for keyword in keywords:
            # Find sentences or phrases related to the impact
            matches = re.findall(rf"({keyword}.*?[\.\n])", body, re.DOTALL)
            for match in matches:
                info[impact_type].append(match.strip())
            
            # Also try to find general impact statements
            general_impact_match = re.search(r"(this project will.*?impact.*?[\.\n])", body)
            if general_impact_match and general_impact_match.group(1) not in info[impact_type]:
                info[impact_type].append(general_impact_match.group(1).strip())


    # Key Facts / Milestones
    key_fact_keywords = ["key facts", "milestones", "updates", "progress", "next steps", "important notes"]
    for keyword in key_fact_keywords:
        if keyword in body:
            match = re.search(rf"{keyword}.*?:\s*(.*?)(?=\n\n|\n[a-z]|\Z)", body, re.DOTALL)
            if match:
                facts = match.group(1).strip()
                fact_items = re.split(r'[-*•\n]', facts)
                info["key_facts"].extend([item.strip() for item in fact_items if item.strip()])
    
    # Remove duplicates and clean up
    info["technical_stack"] = list(set(info["technical_stack"]))
    info["customer_impact"] = list(set(info["customer_impact"]))
    info["business_impact"] = list(set(info["business_impact"]))
    info["key_facts"] = list(set(info["key_facts"]))

    return info

def main():
    emails_dir = "emails/"
    all_extracted_info = {
        "technical_stack": set(),
        "budget": None, # Keep the latest or most significant budget
        "customer_impact": set(),
        "business_impact": set(),
        "key_facts": set(),
        "project_name": "Project Alpha"
    }
    
    email_files = [f for f in os.listdir(emails_dir) if f.endswith(".txt")]
    
    for email_file in sorted(email_files): # Process in order for potential evolution
        with open(os.path.join(emails_dir, email_file), 'r') as f:
            content = f.read()
            email_data = parse_email(content)
            
            # Filter for "Project Alpha"
            if "project alpha" in email_data["subject"].lower() or "project alpha" in email_data["body"].lower():
                extracted = extract_project_alpha_info(email_data)
                
                all_extracted_info["technical_stack"].update(extracted["technical_stack"])
                if extracted["budget"]:
                    all_extracted_info["budget"] = extracted["budget"] # Overwrite with latest budget
                all_extracted_info["customer_impact"].update(extracted["customer_impact"])
                all_extracted_info["business_impact"].update(extracted["business_impact"])
                all_extracted_info["key_facts"].update(extracted["key_facts"])
                if extracted["project_name"] != "Project Alpha":
                    all_extracted_info["project_name"] = extracted["project_name"] # Update if more specific

    # Format the summary
    summary_content = f"# {all_extracted_info['project_name']} Summary\n\n"
    summary_content += "## 1. Technical Stack\n"
    if all_extracted_info["technical_stack"]:
        summary_content += "\n".join([f"- {item}" for item in sorted(list(all_extracted_info["technical_stack"]))]) + "\n\n"
    else:
        summary_content += "No specific technical stack details found.\n\n"

    summary_content += "## 2. Budget\n"
    if all_extracted_info["budget"]:
        summary_content += f"{all_extracted_info['budget']}\n\n"
    else:
        summary_content += "No specific budget details found.\n\n"

    summary_content += "## 3. Customer Impact\n"
    if all_extracted_info["customer_impact"]:
        summary_content += "\n".join([f"- {item}" for item in sorted(list(all_extracted_info["customer_impact"]))]) + "\n\n"
    else:
        summary_content += "No specific customer impact details found.\n\n"

    summary_content += "## 4. Business Impact\n"
    if all_extracted_info["business_impact"]:
        summary_content += "\n".join([f"- {item}" for item in sorted(list(all_extracted_info["business_impact"]))]) + "\n\n"
    else:
        summary_content += "No specific business impact details found.\n\n"

    summary_content += "## 5. Key Facts / Milestones\n"
    if all_extracted_info["key_facts"]:
        summary_content += "\n".join([f"- {item}" for item in sorted(list(all_extracted_info["key_facts"]))]) + "\n\n"
    else:
        summary_content += "No specific key facts or milestones found.\n\n"

    with open("alpha_summary.md", "w") as f:
        f.write(summary_content)
    
    print("alpha_summary.md generated successfully.")

if __name__ == "__main__":
    main()